"""Solve a canonical ``ModelSpec`` with an explicitly chosen backend.

Manual selections are never silently replaced: if the requested backend is
unavailable or cannot handle the model (e.g. OSQP with integer variables) the
result explains why and nothing is solved.  ``auto`` picks a backend and says
which one and why.
"""

from __future__ import annotations

import math
import threading
import time
from typing import Any, Callable, Dict, List, Optional, Tuple

from src.modeling.model_spec import ModelSpec

SOLVERS: Dict[str, Dict[str, Any]] = {
    "auto": {"label": "Auto", "full": "Auto (chosen per model)", "mip": True, "lp": True, "cancel": False},
    "pulp_cbc": {"label": "CBC", "full": "COIN-OR CBC (via PuLP)", "mip": True, "lp": True, "cancel": False},
    "cvxpy_osqp": {"label": "OSQP", "full": "OSQP (via CVXPY)", "mip": False, "lp": True, "cancel": False},
    "cvxpy_glpk": {"label": "GLPK", "full": "GLPK (via CVXPY/CVXOPT)", "mip": True, "lp": True, "cancel": False},
    "cvxpy_scip": {"label": "SCIP", "full": "SCIP (via PySCIPOpt)", "mip": True, "lp": True, "cancel": True},
}
SOLVER_ORDER = ["auto", "pulp_cbc", "cvxpy_osqp", "cvxpy_glpk", "cvxpy_scip"]
_GLPK_LOCK = threading.Lock()
_AVAILABILITY: Optional[Dict[str, Dict[str, Any]]] = None


def _cbc_runs() -> Tuple[bool, str]:
    """Solve a one-variable LP so an unrunnable CBC binary is reported as missing."""
    import pulp

    try:
        probe = pulp.LpProblem("cbc_probe", pulp.LpMaximize)
        x = pulp.LpVariable("x", 0, 1)
        probe += x
        probe += x <= 1
        probe.solve(pulp.PULP_CBC_CMD(msg=False))
        return pulp.LpStatus[probe.status] == "Optimal", "no optimal answer"
    except Exception as exc:
        return False, str(exc).strip().splitlines()[0][:120] if str(exc).strip() else type(exc).__name__


def availability(refresh: bool = False) -> Dict[str, Dict[str, Any]]:
    global _AVAILABILITY
    if _AVAILABILITY is not None and not refresh:
        return _AVAILABILITY
    info: Dict[str, Dict[str, Any]] = {}
    try:
        import pulp

        ok = bool(pulp.PULP_CBC_CMD(msg=False).available())
        reason = "" if ok else "CBC binary not found in the PuLP install."
        if ok:
            # available() only checks the file exists. PuLP ships an x86_64 CBC for
            # macOS, so on Apple Silicon without Rosetta it is present but cannot run.
            ok, failure = _cbc_runs()
            if not ok:
                reason = f"The bundled CBC binary cannot run here ({failure})."
        info["pulp_cbc"] = {"available": ok, "version": f"PuLP {pulp.__version__}", "reason": reason}
    except Exception as exc:  # pragma: no cover
        info["pulp_cbc"] = {"available": False, "version": "", "reason": f"PuLP unavailable: {exc}"}
    try:
        import cvxpy as cp

        installed = set(cp.installed_solvers())
        version = f"CVXPY {cp.__version__}"
        info["cvxpy_osqp"] = {"available": "OSQP" in installed, "version": version, "reason": "" if "OSQP" in installed else "Install osqp."}
        glpk = {"GLPK", "GLPK_MI"} <= installed
        info["cvxpy_glpk"] = {"available": glpk, "version": version + " + CVXOPT", "reason": "" if glpk else "Install cvxopt (provides GLPK)."}
    except Exception as exc:
        for key in ("cvxpy_osqp", "cvxpy_glpk"):
            info[key] = {"available": False, "version": "", "reason": f"CVXPY unavailable: {exc}"}
    try:
        import pyscipopt

        scip_version = ""
        try:
            scip_version = f"SCIP {pyscipopt.Model().version()}"
        except Exception:
            pass
        info["cvxpy_scip"] = {"available": True, "version": f"PySCIPOpt {pyscipopt.__version__} {scip_version}".strip(), "reason": ""}
    except Exception:
        info["cvxpy_scip"] = {"available": False, "version": "", "reason": "Install pyscipopt (bundles SCIP)."}
    info["auto"] = {"available": True, "version": "", "reason": ""}
    _AVAILABILITY = info
    return info


