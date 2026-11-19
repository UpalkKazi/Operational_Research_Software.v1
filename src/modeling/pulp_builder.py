"""Build a PuLP model from the canonical ModelSpec."""

from __future__ import annotations

import pulp

from .model_spec import ModelSpec

_CATEGORIES = {
    "continuous": pulp.LpContinuous,
    "integer": pulp.LpInteger,
    "binary": pulp.LpBinary,
}


def build_pulp_model(spec: ModelSpec) -> pulp.LpProblem:
    spec.validate()
    direction = (
        pulp.LpMaximize if spec.objective.sense == "maximize" else pulp.LpMinimize
    )
    problem = pulp.LpProblem(spec.name, direction)
    variables = {}

    for item in spec.variables:
        lower = item.lower_bound
        upper = item.upper_bound
        if item.variable_type == "binary":
            lower, upper = 0, 1
        variables[item.name] = pulp.LpVariable(
            item.name,
            lowBound=lower,
            upBound=upper,
            cat=_CATEGORIES[item.variable_type],
        )

    objective = (
        pulp.lpSum(
            coefficient * variables[name]
            for name, coefficient in spec.objective.expression.coefficients.items()
        )
        + spec.objective.expression.constant
    )
    problem += objective, spec.objective.name

    for constraint in spec.constraints:
        left = (
            pulp.lpSum(
                coefficient * variables[name]
                for name, coefficient in constraint.expression.coefficients.items()
            )
            + constraint.expression.constant
        )
        if constraint.sense == "<=":
            problem += left <= constraint.rhs, constraint.name
        elif constraint.sense == ">=":
            problem += left >= constraint.rhs, constraint.name
        else:
            problem += left == constraint.rhs, constraint.name
    return problem
