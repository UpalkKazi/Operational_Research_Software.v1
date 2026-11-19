"""Session workspace: models, immutable revisions, runs, sweeps and chat history.

Ownership rules
---------------
* ``ModelRecord.baseline`` is the model as loaded; it never changes (revision ``r0``).
* ``ModelRecord.working`` is the editable draft.  Every edit bumps
  ``working_version``; the draft is frozen into a new immutable revision only
  when it is solved, so a ``Run`` always points at exactly what was solved.
* A run's result is written only to its own record.  "Current" results are
  looked up by revision, so a late completion can never overwrite a newer one.
* Sweeps solve derived copies and never touch ``working``.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field, replace
from typing import Any, Dict, List, Optional, Tuple

from src.modeling.model_spec import (
    ConstraintSpec,
    LinearExpression,
    ModelSpec,
    ModelValidationError,
    ObjectiveSpec,
    VariableSpec,
)
from src.services import jobs
from src.solvers.backends import SOLVERS, solve_spec


class EditError(ValueError):
    pass


@dataclass
class ModelRecord:
    id: str
    name: str
    source: Dict[str, Any]
    baseline: ModelSpec
    working: ModelSpec
    revisions: Dict[str, ModelSpec]
    revision_order: List[str]
    working_version: int = 0
    frozen: Dict[int, str] = field(default_factory=lambda: {0: "r0"})
    run_ids: List[str] = field(default_factory=list)
    sweep_ids: List[str] = field(default_factory=list)
    created: float = field(default_factory=time.time)

    def revision_label(self, revision_id: str) -> str:
        if revision_id == "r0":
            return "Baseline"
        return f"Edit {self.revision_order.index(revision_id)}" if revision_id in self.revision_order else revision_id

    @property
    def working_revision(self) -> Optional[str]:
        return self.frozen.get(self.working_version)

    @property
    def is_edited(self) -> bool:
        return self.working.fingerprint() != self.baseline.fingerprint()


@dataclass
class Run:
    id: str
    model_id: str
    revision_id: str
    origin: str
    requested_solver: str
    time_limit: Optional[float]
    job_id: Optional[str]
    status: str = "queued"  # queued | running | done | failed
    result: Optional[Dict[str, Any]] = None
    created: float = field(default_factory=time.time)
    finished: Optional[float] = None
    historical: bool = False
    cache_hit: bool = False
    library_check: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

    @property
    def pending(self) -> bool:
        return self.status in ("queued", "running")


@dataclass
class Sweep:
    id: str
    model_id: str
    revision_id: str
    constraint_uid: str
    constraint_name: str
    values: List[float]
    solver: str
    job_id: Optional[str]
    status: str = "running"
    points: List[Dict[str, Any]] = field(default_factory=list)
    created: float = field(default_factory=time.time)
    error: Optional[str] = None


def _id(prefix: str) -> str:
    return f"{prefix}{uuid.uuid4().hex[:8]}"


class Workspace:
    def __init__(self) -> None:
        self.models: Dict[str, ModelRecord] = {}
        self.runs: Dict[str, Run] = {}
        self.sweeps: Dict[str, Sweep] = {}
        self.messages: List[Dict[str, Any]] = []
        self.active_model_id: Optional[str] = None

    # ------------------------------------------------------------------
    #  Models
    # ------------------------------------------------------------------
    def add_model(self, spec: ModelSpec, name: str, source: Dict[str, Any], activate: bool = True) -> ModelRecord:
        spec = spec.with_uids()
        spec.validate()
        record = ModelRecord(
            id=_id("m"), name=name, source=dict(source), baseline=spec, working=spec,
            revisions={"r0": spec}, revision_order=["r0"],
        )
        self.models[record.id] = record
        if activate:
            self.active_model_id = record.id
        return record

    def model(self, model_id: Optional[str]) -> Optional[ModelRecord]:
        return self.models.get(model_id) if model_id else None

    def active(self) -> Optional[ModelRecord]:
        return self.model(self.active_model_id)

    def activate(self, model_id: str) -> None:
        if model_id in self.models:
            self.active_model_id = model_id

    # ------------------------------------------------------------------
    #  Edits (each produces a new immutable working spec)
    # ------------------------------------------------------------------
    def _commit(self, record: ModelRecord, spec: ModelSpec) -> ModelSpec:
        if spec.fingerprint() == record.working.fingerprint() and [v.name for v in spec.variables] == [v.name for v in record.working.variables] and [c.name for c in spec.constraints] == [c.name for c in record.working.constraints]:
            return record.working
        record.working = spec
        record.working_version += 1
        if spec.fingerprint() == record.baseline.fingerprint() and _same_names(spec, record.baseline):
            record.frozen[record.working_version] = "r0"
        return spec

    def _constraint(self, record: ModelRecord, uid: str) -> Tuple[int, ConstraintSpec]:
        for index, constraint in enumerate(record.working.constraints):
            if constraint.uid == uid:
                return index, constraint
        raise EditError("That constraint no longer exists.")

    def _replace_constraint(self, record: ModelRecord, uid: str, **changes) -> ModelSpec:
        index, constraint = self._constraint(record, uid)
        constraints = list(record.working.constraints)
        constraints[index] = replace(constraint, **changes)
        return self._commit(record, replace(record.working, constraints=constraints))

    def set_rhs(self, model_id: str, uid: str, value: float) -> ModelSpec:
        try:
            value = float(value)
        except (TypeError, ValueError) as exc:
            raise EditError("The right-hand side must be a number.") from exc
        return self._replace_constraint(self.models[model_id], uid, rhs=value)

    def set_relation(self, model_id: str, uid: str, sense: str) -> ModelSpec:
        if sense not in ("<=", ">=", "="):
            raise EditError("Choose ≤, ≥ or =.")
        return self._replace_constraint(self.models[model_id], uid, sense=sense)

    def set_constraint_expression(self, model_id: str, uid: str, expression: LinearExpression,
                                  sense: Optional[str] = None, rhs: Optional[float] = None) -> ModelSpec:
        record = self.models[model_id]
        _check_names(record.working, expression)
        if not expression.coefficients:
            raise EditError("A constraint needs at least one variable.")
        changes: Dict[str, Any] = {"expression": expression}
        if sense is not None:
            changes["sense"] = sense
        if rhs is not None:
            changes["rhs"] = float(rhs)
        return self._replace_constraint(record, uid, **changes)

    def rename_constraint(self, model_id: str, uid: str, name: str) -> ModelSpec:
        record = self.models[model_id]
        name = (name or "").strip()
        if not name:
            raise EditError("Constraint names can't be empty.")
        if any(c.name == name and c.uid != uid for c in record.working.constraints):
            raise EditError(f"A constraint named '{name}' already exists.")
        return self._replace_constraint(record, uid, name=name)

    def remove_constraint(self, model_id: str, uid: str) -> ModelSpec:
        record = self.models[model_id]
        self._constraint(record, uid)
        if len(record.working.constraints) == 1:
            raise EditError("A model needs at least one constraint.")
        constraints = [c for c in record.working.constraints if c.uid != uid]
        return self._commit(record, replace(record.working, constraints=constraints))

    def add_constraint(self, model_id: str, name: Optional[str] = None, expression: Optional[LinearExpression] = None,
                       sense: str = "<=", rhs: float = 0.0) -> ConstraintSpec:
        record = self.models[model_id]
        spec = record.working
        if expression is None:
            first = spec.variables[0].name
            expression = LinearExpression({first: 1.0})
        _check_names(spec, expression)
        existing = {c.name for c in spec.constraints}
        if not name:
            index = len(spec.constraints) + 1
            while f"constraint_{index}" in existing:
                index += 1
            name = f"constraint_{index}"
        elif name in existing:
            raise EditError(f"A constraint named '{name}' already exists.")
        constraint = ConstraintSpec(name, expression, sense, float(rhs), "editor", spec.new_uid("c"))
        self._commit(record, replace(spec, constraints=[*spec.constraints, constraint]))
        return constraint

    def set_objective(self, model_id: str, expression: Optional[LinearExpression] = None, sense: Optional[str] = None) -> ModelSpec:
        record = self.models[model_id]
        objective = record.working.objective
        if expression is not None:
            _check_names(record.working, expression)
            if not expression.coefficients:
                raise EditError("The objective needs at least one variable.")
            objective = replace(objective, expression=expression)
        if sense is not None:
            if sense not in ("maximize", "minimize"):
                raise EditError("Choose Maximize or Minimize.")
            objective = replace(objective, sense=sense)
        return self._commit(record, replace(record.working, objective=objective))

    def add_variable(self, model_id: str, name: str, variable_type: str = "continuous",
                     lower: Optional[float] = 0.0, upper: Optional[float] = None) -> VariableSpec:
        record = self.models[model_id]
        name = (name or "").strip()
        if not name or any(ch.isspace() for ch in name):
            raise EditError("Variable names need at least one character and no spaces.")
        if name in record.working.variable_map():
            raise EditError(f"A variable named '{name}' already exists.")
        variable = _make_variable(name, variable_type, lower, upper, record.working.new_uid("v"))
        self._commit(record, replace(record.working, variables=[*record.working.variables, variable]))
        return variable

    def set_variable(self, model_id: str, uid: str, variable_type: str, lower: Optional[float], upper: Optional[float]) -> ModelSpec:
        record = self.models[model_id]
        variables = list(record.working.variables)
        for index, variable in enumerate(variables):
            if variable.uid == uid:
                variables[index] = _make_variable(variable.name, variable_type, lower, upper, uid)
                return self._commit(record, replace(record.working, variables=variables))
        raise EditError("That variable no longer exists.")

    def rename_variable(self, model_id: str, uid: str, new_name: str) -> ModelSpec:
        record = self.models[model_id]
        spec = record.working
        new_name = (new_name or "").strip()
        variable = spec.variable_by_uid(uid)
        if variable is None:
            raise EditError("That variable no longer exists.")
        if not new_name or any(ch.isspace() for ch in new_name):
            raise EditError("Variable names need at least one character and no spaces.")
        if new_name == variable.name:
            return spec
        if new_name in spec.variable_map():
            raise EditError(f"A variable named '{new_name}' already exists.")
        old = variable.name
        variables = [replace(v, name=new_name) if v.uid == uid else v for v in spec.variables]
        objective = replace(spec.objective, expression=spec.objective.expression.renamed(old, new_name))
        constraints = [replace(c, expression=c.expression.renamed(old, new_name)) for c in spec.constraints]
        return self._commit(record, replace(spec, variables=variables, objective=objective, constraints=constraints))

    def variable_impact(self, model_id: str, uid: str) -> Dict[str, Any]:
        spec = self.models[model_id].working
        variable = spec.variable_by_uid(uid)
        if variable is None:
            raise EditError("That variable no longer exists.")
        name = variable.name
        uses = [(c.name, c.expression.coefficients[name]) for c in spec.constraints if name in c.expression.coefficients]
        emptied = [c.name for c in spec.constraints if set(c.expression.coefficients) == {name}]
        objective_only = set(spec.objective.expression.coefficients) == {name}
        return {
            "name": name,
            "objective": spec.objective.expression.coefficients.get(name),
            "constraints": uses,
            "emptied_constraints": emptied,
            "objective_would_be_empty": objective_only,
        }

    def remove_variable(self, model_id: str, uid: str) -> ModelSpec:
        """Remove a variable, dropping its terms. Constraints left with no
        variables are removed too so the draft stays valid."""
        record = self.models[model_id]
        spec = record.working
        impact = self.variable_impact(model_id, uid)
        if len(spec.variables) == 1:
            raise EditError("A model needs at least one variable.")
        if impact["objective_would_be_empty"]:
            raise EditError(f"'{impact['name']}' is the only variable in the objective; edit the objective first.")
        name = impact["name"]
        variables = [v for v in spec.variables if v.uid != uid]
        objective = replace(spec.objective, expression=spec.objective.expression.without(name))
        constraints = [replace(c, expression=c.expression.without(name)) for c in spec.constraints
                       if c.name not in impact["emptied_constraints"]]
        if not constraints:
            raise EditError("Removing this variable would leave no constraints.")
        return self._commit(record, replace(spec, variables=variables, objective=objective, constraints=constraints))

    def reset_to_baseline(self, model_id: str) -> None:
        record = self.models[model_id]
        record.working = record.baseline
        record.working_version += 1
        record.frozen[record.working_version] = "r0"
        for run_id in record.run_ids:
            run = self.runs[run_id]
            if run.revision_id != "r0":
                run.historical = True

    def open_revision(self, model_id: str, revision_id: str) -> None:
        record = self.models[model_id]
        spec = record.revisions[revision_id]
        record.working = spec
        record.working_version += 1
        record.frozen[record.working_version] = revision_id
        self.active_model_id = model_id

    def replace_working(self, model_id: str, spec: ModelSpec) -> None:
        record = self.models[model_id]
        self._commit(record, spec.with_uids())

    # ------------------------------------------------------------------
    #  Revisions and runs
    # ------------------------------------------------------------------
    def freeze(self, model_id: str) -> str:
        record = self.models[model_id]
        existing = record.frozen.get(record.working_version)
        if existing:
            return existing
        record.working.validate()
        for rev_id in record.revision_order:
            rev = record.revisions[rev_id]
            if rev.fingerprint() == record.working.fingerprint() and _same_names(rev, record.working):
                record.frozen[record.working_version] = rev_id
                return rev_id
        rev_id = f"r{len(record.revision_order)}"
        record.revisions[rev_id] = record.working
        record.revision_order.append(rev_id)
        record.frozen[record.working_version] = rev_id
        return rev_id

    def pending_run(self, model_id: str, revision_id: Optional[str], solver: Optional[str] = None) -> Optional[Run]:
        for run in self.runs.values():
            if run.model_id == model_id and run.pending and (revision_id is None or run.revision_id == revision_id):
                if solver is None or run.requested_solver == solver:
                    return run
        return None

    def submit_run(self, model_id: str, solver: str, time_limit: Optional[float], origin: str,
                   revision_id: Optional[str] = None, use_cache: bool = True) -> Run:
        record = self.models[model_id]
        if revision_id is None:
            revision_id = self.freeze(model_id)
        spec = record.revisions[revision_id]
        duplicate = self.pending_run(model_id, revision_id, solver)
        if duplicate is not None:
            return duplicate
        source = record.source
        mps_path = None
        miplib_name = source.get("miplib") if revision_id == "r0" else None
        if revision_id == "r0" and spec.metadata.get("mps_path") and solver in ("cvxpy_scip", "auto"):
            mps_path = spec.metadata.get("mps_path")
        plan = source.get("orlearn_plan") if revision_id == "r0" else None

        run = Run(id=_id("run"), model_id=model_id, revision_id=revision_id, origin=origin,
                  requested_solver=solver, time_limit=time_limit, job_id=None)

        if miplib_name and use_cache:
            from src.services import miplib_service

            cached = miplib_service.cached_solution(miplib_name, solver)
            if cached:
                run.status = "done"
                run.result = cached
                run.cache_hit = True
                run.finished = time.time()
                self.runs[run.id] = run
                record.run_ids.append(run.id)
                return run

        def work(job: jobs.Job) -> Dict[str, Any]:
            label = SOLVERS.get(solver, {}).get("label", solver)
            job.set_progress(f"Solving with {label}")
            result = solve_spec(spec, solver, time_limit, cancel=job.cancel_event, handle=job.handle,
                                mps_path=mps_path if (solver == "cvxpy_scip" or _auto_is_scip(spec, solver)) else None)
            if plan is not None:
                job.set_progress("Cross-checking with OR-Learn")
                try:
                    from src.modeling.orlearn_adapter import reference_solve

                    result["library_check"] = reference_solve(plan)
                except Exception as exc:
                    result["library_check"] = {"available": False, "error": str(exc)}
            if miplib_name and result.get("kind") in ("optimal", "feasible", "infeasible"):
                try:
                    from src.services import miplib_service

                    miplib_service.store_solution(miplib_name, solver, result)
                except Exception:
                    pass
            return result

        cancellable = solver == "cvxpy_scip" or _auto_is_scip(spec, solver)
        job = jobs.submit("solve", f"{record.name} · {record.revision_label(revision_id)}", work, cancellable=cancellable)
        run.job_id = job.id
        run.status = "running"
        self.runs[run.id] = run
        record.run_ids.append(run.id)
        return run

    def poll(self) -> List[str]:
        changed: List[str] = []
        for run in self.runs.values():
            if not run.pending or not run.job_id:
                continue
            job = jobs.get(run.job_id)
            if job is None:
                run.status = "failed"
                run.error = "The background job was lost (server restarted?)."
                changed.append(run.id)
                continue
            if job.done:
                run.finished = job.finished or time.time()
                if job.error:
                    run.status = "failed"
                    run.error = job.error
                else:
                    run.status = "done"
                    run.result = job.result
                    run.library_check = (job.result or {}).get("library_check")
                changed.append(run.id)
        for sweep in self.sweeps.values():
            if sweep.status != "running" or not sweep.job_id:
                continue
            job = jobs.get(sweep.job_id)
            if job is None:
                sweep.status = "failed"
                continue
            if job.done:
                if job.error:
                    sweep.status = "failed"
                    sweep.error = job.error
                else:
                    sweep.points = job.result or []
                    sweep.status = "cancelled" if job.cancel_event.is_set() else "done"
                changed.append(sweep.id)
        return changed

    def has_pending(self) -> bool:
        return any(r.pending for r in self.runs.values()) or any(s.status == "running" for s in self.sweeps.values())

    def runs_for(self, model_id: str) -> List[Run]:
        record = self.models[model_id]
        return [self.runs[r] for r in record.run_ids if r in self.runs]

    def latest_run(self, model_id: str, revision_id: Optional[str], include_pending: bool = False,
                   include_historical: bool = False) -> Optional[Run]:
        if revision_id is None:
            return None
        candidates = [r for r in self.runs_for(model_id) if r.revision_id == revision_id
                      and (include_pending or r.status == "done")
                      and (include_historical or not r.historical)]
        return candidates[-1] if candidates else None

    def baseline_run(self, model_id: str) -> Optional[Run]:
        return self.latest_run(model_id, "r0")

    def current_run(self, model_id: str) -> Optional[Run]:
        record = self.models[model_id]
        return self.latest_run(model_id, record.working_revision, include_pending=True)

    def has_unsolved_edits(self, model_id: str) -> bool:
        record = self.models[model_id]
        if not record.is_edited:
            return False
        rev = record.working_revision
        return rev is None or self.latest_run(model_id, rev, include_pending=True) is None

    def compare(self, model_id: str) -> Optional[Dict[str, Any]]:
        record = self.models[model_id]
        base = self.baseline_run(model_id)
        rev = record.working_revision
        if base is None or rev in (None, "r0"):
            return None
        edited = self.latest_run(model_id, rev)
        if edited is None:
            return None
        b, e = base.result or {}, edited.result or {}
        diff = None
        if b.get("objective") is not None and e.get("objective") is not None:
            diff = e["objective"] - b["objective"]
        names = list(dict.fromkeys([*b.get("variables", {}).keys(), *e.get("variables", {}).keys()]))
        rows = []
        for name in names:
            bv, ev = b.get("variables", {}).get(name), e.get("variables", {}).get(name)
            delta = (ev - bv) if (bv is not None and ev is not None) else None
            rows.append({"variable": name, "baseline": bv, "edited": ev, "change": delta})
        return {
            "baseline_run": base, "edited_run": edited,
            "baseline_objective": b.get("objective"), "edited_objective": e.get("objective"),
            "difference": diff, "baseline_status": b.get("status"), "edited_status": e.get("status"),
            "variables": rows, "changes": diff_specs(record.baseline, record.revisions[rev]),
        }

    # ------------------------------------------------------------------
    #  Sensitivity sweep (never mutates the working model)
    # ------------------------------------------------------------------
    def start_sweep(self, model_id: str, uid: str, values: List[float], solver: str, time_limit: Optional[float]) -> Sweep:
        record = self.models[model_id]
        revision_id = self.freeze(model_id)
        spec = record.revisions[revision_id]
        constraint = spec.constraint_by_uid(uid)
        if constraint is None:
            raise EditError("Pick a constraint to sweep.")
        if not values:
            raise EditError("Give at least one right-hand-side value.")
        if len(values) > 200:
            raise EditError("A sweep is limited to 200 points.")

        def work(job: jobs.Job) -> List[Dict[str, Any]]:
            points = []
            for index, value in enumerate(values):
                if job.cancel_event.is_set():
                    break
                job.set_progress(f"Point {index + 1} of {len(values)}", index / len(values), f"RHS = {value:g}")
                derived = replace(spec, constraints=[replace(c, rhs=float(value)) if c.uid == uid else c for c in spec.constraints])
                result = solve_spec(derived, solver, time_limit)
                points.append({
                    "rhs": float(value), "status": result["status"], "kind": result["kind"],
                    "objective": result["objective"], "solver": result.get("backend", ""),
                    "variables": result.get("variables", {}),
                })
            job.set_progress("Done", 1.0)
            return points

        job = jobs.submit("sweep", f"Sweep {constraint.name}", work, cancellable=True)
        sweep = Sweep(_id("sw"), model_id, revision_id, uid, constraint.name, [float(v) for v in values], solver, job.id)
        self.sweeps[sweep.id] = sweep
        record.sweep_ids.append(sweep.id)
        return sweep

    # ------------------------------------------------------------------
    #  Chat history
    # ------------------------------------------------------------------
    def add_message(self, role: str, kind: str, **payload: Any) -> Dict[str, Any]:
        message = {"id": _id("msg"), "role": role, "kind": kind, "time": time.time(), **payload}
        self.messages.append(message)
        return message

    def message(self, message_id: str) -> Optional[Dict[str, Any]]:
        return next((m for m in self.messages if m["id"] == message_id), None)


def _auto_is_scip(spec: ModelSpec, solver: str) -> bool:
    if solver != "auto":
        return False
    from src.solvers.backends import resolve

    resolved, _ = resolve(spec, "auto")
    return resolved == "cvxpy_scip"


def _same_names(a: ModelSpec, b: ModelSpec) -> bool:
    return [v.name for v in a.variables] == [v.name for v in b.variables] and [c.name for c in a.constraints] == [c.name for c in b.constraints]


def _check_names(spec: ModelSpec, expression: LinearExpression) -> None:
    known = spec.variable_map()
    unknown = [n for n in expression.coefficients if n not in known]
    if unknown:
        raise EditError(f"Unknown variable(s): {', '.join(unknown)}. Add them in the Variables table first.")


def _make_variable(name: str, variable_type: str, lower: Optional[float], upper: Optional[float], uid: str) -> VariableSpec:
    if variable_type not in ("continuous", "integer", "binary"):
        raise EditError("Domain must be continuous, integer, or binary.")
    if variable_type == "binary":
        lower = 0.0 if lower is None else lower
        upper = 1.0 if upper is None else upper
        if lower < 0 or upper > 1:
            raise EditError(f"Binary variable '{name}' must stay within [0, 1].")
    if lower is not None and upper is not None and lower > upper:
        raise EditError(f"'{name}': the lower bound is above the upper bound.")
    return VariableSpec(name, variable_type, lower, upper, uid)


def diff_specs(base: ModelSpec, other: ModelSpec) -> List[str]:
    changes: List[str] = []
    if base.objective.sense != other.objective.sense:
        changes.append(f"Objective direction: {base.objective.sense} → {other.objective.sense}")
    if base.objective.expression != other.objective.expression:
        changes.append("Objective expression changed")
    b_cons = {c.uid: c for c in base.constraints}
    o_cons = {c.uid: c for c in other.constraints}
    for uid, c in b_cons.items():
        if uid not in o_cons:
            changes.append(f"Constraint removed: {c.name}")
            continue
        o = o_cons[uid]
        if o.name != c.name:
            changes.append(f"Constraint renamed: {c.name} → {o.name}")
        if o.rhs != c.rhs:
            changes.append(f"{o.name} RHS: {c.rhs:g} → {o.rhs:g}")
        if o.sense != c.sense:
            changes.append(f"{o.name} relation: {c.sense} → {o.sense}")
        if o.expression != c.expression:
            changes.append(f"{o.name} expression changed")
    for uid, o in o_cons.items():
        if uid not in b_cons:
            changes.append(f"Constraint added: {o.name}")
    b_vars = {v.uid: v for v in base.variables}
    o_vars = {v.uid: v for v in other.variables}
    for uid, v in b_vars.items():
        if uid not in o_vars:
            changes.append(f"Variable removed: {v.name}")
            continue
        o = o_vars[uid]
        if o.name != v.name:
            changes.append(f"Variable renamed: {v.name} → {o.name}")
        if (o.variable_type, o.lower_bound, o.upper_bound) != (v.variable_type, v.lower_bound, v.upper_bound):
            changes.append(f"{o.name} domain/bounds changed")
    for uid, o in o_vars.items():
        if uid not in b_vars:
            changes.append(f"Variable added: {o.name}")
    return changes