def compatibility(spec: ModelSpec, key: str) -> Tuple[bool, str]:
    if key not in SOLVERS:
        return False, f"Unknown solver '{key}'."
    if key == "auto":
        return True, ""
    avail = availability()[key]
    if not avail["available"]:
        return False, f"{SOLVERS[key]['full']} is not installed here. {avail['reason']}"
    if spec.is_mip and not SOLVERS[key]["mip"]:
        n_int = sum(1 for v in spec.variables if v.variable_type != "continuous")
        return False, (
            f"{SOLVERS[key]['label']} solves continuous problems only, and this model has "
            f"{n_int} integer/binary variable(s). Choose CBC, GLPK, SCIP, or Auto."
        )
    return True, ""


def resolve(spec: ModelSpec, key: str) -> Tuple[Optional[str], str]:
    if key != "auto":
        ok, reason = compatibility(spec, key)
        return (key, f"Using {SOLVERS[key]['full']} as selected.") if ok else (None, reason)
    stats = spec.stats()
    avail = availability()
    if spec.is_mip and (stats["variables"] > 2000 or spec.metadata.get("miplib_instance")) and avail["cvxpy_scip"]["available"]:
        return "cvxpy_scip", f"Auto chose SCIP: integer model with {stats['variables']:,} variables."
    if avail["pulp_cbc"]["available"]:
        kind = "integer model" if spec.is_mip else "linear program"
        return "pulp_cbc", f"Auto chose CBC: {kind} with {stats['variables']:,} variables (exact simplex/branch-and-cut)."
    for fallback in ("cvxpy_scip", "cvxpy_glpk"):
        if avail[fallback]["available"]:
            return fallback, f"Auto chose {SOLVERS[fallback]['label']} (CBC is unavailable)."
    return None, "No compatible solver is installed."


def _result(**kwargs) -> Dict[str, Any]:
    base = {
        "status": "Error", "kind": "error", "objective": None, "variables": {}, "constraints": {},
        "reduced_costs": {}, "gap": None, "messages": [], "backend": "", "requested": "", "resolved": "",
        "explanation": "", "elapsed": 0.0, "solve_time": 0.0, "time_limit": None, "stats": {},
    }
    base.update(kwargs)
    return base


def _activities(spec: ModelSpec, values: Dict[str, Optional[float]], duals: Dict[str, float]) -> Dict[str, Dict[str, Any]]:
    rows: Dict[str, Dict[str, Any]] = {}
    for c in spec.constraints:
        try:
            activity = sum(coef * (values.get(n) or 0.0) for n, coef in c.expression.coefficients.items()) + c.expression.constant
        except TypeError:
            activity = None
        slack = None
        if activity is not None:
            slack = c.rhs - activity if c.sense == "<=" else (activity - c.rhs if c.sense == ">=" else 0.0)
        binding = slack is not None and abs(slack) <= 1e-6 * max(1.0, abs(c.rhs))
        rows[c.name] = {"activity": activity, "slack": slack, "dual": duals.get(c.name), "binding": binding, "sense": c.sense, "rhs": c.rhs}
    return rows


