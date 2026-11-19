"""Wrapper around the existing natural-language pipeline (classify → generate → solve → interpret).

No new AI features are added here; this only runs the existing agents in a
background job and reports provider availability truthfully.
"""

from __future__ import annotations

import os
from typing import Any, Dict, Optional

_PLACEHOLDERS = ("your_", "sk-xxx", "changeme", "<", "placeholder")


def _real_key(value: Optional[str]) -> bool:
    if not value or not value.strip():
        return False
    lowered = value.strip().lower()
    return not any(lowered.startswith(p) for p in _PLACEHOLDERS)


def provider_status() -> Dict[str, Any]:
    provider = (os.getenv("AI_PROVIDER") or "").strip().lower()
    keys = {
        "anthropic": _real_key(os.getenv("ANTHROPIC_API_KEY")),
        "openai": _real_key(os.getenv("OPENAI_API_KEY")),
    }
    if provider in keys:
        configured = keys[provider]
        chosen = provider
    else:
        chosen = "anthropic" if keys["anthropic"] else ("openai" if keys["openai"] else "")
        configured = bool(chosen)
    model = os.getenv("OPENAI_MODEL" if chosen == "openai" else "ANTHROPIC_MODEL", "") if chosen else ""
    reason = "" if configured else (
        f"AI_PROVIDER is '{provider}' but no {provider.upper()}_API_KEY is set." if provider in keys
        else "No ANTHROPIC_API_KEY or OPENAI_API_KEY is set in the environment or .env file."
    )
    return {"configured": configured, "provider": chosen, "model": model, "reason": reason}


def run_natural_language(job, text: str, solver: str, time_limit: Optional[float]) -> Dict[str, Any]:
    """Executed inside a background job. Raises with a step label on failure."""
    from src.agents.problem_classifier import ProblemClassifier
    from src.modeling.model_generator import ModelGenerator
    from src.modeling.pulp_convert import pulp_to_spec
    from src.solvers.backends import solve_spec

    steps = []
    job.set_progress("Step 1 of 4 · Classifying the problem")
    try:
        problem_data = ProblemClassifier().classify(text)
    except Exception as exc:
        raise RuntimeError(f"Classification failed: {exc}") from exc
    steps.append({"step": "Classify", "detail": f"{problem_data.get('problem_type', '?')} ({problem_data.get('confidence', 0):.0%} confidence)"})
    if problem_data.get("confidence", 0) < 0.15:
        raise RuntimeError("The provider could not identify an optimization problem in this description.")

    job.set_progress("Step 2 of 4 · Building the model")
    try:
        model = ModelGenerator().generate(problem_data, solver_preference="pulp")
    except Exception as exc:
        raise RuntimeError(f"Model generation failed: {exc}") from exc
    if isinstance(model, dict):
        raise RuntimeError("The generated model is not linear (CVXPY model); it cannot be solved in the deterministic workspace.")
    spec = pulp_to_spec(model, name=problem_data.get("problem_type", "AI model").replace("_", " ").title())
    steps.append({"step": "Generate", "detail": f"{len(spec.variables)} variables, {len(spec.constraints)} constraints"})

    job.set_progress("Step 3 of 4 · Solving")
    result = solve_spec(spec, solver, time_limit, cancel=job.cancel_event, handle=job.handle)
    steps.append({"step": "Solve", "detail": result["status"]})

    job.set_progress("Step 4 of 4 · Explaining the result")
    interpretation = None
    try:
        from src.interpreters.result_interpreter import ResultInterpreter

        legacy_solution = {
            "status": result["status"], "is_optimal": result["kind"] == "optimal",
            "objective_value": result["objective"], "variables": result["variables"],
            "solve_time": result.get("solve_time"), "solver_name": result.get("backend"),
        }
        interpretation = ResultInterpreter().interpret(legacy_solution, problem_data)
        steps.append({"step": "Interpret", "detail": "Provider explanation"})
    except Exception as exc:
        steps.append({"step": "Interpret", "detail": f"Provider explanation unavailable ({exc}); offline summary shown."})
    return {"problem_data": problem_data, "spec": spec, "result": result, "interpretation": interpretation, "steps": steps}
