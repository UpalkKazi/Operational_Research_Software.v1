"""Session state helpers: the workspace, persistent preferences and bound widgets."""

from __future__ import annotations

from typing import Any, Callable, Optional

import streamlit as st

from src.services.workspace import Workspace

DEFAULTS = {
    "view": "chat",
    "solver": "auto",
    "time_limit": 60,
    "fmt": "auto",
    "draft": "",
    "pg_tab": "Easy Start",
    "alg_text": "",
    "alg_fmt": "auto",
    "tpl_selected": None,
}


def ws() -> Workspace:
    if "ws" not in st.session_state:
        st.session_state["ws"] = Workspace()
    return st.session_state["ws"]


def pref(name: str) -> Any:
    key = f"pref_{name}"
    if key not in st.session_state:
        st.session_state[key] = DEFAULTS.get(name)
    return st.session_state[key]


def set_pref(name: str, value: Any) -> None:
    st.session_state[f"pref_{name}"] = value


def bound(widget: Callable, pref_name: str, key: str, on_change: Optional[Callable] = None, **kwargs) -> Any:
    """Render ``widget`` bound to a persistent preference.

    Widget state is cleared by Streamlit when a widget is not rendered (e.g.
    on the other page); the preference survives and re-seeds the widget, and
    several widgets can share one preference.
    """
    wkey = f"w_{key}"
    value = pref(pref_name)
    if st.session_state.get(wkey, object()) != value:
        st.session_state[wkey] = value

    def sync() -> None:
        set_pref(pref_name, st.session_state[wkey])
        if on_change:
            on_change()

    return widget(key=wkey, on_change=sync, **kwargs)


def flash(message: str, level: str = "info") -> None:
    st.session_state.setdefault("_flash", []).append((level, message))


def show_flashes() -> None:
    for level, message in st.session_state.pop("_flash", []):
        icon = {"success": ":material/check_circle:", "error": ":material/error:", "warning": ":material/warning:"}.get(level, ":material/info:")
        st.toast(message, icon=icon)


def epoch(model_id: str) -> int:
    return st.session_state.setdefault("_epochs", {}).get(model_id, 0)


def bump_epoch(model_id: str) -> None:
    """Force Live Editor widgets to re-read the model after an external change."""
    epochs = st.session_state.setdefault("_epochs", {})
    epochs[model_id] = epochs.get(model_id, 0) + 1
    st.session_state.pop("le_active_eq", None)


def go(view: str, tab: Optional[str] = None) -> None:
    set_pref("view", view)
    if tab:
        set_pref("pg_tab", tab)
