"""Validated adapter around the real OR-Learn library.

A call plan produced by :func:`parse_orlearn_plan` is replayed against
``orlearn`` (pinned in ``requirements-orlearn.txt``).  The canonical model is
then read back from the library object's own state, so OR Studio solves the
model exactly as OR-Learn understood it.  ``reference_solve`` runs OR-Learn's
own ``solve()``/``assign()``/network method so results can be cross-checked.
"""

from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .model_spec import ConstraintSpec, LinearExpression, ModelSpec, ObjectiveSpec, VariableSpec
from .orlearn_parser import ORLearnParseError, ORLearnPlan

PINNED_COMMIT = "38355732feae2c6cc776d58b6f01491bbce78124"
REPOSITORY = "https://github.com/harunpirim/orlearn"


class ORLearnUnavailable(RuntimeError):
    """Raised when the optional OR-Learn package is not installed."""


@dataclass
class ORLearnOutcome:
    kind: str  # "lp" | "transport" | "assign" | "network"
    spec: Optional[ModelSpec]
    invoked: List[str]
    library: Dict[str, str]
    notes: List[str] = field(default_factory=list)
    unsupported_reason: str = ""
    labels: Dict[str, Any] = field(default_factory=dict)


def library_info() -> Dict[str, str]:
    try:
        import orlearn  # noqa: F401
    except ImportError as exc:
        raise ORLearnUnavailable(
            "The OR-Learn library is not installed. Install it with "
            "'pip install -r requirements-orlearn.txt'."
        ) from exc
    import orlearn
    from importlib import metadata

    info = {"package": "orlearn", "version": getattr(orlearn, "__version__", "?"), "commit": "", "repository": REPOSITORY}
    try:
        raw = metadata.distribution("orlearn").read_text("direct_url.json")
        if raw:
            direct = json.loads(raw)
            info["commit"] = direct.get("vcs_info", {}).get("commit_id", "")
            archive = re.search(r"/archive/([0-9a-f]{40})\.(zip|tar\.gz)$", direct.get("url", ""))
            if not info["commit"] and archive:
                info["commit"] = archive.group(1)
    except Exception:
        pass
    info["pinned"] = "yes" if info["commit"] == PINNED_COMMIT else ("unknown" if not info["commit"] else "no")
    return info


def _number(value: Any, what: str, line: int) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(float(value)):
        raise ORLearnParseError(f"{what} must be a finite number (got {value!r}).", line)
    return float(value)


def _numbers(values: Any, what: str, line: int) -> List[float]:
    if not isinstance(values, (list, tuple)) or not values:
        raise ORLearnParseError(f"{what} must be a non-empty list of numbers.", line)
    return [_number(v, what, line) for v in values]


def _matrix(values: Any, what: str, line: int) -> List[List[float]]:
    if not isinstance(values, (list, tuple)) or not values:
        raise ORLearnParseError(f"{what} must be a list of rows.", line)
    rows = [_numbers(r, what, line) for r in values]
    width = len(rows[0])
    if any(len(r) != width for r in rows):
        raise ORLearnParseError(f"Every row of {what} must have the same length.", line)
    return rows


def _validate_plan_values(plan: ORLearnPlan) -> None:
    width: Optional[int] = None
    for call in plan.all_calls:
        kw = call.kwargs
        if call.method in ("maximize", "minimize"):
            coefficients = _numbers(kw.get("coefficients"), "Objective coefficients", call.line)
            width = len(coefficients)
            names = kw.get("names")
            if names is not None:
                if not isinstance(names, (list, tuple)) or not all(isinstance(n, str) and n.strip() for n in names):
                    raise ORLearnParseError("names= must be a list of non-empty strings.", call.line)
                if len(names) != width:
                    raise ORLearnParseError(
                        f"names= has {len(names)} entries but there are {width} coefficients.", call.line
                    )
                if len(set(names)) != len(names):
                    raise ORLearnParseError("Variable names must be unique.", call.line)
        elif call.method in ("subject_to", "st"):
            coefficients = _numbers(kw.get("coefficients"), "Constraint coefficients", call.line)
            if width is not None and len(coefficients) != width:
                raise ORLearnParseError(
                    f"This constraint has {len(coefficients)} coefficients; the objective has {width}.", call.line
                )
            if kw.get("sense") not in ("<=", ">=", "="):
                raise ORLearnParseError("Constraint sense must be '<=', '>=', or '='.", call.line)
            _number(kw.get("rhs"), "Right-hand side", call.line)
            if "name" in kw and kw["name"] is not None and not isinstance(kw["name"], str):
                raise ORLearnParseError("Constraint name must be a string.", call.line)
        elif call.method == "transport":
            _numbers(kw.get("supply"), "supply", call.line)
            _numbers(kw.get("demand"), "demand", call.line)
        elif call.method in ("costs", "assign"):
            _matrix(kw.get("cost_matrix"), "the cost matrix", call.line)
        elif call.method == "network":
            edges = kw.get("edges")
            if not isinstance(edges, (list, tuple)) or not edges:
                raise ORLearnParseError("network() needs a list of (from, to, weight) edges.", call.line)
            for edge in edges:
                if not isinstance(edge, (list, tuple)) or len(edge) != 3:
                    raise ORLearnParseError("Each edge must be (from, to, weight).", call.line)
                _number(edge[2], "Edge weight", call.line)
    if width is not None:
        for call in plan.all_calls:
            if call.method in ("subject_to", "st") and len(call.kwargs.get("coefficients", [])) != width:
                raise ORLearnParseError("Constraint coefficient count does not match the objective.", call.line)


