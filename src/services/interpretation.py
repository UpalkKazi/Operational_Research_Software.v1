"""Deterministic (no-AI) interpretation of a solver result."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from src.modeling.model_spec import ModelSpec


def fmt(value: Optional[float], digits: int = 6) -> str:
    if value is None:
        return "—"
    value = float(value)
    if abs(value) < 1e-9:
        return "0"
    rounded = round(value)
    if abs(value - rounded) < 1e-7 * max(1.0, abs(value)):
        return f"{int(rounded):,}"
    return f"{value:,.{digits}g}"


def key_decisions(result: Dict[str, Any], limit: int = 6) -> List[tuple]:
    values = result.get("variables") or {}
    nonzero = [(n, v) for n, v in values.items() if v is not None and abs(v) > 1e-7]
    nonzero.sort(key=lambda item: -abs(item[1]))
    return nonzero[:limit]


def offline_summary(result: Dict[str, Any], spec: Optional[ModelSpec]) -> Dict[str, Any]:
    kind = result.get("kind")
    status = result.get("status", "")
    sense = spec.objective.sense if spec else "optimize"
    objective_name = spec.objective.name if spec else "objective"
    paragraphs: List[str] = []
    bullets: List[str] = []

    if kind == "optimal":
        paragraphs.append(f"The solver proved this plan optimal: the best possible {objective_name} is **{fmt(result.get('objective'))}** ({sense}).")
    elif kind == "feasible":
        paragraphs.append(
            f"The solver found a **feasible** plan with {objective_name} **{fmt(result.get('objective'))}**, "
            "but stopped before proving it optimal (time limit). A better plan may exist; increase the time limit to keep searching."
        )
    elif kind == "infeasible":
        paragraphs.append("No plan satisfies every constraint at once. Look for constraints that conflict, such as a minimum requirement above an available capacity.")
    elif kind == "unbounded":
        paragraphs.append(f"The {objective_name} can improve without limit. A capacity or bound is probably missing.")
    elif kind == "no_solution":
        paragraphs.append("The time limit ran out before any feasible plan was found.")
    elif kind == "cancelled":
        paragraphs.append("The run was cancelled." + (" The best plan found before cancelling is shown." if result.get("variables") else ""))
    elif kind == "unsupported":
        paragraphs.append(result.get("explanation") or "The selected solver could not run this model.")
    else:
        paragraphs.append(f"The run ended with status: {status}.")

    decisions = key_decisions(result)
    total_nonzero = sum(1 for v in (result.get("variables") or {}).values() if v and abs(v) > 1e-7)
    if decisions:
        shown = ", ".join(f"{n} = {fmt(v)}" for n, v in decisions)
        more = f" (and {total_nonzero - len(decisions)} more non-zero)" if total_nonzero > len(decisions) else ""
        bullets.append(f"Key decisions: {shown}{more}.")
        zero = len(result.get("variables") or {}) - total_nonzero
        if zero:
            bullets.append(f"{zero} variable(s) are zero in this plan.")

    rows = result.get("constraints") or {}
    binding = [n for n, r in rows.items() if r.get("binding")]
    if binding:
        bullets.append("Binding (fully used) constraints: " + ", ".join(binding[:8]) + (" …" if len(binding) > 8 else "") + ".")
    slack = [(n, r["slack"]) for n, r in rows.items() if r.get("slack") is not None and not r.get("binding") and r["slack"] > 1e-7]
    if slack:
        bullets.append("Spare capacity: " + ", ".join(f"{n} ({fmt(s)})" for n, s in slack[:5]) + ".")
    duals = [(n, r["dual"]) for n, r in rows.items() if r.get("dual") not in (None, 0) and abs(r["dual"]) > 1e-9]
    if duals:
        bullets.append(
            "Shadow prices (objective change per extra unit of right-hand side): "
            + ", ".join(f"{n} {fmt(d)}" for n, d in duals[:6]) + "."
        )
    check = result.get("library_check")
    if check and check.get("available") and check.get("value") is not None and result.get("objective") is not None:
        same = abs(check["value"] - result["objective"]) <= 1e-6 * max(1.0, abs(check["value"]))
        bullets.append(
            f"OR-Learn's own {check.get('call', 'solve()')} returned {fmt(check['value'])}"
            + (" — matches." if same else " — differs from this run; see Diagnostics.")
        )
    return {"summary": " ".join(paragraphs), "bullets": bullets, "source": "offline"}
