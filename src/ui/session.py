"""Central Streamlit session state for the modern app."""

from __future__ import annotations

import streamlit as st

from src.modeling.playground_examples import EXAMPLES

DEFAULTS = {
    "model_spec": None,
    "solution": None,
    "solve_summary": "",
    "playground_error": "",
    "editor_example": next(iter(EXAMPLES)),
    "editor_text": EXAMPLES[next(iter(EXAMPLES))]["text"],
    "editor_syntax": "Auto detect",
}


def init_session_state() -> None:
    for key, value in DEFAULTS.items():
        if key not in st.session_state:
            st.session_state[key] = value


def clear_solution() -> None:
    st.session_state.model_spec = None
    st.session_state.solution = None
    st.session_state.solve_summary = ""
    st.session_state.playground_error = ""


def load_example(name: str) -> None:
    example = EXAMPLES[name]
    st.session_state.editor_text = example["text"]
    st.session_state.editor_syntax = example["syntax"].title()
    clear_solution()