def solve_spec(
    spec: ModelSpec,
    key: str,
    time_limit: Optional[float] = 60,
    cancel: Optional[threading.Event] = None,
    handle: Optional[Dict[str, Any]] = None,
    mps_path: Optional[str] = None,
) -> Dict[str, Any]:
    start = time.perf_counter()
    stats = spec.stats()
    issues = spec.issues()
    if issues:
        return _result(status="Invalid model", kind="error", requested=key, stats=stats,
                       messages=[i["message"] for i in issues])
    resolved, explanation = resolve(spec, key)
    if resolved is None:
        return _result(status="Not run", kind="unsupported", requested=key, explanation=explanation,
                       messages=[explanation], stats=stats)
    if cancel is not None and cancel.is_set():
        return _result(status="Cancelled", kind="cancelled", requested=key, resolved=resolved, stats=stats)
    runner = {"pulp_cbc": _solve_cbc, "cvxpy_osqp": _solve_cvxpy, "cvxpy_glpk": _solve_cvxpy, "cvxpy_scip": _solve_scip}[resolved]
    try:
        result = runner(spec, resolved, time_limit, cancel, handle if handle is not None else {}, mps_path)
    except Exception as exc:  # solver crashed: report it, never hide it
        result = _result(status="Error", kind="error", messages=[f"{SOLVERS[resolved]['full']} failed: {exc}"])
    if result["kind"] not in ("cancelled",) and cancel is not None and cancel.is_set():
        result["messages"].append("Cancellation was requested but this solver finished first.")
    result.update(
        requested=key, resolved=resolved, explanation=explanation, stats=stats, time_limit=time_limit,
        elapsed=round(time.perf_counter() - start, 4),
    )
    if not result.get("backend"):
        result["backend"] = SOLVERS[resolved]["full"]
    version = availability()[resolved].get("version")
    if version:
        result["backend_version"] = version
    return result


# ---------------------------------------------------------------------------
#  CBC via PuLP
# ---------------------------------------------------------------------------

def _solve_cbc(spec, key, time_limit, cancel, handle, mps_path):
    import pulp

    sense = pulp.LpMaximize if spec.objective.sense == "maximize" else pulp.LpMinimize
    prob = pulp.LpProblem("orstudio", sense)
    cat = {"continuous": pulp.LpContinuous, "integer": pulp.LpInteger, "binary": pulp.LpBinary}
    pv: Dict[str, Any] = {}
    for i, v in enumerate(spec.variables):
        pv[v.name] = pulp.LpVariable(f"v{i}", lowBound=v.lower_bound, upBound=v.upper_bound, cat=cat[v.variable_type])
    prob += pulp.LpAffineExpression([(pv[n], c) for n, c in spec.objective.expression.coefficients.items()],
                                    constant=spec.objective.expression.constant)
    cname: Dict[str, str] = {}
    for j, c in enumerate(spec.constraints):
        expr = pulp.LpAffineExpression([(pv[n], coef) for n, coef in c.expression.coefficients.items()],
                                       constant=c.expression.constant)
        safe = f"c{j}"
        cname[safe] = c.name
        if c.sense == "<=":
            prob += pulp.LpConstraint(expr, pulp.LpConstraintLE, safe, c.rhs)
        elif c.sense == ">=":
            prob += pulp.LpConstraint(expr, pulp.LpConstraintGE, safe, c.rhs)
        else:
            prob += pulp.LpConstraint(expr, pulp.LpConstraintEQ, safe, c.rhs)
    solver = pulp.PULP_CBC_CMD(msg=False, timeLimit=time_limit if time_limit else None)
    t0 = time.perf_counter()
    prob.solve(solver)
    solve_time = time.perf_counter() - t0
    sol_status = getattr(prob, "sol_status", None)
    status_code = prob.status
    messages: List[str] = []
    hit_limit = bool(time_limit) and solve_time >= 0.95 * float(time_limit)
    if sol_status == pulp.LpSolutionOptimal or (sol_status is None and status_code == 1):
        status, kind = "Optimal", "optimal"
    elif sol_status == pulp.LpSolutionIntegerFeasible:
        status, kind = "Feasible (time limit)", "feasible"
        messages.append(f"CBC stopped at the {time_limit:g}s time limit with a feasible, not proven optimal, solution.")
    elif status_code == -1 or sol_status == pulp.LpSolutionInfeasible:
        status, kind = "Infeasible", "infeasible"
    elif status_code == -2 or sol_status == pulp.LpSolutionUnbounded:
        status, kind = "Unbounded", "unbounded"
    elif hit_limit:
        status, kind = "Time limit (no solution)", "no_solution"
        messages.append(f"CBC found no feasible solution within {time_limit:g}s.")
    else:
        status, kind = pulp.LpStatus.get(status_code, "Not solved"), "error"
    values: Dict[str, Optional[float]] = {}
    duals: Dict[str, float] = {}
    reduced: Dict[str, float] = {}
    objective = None
    if kind in ("optimal", "feasible"):
        values = {n: (var.varValue if var.varValue is not None else None) for n, var in pv.items()}
        objective = pulp.value(prob.objective)
        if objective is None:
            objective = spec.objective.expression.constant
        if not spec.is_mip and kind == "optimal":
            for safe, con in prob.constraints.items():
                if con.pi is not None:
                    duals[cname[safe]] = float(con.pi)
            for n, var in pv.items():
                if var.dj is not None:
                    reduced[n] = float(var.dj)
    return _result(
        status=status, kind=kind, objective=objective, variables=values,
        constraints=_activities(spec, values, duals) if values else {}, reduced_costs=reduced,
        messages=messages, solve_time=round(solve_time, 4), backend=SOLVERS[key]["full"],
    )


