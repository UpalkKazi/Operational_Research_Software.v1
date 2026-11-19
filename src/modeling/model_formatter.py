"""Human-readable formatting for canonical models."""

from __future__ import annotations

from typing import Dict, List

from .linear_expression import format_expression, format_number
from .model_spec import ConstraintSpec, ModelSpec


def constraint_row(constraint: ConstraintSpec) -> Dict[str, str]:
    return {
        "Name": constraint.name,
        "Left-hand side": format_expression(constraint.expression),
        "Sense": constraint.sense,
        "Right-hand side": format_number(constraint.rhs),
    }


def constraint_rows(model: ModelSpec) -> List[Dict[str, str]]:
    return [constraint_row(constraint) for constraint in model.constraints]


def objective_text(model: ModelSpec) -> str:
    objective = model.objective
    return (
        f"{objective.sense.title()} {objective.name}: "
        f"{format_expression(objective.expression)}"
    )


def variable_rows(model: ModelSpec) -> List[Dict[str, str]]:
    return [
        {
            "Variable": variable.name,
            "Type": variable.variable_type.title(),
            "Lower bound": (
                "−∞"
                if variable.lower_bound is None
                else format_number(variable.lower_bound)
            ),
            "Upper bound": (
                "∞"
                if variable.upper_bound is None
                else format_number(variable.upper_bound)
            ),
        }
        for variable in model.variables
    ]
