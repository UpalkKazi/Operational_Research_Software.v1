"""Export a solved run: JSON, CSV and an AMPL-style / LP-format model file."""

from __future__ import annotations

import csv
import io
import json
import re
from typing import Any, Dict, Optional

from src.modeling.model_spec import LinearExpression, ModelSpec


def _safe(name: str, used: Dict[str, str]) -> str:
    base = re.sub(r"\W", "_", name).strip("_") or "x"
    if base[0].isdigit():
        base = "_" + base
    candidate, n = base, 1
    while candidate in used.values() and used.get(name) != candidate:
        n += 1
        candidate = f"{base}_{n}"
    used[name] = candidate
    return candidate


def _num(value: float) -> str:
    return format(float(value), ".15g")


def _expr(expr: LinearExpression, names: Dict[str, str], times: str = "*") -> str:
    parts = []
    for name, coef in expr.coefficients.items():
        if coef == 0:
            continue
        sign = "-" if coef < 0 else "+"
        magnitude = abs(coef)
        term = names[name] if magnitude == 1 else f"{_num(magnitude)}{times}{names[name]}"
        parts.append(f"{sign} {term}")
    if expr.constant:
        parts.append(f"{'-' if expr.constant < 0 else '+'} {_num(abs(expr.constant))}")
    text = " ".join(parts) or "0"
    return text[2:] if text.startswith("+ ") else text


def spec_to_ampl(spec: ModelSpec) -> str:
    names: Dict[str, str] = {}
    for v in spec.variables:
        _safe(v.name, names)
    lines = [f"# {spec.name} — exported from OR Studio (AMPL-style subset)"]
    renamed = [f"#   {n} -> {s}" for n, s in names.items() if n != s]
    if renamed:
        lines.append("# Renamed variables:")
        lines.extend(renamed[:200])
    for v in spec.variables:
        attrs = []
        if v.lower_bound is not None:
            attrs.append(f">= {_num(v.lower_bound)}")
        if v.upper_bound is not None:
            attrs.append(f"<= {_num(v.upper_bound)}")
        if v.variable_type == "integer":
            attrs.append("integer")
        elif v.variable_type == "binary":
            attrs = ["binary"]
        lines.append(f"var {names[v.name]}{(' ' + ', '.join(attrs)) if attrs else ''};")
    cnames: Dict[str, str] = {}
    lines.append(f"{spec.objective.sense} {_safe(spec.objective.name, {})}: {_expr(spec.objective.expression, names)};")
    for c in spec.constraints:
        lines.append(f"subject to {_safe(c.name, cnames)}: {_expr(c.expression, names)} {c.sense} {_num(c.rhs)};")
    return "\n".join(lines) + "\n"


def spec_to_lp(spec: ModelSpec) -> str:
    names: Dict[str, str] = {}
    for v in spec.variables:
        _safe(v.name, names)
    cnames: Dict[str, str] = {}
    out = [f"\\ {spec.name} — exported from OR Studio", "Maximize" if spec.objective.sense == "maximize" else "Minimize"]
    out.append(f" obj: {_expr(spec.objective.expression, names, ' ')}")
    out.append("Subject To")
    for c in spec.constraints:
        rhs = c.rhs - c.expression.constant
        body = _expr(LinearExpression(c.expression.coefficients, 0.0), names, " ")
        out.append(f" {_safe(c.name, cnames)}: {body} {c.sense} {_num(rhs)}")
    out.append("Bounds")
    for v in spec.variables:
        n = names[v.name]
        if v.variable_type == "binary":
            continue
        lo = "-inf" if v.lower_bound is None else _num(v.lower_bound)
        hi = "+inf" if v.upper_bound is None else _num(v.upper_bound)
        out.append(f" {lo} <= {n} <= {hi}")
    generals = [names[v.name] for v in spec.variables if v.variable_type == "integer"]
    binaries = [names[v.name] for v in spec.variables if v.variable_type == "binary"]
    if generals:
        out.append("General")
        out.extend(f" {n}" for n in generals)
    if binaries:
        out.append("Binary")
        out.extend(f" {n}" for n in binaries)
    out.append("End")
    return "\n".join(out) + "\n"


def result_json(result: Dict[str, Any], spec: Optional[ModelSpec], run_meta: Dict[str, Any]) -> str:
    payload = {
        "run": run_meta,
        "model": {"name": spec.name, "fingerprint": spec.fingerprint(), "stats": spec.stats()} if spec else None,
        "result": {k: v for k, v in result.items() if k not in ("library_check",)},
        "library_check": result.get("library_check"),
    }
    return json.dumps(payload, indent=2, default=str)


def variables_csv(result: Dict[str, Any], spec: Optional[ModelSpec]) -> str:
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["variable", "value", "domain", "lower_bound", "upper_bound", "reduced_cost"])
    vmap = spec.variable_map() if spec else {}
    reduced = result.get("reduced_costs") or {}
    for name, value in (result.get("variables") or {}).items():
        v = vmap.get(name)
        writer.writerow([name, value, v.variable_type if v else "", "" if not v or v.lower_bound is None else v.lower_bound,
                         "" if not v or v.upper_bound is None else v.upper_bound, reduced.get(name, "")])
    return buffer.getvalue()


def constraints_csv(result: Dict[str, Any]) -> str:
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["constraint", "activity", "relation", "rhs", "slack", "dual", "binding"])
    for name, row in (result.get("constraints") or {}).items():
        writer.writerow([name, row.get("activity"), row.get("sense"), row.get("rhs"), row.get("slack"), row.get("dual"), row.get("binding")])
    return buffer.getvalue()
