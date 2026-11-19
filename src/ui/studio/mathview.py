"""Render a ModelSpec as readable LaTeX with real variable and constraint names."""

from __future__ import annotations

import re
from typing import Dict, List, Optional

import streamlit as st

from src.modeling.latex_linear import latex_names, latex_number, linear_to_latex
from src.modeling.model_spec import ConstraintSpec, ModelSpec

REL = {"<=": r"\le", ">=": r"\ge", "=": "="}
REL_TEXT = {"<=": "≤", ">=": "≥", "=": "="}


def symbols(spec: ModelSpec) -> Dict[str, str]:
    key = ("_sym", spec.fingerprint(), tuple(v.name for v in spec.variables))
    cache = st.session_state.setdefault("_symcache", {})
    if key not in cache:
        if len(cache) > 64:
            cache.clear()
        cache[key] = latex_names([v.name for v in spec.variables])
    return cache[key]


def text_name(name: str) -> str:
    return r"\text{" + re.sub(r"([#$%&_{}~^\\])", r"\\\1", name) + "}"


def objective_latex(spec: ModelSpec, max_terms: Optional[int] = None) -> str:
    return linear_to_latex(spec.objective.expression, symbols(spec), max_terms)


def lhs_latex(spec: ModelSpec, constraint: ConstraintSpec, max_terms: Optional[int] = None) -> str:
    return linear_to_latex(constraint.expression, symbols(spec), max_terms)


def constraint_latex(spec: ModelSpec, constraint: ConstraintSpec, max_terms: Optional[int] = None) -> str:
    return f"{lhs_latex(spec, constraint, max_terms)} {REL[constraint.sense]} {latex_number(constraint.rhs)}"


def bounds_text(lower: Optional[float], upper: Optional[float]) -> str:
    lo = "−∞" if lower is None else f"{lower:g}"
    hi = "+∞" if upper is None else f"{upper:g}"
    return f"{lo} … {hi}"


def domain_latex(spec: ModelSpec, limit: int = 40) -> List[str]:
    sym = symbols(spec)
    groups: Dict[tuple, List[str]] = {}
    for v in spec.variables:
        groups.setdefault((v.variable_type, v.lower_bound, v.upper_bound), []).append(sym[v.name])
    lines = []
    for (kind, lo, hi), names in groups.items():
        shown = names[:limit]
        head = ", ".join(shown) + (r", \ldots" if len(names) > limit else "")
        if kind == "binary":
            lines.append(head + r" \in \{0, 1\}")
            continue
        tag = r",\ \text{integer}" if kind == "integer" else ""
        if lo is not None and hi is not None:
            lines.append(f"{latex_number(lo)} \\le {head} \\le {latex_number(hi)}{tag}")
        elif lo is not None:
            lines.append(f"{head} \\ge {latex_number(lo)}{tag}")
        elif hi is not None:
            lines.append(f"{head} \\le {latex_number(hi)}{tag}" + r"\ \text{(no lower bound)}")
        else:
            lines.append(f"{head}\\ \\text{{free}}{tag}")
    return lines


def model_latex(spec: ModelSpec, max_rows: int = 40, max_terms: int = 14) -> str:
    sense = r"\max" if spec.objective.sense == "maximize" else r"\min"
    rows = [f"{sense} \\quad & {objective_latex(spec, max_terms)}"]
    shown = spec.constraints[:max_rows]
    for index, c in enumerate(shown):
        prefix = r"\text{s.t.}" if index == 0 else ""
        rows.append(f"{prefix} \\quad & {constraint_latex(spec, c, max_terms)} && {text_name(c.name)}")
    if len(spec.constraints) > max_rows:
        rows.append(rf"& \vdots && \text{{{len(spec.constraints) - max_rows:,} more constraints}}")
    for line in domain_latex(spec):
        rows.append(f"& {line}")
    return r"\begin{aligned}" + r"\\ ".join(rows) + r"\end{aligned}"


def show_model(spec: ModelSpec, max_rows: int = 40) -> None:
    st.latex(model_latex(spec, max_rows=max_rows))