# ---------------------------------------------------------------------------
#  CVXPY (OSQP, GLPK)
# ---------------------------------------------------------------------------

def _solve_cvxpy(spec, key, time_limit, cancel, handle, mps_path):
    import cvxpy as cp
    import numpy as np
    import scipy.sparse as sp

    names = [v.name for v in spec.variables]
    index = {n: i for i, n in enumerate(names)}
    n = len(names)
    # CVXPY 1.9 + GLPK_MI rejects partially-integer vectors, so integer and
    # continuous columns live in separate variables joined by a permutation.
    int_cols = [i for i, v in enumerate(spec.variables) if v.variable_type != "continuous"]
    cont_cols = [i for i, v in enumerate(spec.variables) if v.variable_type == "continuous"]
    parts = []
    perm_rows, perm_cols = [], []
    if cont_cols:
        xc = cp.Variable(len(cont_cols))
        parts.append(xc)
    if int_cols:
        xi = cp.Variable(len(int_cols), integer=True)
        parts.append(xi)
    stacked = parts[0] if len(parts) == 1 else cp.hstack(parts)
    order = cont_cols + int_cols
    for position, column in enumerate(order):
        perm_rows.append(column)
        perm_cols.append(position)
    P = sp.csr_matrix((np.ones(n), (perm_rows, perm_cols)), shape=(n, n))
    x = P @ stacked
    c = np.zeros(n)
    for name, coef in spec.objective.expression.coefficients.items():
        c[index[name]] = coef
    objective_expr = c @ x + spec.objective.expression.constant
    objective = cp.Maximize(objective_expr) if spec.objective.sense == "maximize" else cp.Minimize(objective_expr)

    groups: Dict[str, List[int]] = {"<=": [], ">=": [], "=": []}
    for j, con in enumerate(spec.constraints):
        groups[con.sense].append(j)
    constraints = []
    con_refs: List[Tuple[Any, List[int], float]] = []
    for sense, rows in groups.items():
        if not rows:
            continue
        data, ri, ci = [], [], []
        b = np.zeros(len(rows))
        for r, j in enumerate(rows):
            con = spec.constraints[j]
            for name, coef in con.expression.coefficients.items():
                data.append(coef)
                ri.append(r)
                ci.append(index[name])
            b[r] = con.rhs - con.expression.constant
        A = sp.csr_matrix((data, (ri, ci)), shape=(len(rows), n))
        if sense == "<=":
            cons = A @ x <= b
            sign = 1.0
        elif sense == ">=":
            cons = A @ x >= b
            sign = 1.0
        else:
            cons = A @ x == b
            sign = 1.0
        constraints.append(cons)
        con_refs.append((cons, rows, sign))
    lb_idx = [i for i, v in enumerate(spec.variables) if v.lower_bound is not None]
    ub_idx = [i for i, v in enumerate(spec.variables) if v.upper_bound is not None]
    if lb_idx:
        constraints.append(x[lb_idx] >= np.array([spec.variables[i].lower_bound for i in lb_idx]))
    if ub_idx:
        constraints.append(x[ub_idx] <= np.array([spec.variables[i].upper_bound for i in ub_idx]))
    prob = cp.Problem(objective, constraints)

    messages: List[str] = []
    t0 = time.perf_counter()
    if key == "cvxpy_osqp":
        kwargs = {"solver": cp.OSQP, "eps_abs": 1e-8, "eps_rel": 1e-8, "max_iter": 200000, "polishing": True}
        if time_limit:
            kwargs["time_limit"] = float(time_limit)
        prob.solve(**kwargs)
        backend = SOLVERS[key]["full"]
        messages.append("OSQP is a first-order method; values are accurate to its tolerance (1e-8).")
    else:
        with _GLPK_LOCK:
            if spec.is_mip:
                kwargs = {"solver": cp.GLPK_MI}
                if time_limit:
                    kwargs["tm_lim"] = int(float(time_limit) * 1000)
                prob.solve(**kwargs)
                backend = "GLPK_MI (via CVXPY/CVXOPT)"
            else:
                kwargs = {"solver": cp.GLPK}
                if time_limit:
                    kwargs["glpk"] = {"tm_lim": int(float(time_limit) * 1000)}
                prob.solve(**kwargs)
                backend = "GLPK simplex (via CVXPY/CVXOPT)"
    solve_time = time.perf_counter() - t0
    raw = prob.status
    hit_limit = bool(time_limit) and solve_time >= 0.95 * float(time_limit)
    has_values = all(part.value is not None for part in parts)
    if raw == "optimal" and not hit_limit:
        status, kind = "Optimal", "optimal"
    elif raw in ("optimal", "optimal_inaccurate", "user_limit") and has_values and hit_limit:
        status, kind = "Feasible (time limit)", "feasible"
        messages.append(f"Stopped at the {time_limit:g}s time limit; the solution is not proven optimal.")
    elif raw == "optimal_inaccurate" and has_values:
        status, kind = "Optimal (inaccurate)", "optimal"
        messages.append("The solver reports the solution as numerically inaccurate.")
    elif raw in ("infeasible", "infeasible_inaccurate"):
        status, kind = "Infeasible", "infeasible"
    elif raw in ("unbounded", "unbounded_inaccurate"):
        status, kind = "Unbounded", "unbounded"
    elif hit_limit:
        status, kind = "Time limit (no solution)", "no_solution"
    else:
        status, kind = f"Solver status: {raw}", "error"
    values: Dict[str, Optional[float]] = {}
    duals: Dict[str, float] = {}
    obj_value = None
    if kind in ("optimal", "feasible") and has_values:
        vec = np.asarray(P @ np.concatenate([np.asarray(p.value).ravel() for p in parts])).ravel()
        values = {name: float(vec[i]) for i, name in enumerate(names)}
        obj_value = float(prob.value) if prob.value is not None else None
        if not spec.is_mip:
            for cons, rows, sign in con_refs:
                dual = cons.dual_value
                if dual is None:
                    continue
                dual = np.asarray(dual).ravel()
                for r, j in enumerate(rows):
                    duals[spec.constraints[j].name] = float(dual[r]) * sign
    return _result(
        status=status, kind=kind, objective=obj_value, variables=values,
        constraints=_activities(spec, values, duals) if values else {}, messages=messages,
        solve_time=round(solve_time, 4), backend=backend,
    )


