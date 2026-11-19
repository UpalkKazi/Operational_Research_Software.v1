"""Convert PuLP models (e.g. from the AI model generator) to ``ModelSpec``."""

from __future__ import annotations

import pulp

from .model_spec import ConstraintSpec, LinearExpression, ModelSpec, ObjectiveSpec, VariableSpec


def pulp_to_spec(model: pulp.LpProblem, name: str = "", source_syntax: str = "ai") -> ModelSpec:
    cats = {pulp.LpContinuous: "continuous", pulp.LpInteger: "integer", pulp.LpBinary: "binary"}
    variables = []
    for var in model.variables():
        vtype = cats.get(var.cat, "continuous")
        lower, upper = var.lowBound, var.upBound
        if vtype == "integer" and lower == 0 and upper == 1:
            vtype = "binary"
        variables.append(VariableSpec(var.name, vtype, None if lower is None else float(lower), None if upper is None else float(upper)))
    objective_expr = model.objective if model.objective is not None else pulp.LpAffineExpression()
    objective = ObjectiveSpec(
        "maximize" if model.sense == pulp.LpMaximize else "minimize",
        LinearExpression({v.name: float(c) for v, c in objective_expr.items()}, float(objective_expr.constant or 0.0)),
        getattr(objective_expr, "name", None) or "objective",
    )
    senses = {pulp.LpConstraintLE: "<=", pulp.LpConstraintGE: ">=", pulp.LpConstraintEQ: "="}
    constraints = []
    for cname, con in model.constraints.items():
        coefficients = {v.name: float(c) for v, c in con.items() if float(c) != 0.0}
        constraints.append(ConstraintSpec(cname, LinearExpression(coefficients), senses[con.sense], -float(con.constant), source_syntax))
    return ModelSpec(name or model.name or "Generated model", variables, objective, constraints, source_syntax).with_uids()
