"""Classify composer input as OR-Learn, AMPL-style, natural language, or ambiguous."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List

FORMAT_LABELS = {
    "auto": "Auto",
    "natural": "Natural Language",
    "orlearn": "OR-Learn",
    "ampl": "AMPL-style",
}


@dataclass
class Detection:
    format: str  # "orlearn" | "ampl" | "natural" | "ambiguous" | "empty"
    reasons: List[str] = field(default_factory=list)
    candidates: List[str] = field(default_factory=list)


_ORL_STRONG = [
    (re.compile(r"^\s*(from\s+orlearn\b|import\s+orlearn\b)", re.M), "imports orlearn"),
    (re.compile(r"\bOR\s*\(\s*\)"), "uses OR()"),
    (re.compile(r"\.subject_to\s*\("), "calls .subject_to()"),
]
_ORL_WEAK = [
    (re.compile(r"\.(maximize|minimize)\s*\(\s*\["), "calls .maximize([...])"),
    (re.compile(r"\bassign\s*\(\s*[\[\w]"), "calls assign(...)"),
]
_AMPL_STRONG = [
    (re.compile(r"^\s*var\s+[A-Za-z_]\w*[^;\n]*;", re.M), "declares 'var ...;'"),
    (re.compile(r"^\s*(param|set)\s+[A-Za-z_]\w*", re.M), "declares param/set"),
    (re.compile(r"^\s*(maximize|minimize)\s+[A-Za-z_]\w*\s*:", re.M | re.I), "names an objective 'maximize name:'"),
    (re.compile(r"^\s*(subject\s+to|s\.t\.)\s+[A-Za-z_]\w*\s*(\{[^}]*\})?\s*:", re.M | re.I), "names a constraint 'subject to name:'"),
]
_MATH_HINT = re.compile(r"(<=|>=|≤|≥|=)")
_PROSE_WORD = re.compile(r"\b[a-zA-Z]{3,}\b")


def detect_format(text: str) -> Detection:
    stripped = (text or "").strip()
    if not stripped:
        return Detection("empty")
    orl_strong = [label for rx, label in _ORL_STRONG if rx.search(stripped)]
    orl_weak = [label for rx, label in _ORL_WEAK if rx.search(stripped)]
    ampl = [label for rx, label in _AMPL_STRONG if rx.search(stripped)]
    semicolons = stripped.count(";")

    if orl_strong and not ampl:
        return Detection("orlearn", orl_strong + orl_weak)
    if ampl and not orl_strong and (semicolons or len(ampl) >= 2):
        return Detection("ampl", ampl)
    if orl_strong and ampl:
        return Detection("ambiguous", orl_strong + ampl, ["orlearn", "ampl"])

    words = _PROSE_WORD.findall(stripped)
    has_math = bool(_MATH_HINT.search(stripped))
    lowered = stripped.lower()
    structured_words = any(k in lowered for k in ("maximize", "minimize", "subject to", "s.t."))
    if orl_weak:
        return Detection("ambiguous", orl_weak, ["orlearn", "natural"])
    if ampl:
        return Detection("ambiguous", ampl + ["but no ';' statement endings"], ["ampl", "natural"])
    if structured_words and has_math and len(words) < 25:
        return Detection(
            "ambiguous",
            ["looks like algebra without AMPL declarations"],
            ["ampl", "natural"],
        )
    return Detection("natural", ["reads as a description"])