def _replay(plan: ORLearnPlan):
    """Invoke the library for every non-terminal call. Returns (object, invoked, notes, terminal)."""
    import orlearn

    invoked: List[str] = []
    notes: List[str] = []
    root = plan.root
    terminal = None
    obj = None
    if root.method in ("OR", "lp", "ip"):
        obj = getattr(orlearn, root.method)()
        invoked.append(f"orlearn.{root.method}()")
    elif root.method in ("transport", "network"):
        obj = getattr(orlearn, root.method)(**root.kwargs)
        invoked.append(f"orlearn.{root.render()}")
    elif root.method == "assign":
        terminal = root
    for call in plan.calls:
        if call.method in ("solve", "shortest_path", "max_flow", "mst", "assign"):
            terminal = call
            continue
        obj = getattr(obj, call.method)(**call.kwargs)
        invoked.append(f".{call.render()}")
    return obj, invoked, notes, terminal


def build_from_plan(plan: ORLearnPlan) -> ORLearnOutcome:
    info = library_info()
    _validate_plan_values(plan)
    obj, invoked, notes, terminal = _replay(plan)
    if plan.skipped:
        notes.append(
            "Not executed (display only): " + "; ".join(s.splitlines()[0][:60] for s in plan.skipped)
            + ". OR Studio shows the result card instead."
        )

    if terminal is not None and terminal.method == "assign":
        kwargs = dict(terminal.kwargs)
        labels = kwargs.pop("names", None)
        if labels is not None:
            notes.append(
                "names= is applied by OR Studio for display; OR-Learn 0.1.0's assign() does not accept it "
                "(the upstream README shows it, but the library signature is assign(cost_matrix))."
            )
        matrix = _matrix(kwargs["cost_matrix"], "the cost matrix", terminal.line)
        spec = _assignment_spec(matrix, labels, plan.text)
        invoked.append(f"orlearn.assign(cost_matrix={matrix!r})  [run at solve time]")
        return ORLearnOutcome("assign", spec, invoked, info, notes, labels={"rows": labels})

    if terminal is not None and terminal.method in ("shortest_path", "max_flow", "mst"):
        invoked.append(f".{terminal.render()}  [run at solve time]")
        return ORLearnOutcome(
            "network", None, invoked, info, notes,
            unsupported_reason=(
                f"OR-Learn {terminal.method}() is a graph algorithm, not a linear model. "
                "OR Studio runs it through OR-Learn and shows the result, but it cannot be opened in the Playground."
            ),
        )

    if getattr(obj, "_problem_type", "lp") == "transport":
        supply = _numbers(obj._supply, "supply", plan.root.line)
        demand = _numbers(obj._demand, "demand", plan.root.line)
        costs = _matrix(obj._costs, "the cost matrix", plan.root.line) if obj._costs else None
        if costs is None:
            raise ORLearnParseError("Call .costs([[...], ...]) before .solve() for a transportation problem.", plan.root.line)
        if len(costs) != len(supply) or len(costs[0]) != len(demand):
            raise ORLearnParseError(
                f"The cost matrix must be {len(supply)}×{len(demand)} (supply × demand).", plan.root.line
            )
        spec = _transport_spec(supply, demand, costs, plan.text)
        if terminal is not None:
            invoked.append(".solve()  [run at solve time for the library cross-check]")
        if abs(sum(supply) - sum(demand)) > 1e-9:
            notes.append(f"Unbalanced: total supply {sum(supply):g} vs demand {sum(demand):g}.")
        return ORLearnOutcome("transport", spec, invoked, info, notes)

    # LP / IP: read back the library's own state.
    if not obj._objective:
        raise ORLearnParseError("Call .maximize(...) or .minimize(...) to define the objective.", plan.root.line)
    names = list(obj._var_names)
    var_type = obj._var_type
    lower = 0.0
    upper = 1.0 if var_type == "binary" else None
    variables = [VariableSpec(n, var_type, lower, upper) for n in names]
    objective = ObjectiveSpec(obj._sense, LinearExpression(dict(zip(names, map(float, obj._objective)))), "objective")
    constraints = []
    for coefficients, sense, rhs, cname in obj._constraints:
        coeffs = {n: float(c) for n, c in zip(names, coefficients) if float(c) != 0.0}
        constraints.append(ConstraintSpec(str(cname), LinearExpression(coeffs), sense, float(rhs), "orlearn"))
    if not constraints:
        raise ORLearnParseError("Add at least one .subject_to(...) constraint.", plan.root.line)
    if terminal is None:
        notes.append("The chain has no .solve(); OR Studio solves it when you press Solve.")
    else:
        invoked.append(".solve()  [run at solve time for the library cross-check]")
    spec = ModelSpec(
        name="OR-Learn model",
        variables=variables,
        objective=objective,
        constraints=constraints,
        source_syntax="orlearn",
        source_text=plan.text,
        metadata={"orlearn_kind": "lp"},
    ).with_uids().validate()
    return ORLearnOutcome("lp", spec, invoked, info, notes)


