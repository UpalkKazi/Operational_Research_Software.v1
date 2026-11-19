"""Deterministic orchestration for parsing, building, and solving models."""

from __future__ import annotations

from typing import Any, Dict

from src.modeling.model_spec import ModelSpec
from src.modeling.playground_parser import Syntax, parse_model
from src.modeling.pulp_builder import build_pulp_model
from src.solvers.solver_interface import SolverInterface


def parse_playground_model(text: str, syntax: Syntax = "auto") -> ModelSpec:
    return parse_model(text, syntax)


def solve_model_spec(
    spec: ModelSpec,
    solver: str = "pulp_cbc",
    max_time: int = 60,
) -> Dict[str, Any]:
    model = build_pulp_model(spec)
    result = SolverInterface(solver, problem_data={"source": "playground"}).solve(
        model,
        max_time=max_time,
        verbose=False,
    )
    result["source_syntax"] = spec.source_syntax
    result["model_name"] = spec.name
    return result


def deterministic_summary(result: Dict[str, Any]) -> str:
    status = result.get("status", "Unknown")
    if not result.get("is_optimal"):
        error = result.get("error_message")
        return f"Solver status: {status}." + (f" {error}" if error else "")
    objective = result.get("objective_value")
    count = result.get("num_variables", len(result.get("variables", {})))
    return (
        f"An optimal solution was found with objective value {objective:,.4f} "
        f"across {count} decision variable{'s' if count != 1 else ''}."
    )
