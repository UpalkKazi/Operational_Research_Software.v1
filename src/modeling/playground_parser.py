"""Syntax detection and unified entry point for Model Playground input."""

from __future__ import annotations

from typing import Literal

from .ampl_parser import parse_ampl
from .model_spec import ModelSpec
from .orlearn_parser import parse_orlearn

Syntax = Literal["auto", "orlearn", "ampl"]


def detect_syntax(text: str) -> Literal["orlearn", "ampl"]:
    lowered = text.lower()
    if "or()" in lowered or "from orlearn" in lowered or ".subject_to(" in lowered:
        return "orlearn"
    if any(
        token in lowered
        for token in ("var ", "maximize ", "minimize ", "subject to", "s.t.")
    ):
        return "ampl"
    raise ValueError(
        "Could not detect the syntax. Start with OR().maximize(...) or an AMPL-style "
        "'var x;' declaration, or choose a syntax manually."
    )


def parse_model(text: str, syntax: Syntax = "auto") -> ModelSpec:
    selected = detect_syntax(text) if syntax == "auto" else syntax
    if selected == "orlearn":
        return parse_orlearn(text)
    if selected == "ampl":
        return parse_ampl(text)
    raise ValueError(f"Unknown syntax '{syntax}'.")