def _transport_spec(supply, demand, costs, text) -> ModelSpec:
    srcs = [f"S{i + 1}" for i in range(len(supply))]
    dsts = [f"D{j + 1}" for j in range(len(demand))]
    variables, obj = [], {}
    for i, s in enumerate(srcs):
        for j, d in enumerate(dsts):
            name = f"x[{s},{d}]"
            variables.append(VariableSpec(name, "continuous", 0.0, None))
            obj[name] = costs[i][j]
    constraints = []
    for i, s in enumerate(srcs):
        constraints.append(ConstraintSpec(
            f"supply[{s}]", LinearExpression({f"x[{s},{d}]": 1.0 for d in dsts}), "<=", supply[i], "orlearn"))
    for j, d in enumerate(dsts):
        constraints.append(ConstraintSpec(
            f"demand[{d}]", LinearExpression({f"x[{s},{d}]": 1.0 for s in srcs}), ">=", demand[j], "orlearn"))
    return ModelSpec(
        "OR-Learn transportation", variables, ObjectiveSpec("minimize", LinearExpression(obj), "shipping_cost"),
        constraints, "orlearn", text, {"orlearn_kind": "transport"},
    ).with_uids().validate()


def _assignment_spec(matrix, labels, text) -> ModelSpec:
    rows = [str(l) for l in labels] if labels and len(labels) == len(matrix) else [f"R{i + 1}" for i in range(len(matrix))]
    cols = [f"C{j + 1}" for j in range(len(matrix[0]))]
    variables, obj = [], {}
    for i, r in enumerate(rows):
        for j, c in enumerate(cols):
            name = f"x[{r},{c}]"
            variables.append(VariableSpec(name, "binary", 0.0, 1.0))
            obj[name] = matrix[i][j]
    constraints = []
    row_sense = "=" if len(rows) <= len(cols) else "<="
    col_sense = "=" if len(cols) <= len(rows) else "<="
    for r in rows:
        constraints.append(ConstraintSpec(f"assign[{r}]", LinearExpression({f"x[{r},{c}]": 1.0 for c in cols}), row_sense, 1.0, "orlearn"))
    for c in cols:
        constraints.append(ConstraintSpec(f"cover[{c}]", LinearExpression({f"x[{r},{c}]": 1.0 for r in rows}), col_sense, 1.0, "orlearn"))
    return ModelSpec(
        "OR-Learn assignment", variables, ObjectiveSpec("minimize", LinearExpression(obj), "total_cost"),
        constraints, "orlearn", text, {"orlearn_kind": "assign"},
    ).with_uids().validate()


def reference_solve(plan: ORLearnPlan) -> Dict[str, Any]:
    """Run OR-Learn's own solver for the plan and return a plain dict."""
    obj, invoked, _notes, terminal = _replay(plan)
    import orlearn

    if terminal is None:
        if obj is None:
            return {"available": False}
        result = obj.solve()
        call = "solve()"
    elif terminal.method == "assign":
        kwargs = {k: v for k, v in terminal.kwargs.items() if k != "names"}
        result = orlearn.assign(**kwargs) if obj is None else obj.assign(**kwargs)
        call = "assign(cost_matrix)"
    else:
        result = getattr(obj, terminal.method)(**terminal.kwargs)
        call = terminal.render()
    solution = result._clean_solution() if hasattr(result, "_clean_solution") else dict(result.solution)
    value = result.value
    return {
        "available": True,
        "call": call,
        "optimal": bool(result.optimal),
        "value": float(value) if value is not None else None,
        "solution": solution,
    }


def build_orlearn_model(spec: ModelSpec):
    """Build an ``orlearn.OR`` object for a canonical LP/IP model (used for export)."""
    library_info()
    from orlearn import OR

    names = [v.name for v in spec.variables]
    types = {v.variable_type for v in spec.variables}
    if len(types) > 1:
        raise ValueError("OR-Learn's fluent API needs every variable to share one domain.")
    model = OR()
    coefficients = [spec.objective.expression.coefficients.get(n, 0.0) for n in names]
    model = model.maximize(coefficients, names=names) if spec.objective.sense == "maximize" else model.minimize(coefficients, names=names)
    for c in spec.constraints:
        model = model.subject_to([c.expression.coefficients.get(n, 0.0) for n in names], c.sense, c.rhs, c.name)
    domain = types.pop()
    if domain == "binary":
        model = model.as_binary()
    elif domain == "integer":
        model = model.as_integer()
    return model