# ---------------------------------------------------------------------------
#  SCIP via PySCIPOpt
# ---------------------------------------------------------------------------

def _solve_scip(spec, key, time_limit, cancel, handle, mps_path):
    from pyscipopt import Model, quicksum

    model = Model("orstudio")
    model.hideOutput()
    if time_limit:
        model.setParam("limits/time", float(time_limit))
    handle["interrupt"] = model.interruptSolve
    names: Dict[str, Any] = {}
    messages: List[str] = []
    if mps_path:
        import gzip
        import os
        import tempfile

        path = mps_path
        if mps_path.endswith(".gz"):
            tmp = tempfile.NamedTemporaryFile(suffix=".mps", delete=False)
            with gzip.open(mps_path, "rb") as fin:
                tmp.write(fin.read())
            tmp.close()
            path = tmp.name
        model.readProblem(path)
        if path != mps_path:
            os.unlink(path)
        names = {v.name: v for v in model.getVars()}
        messages.append("SCIP read the original MPS file directly.")
    else:
        vtype = {"continuous": "C", "integer": "I", "binary": "B"}
        for i, v in enumerate(spec.variables):
            names[v.name] = model.addVar(name=f"v{i}", vtype=vtype[v.variable_type], lb=v.lower_bound, ub=v.upper_bound)
        expr = quicksum(coef * names[n] for n, coef in spec.objective.expression.coefficients.items())
        model.setObjective(expr, "maximize" if spec.objective.sense == "maximize" else "minimize")
        if spec.objective.expression.constant:
            model.addObjoffset(spec.objective.expression.constant)
        for j, c in enumerate(spec.constraints):
            lhs = quicksum(coef * names[n] for n, coef in c.expression.coefficients.items()) + c.expression.constant
            if c.sense == "<=":
                model.addCons(lhs <= c.rhs, name=f"c{j}")
            elif c.sense == ">=":
                model.addCons(lhs >= c.rhs, name=f"c{j}")
            else:
                model.addCons(lhs == c.rhs, name=f"c{j}")
    if cancel is not None and cancel.is_set():
        return _result(status="Cancelled", kind="cancelled", backend=SOLVERS[key]["full"])
    t0 = time.perf_counter()
    # optimize() keeps the GIL for the whole solve, which would block both the
    # UI thread and interruptSolve(); optimizeNogil() releases it.
    if hasattr(model, "optimizeNogil"):
        model.optimizeNogil()
    else:
        model.optimize()
    solve_time = time.perf_counter() - t0
    raw = model.getStatus()
    has_sol = model.getNSols() > 0
    gap = None
    if raw == "optimal":
        status, kind = "Optimal", "optimal"
    elif raw == "userinterrupt":
        status, kind = ("Cancelled (best solution kept)", "cancelled") if has_sol else ("Cancelled", "cancelled")
    elif raw in ("timelimit", "gaplimit", "nodelimit", "sollimit", "memlimit", "totalnodelimit", "stallnodelimit") and has_sol:
        status, kind = "Feasible (time limit)" if raw == "timelimit" else f"Feasible ({raw})", "feasible"
    elif raw == "timelimit":
        status, kind = "Time limit (no solution)", "no_solution"
    elif raw == "infeasible":
        status, kind = "Infeasible", "infeasible"
    elif raw == "unbounded":
        status, kind = "Unbounded", "unbounded"
    elif raw == "inforunbd":
        status, kind = "Infeasible or unbounded", "infeasible"
    else:
        status, kind = f"SCIP status: {raw}", "error"
    values: Dict[str, Optional[float]] = {}
    objective = None
    if has_sol and kind in ("optimal", "feasible", "cancelled"):
        best = model.getBestSol()
        values = {n: float(model.getSolVal(best, var)) for n, var in names.items()}
        objective = float(model.getSolObjVal(best))
        if kind != "optimal":
            try:
                gap = float(model.getGap())
                if math.isfinite(gap) and gap < 10:
                    messages.append(f"Relative MIP gap at stop: {gap:.2%}.")
                else:
                    gap = None
                    messages.append(f"Best bound so far: {model.getDualbound():g} (relative gap undefined).")
            except Exception:
                pass
    if kind == "feasible" and raw == "timelimit":
        messages.append(f"SCIP stopped at the {time_limit:g}s time limit; the solution is feasible, not proven optimal.")
    if mps_path:
        spec_names = {v.name for v in spec.variables}
        values = {k: v for k, v in values.items() if k in spec_names}
    return _result(
        status=status, kind=kind, objective=objective, variables=values,
        constraints=_activities(spec, values, {}) if values and len(spec.constraints) <= 20000 else {},
        gap=gap, messages=messages, solve_time=round(solve_time, 4), backend=SOLVERS[key]["full"],
    )
