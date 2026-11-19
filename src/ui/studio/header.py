"""Compact top bar: brand, primary navigation, active model, Settings and Help."""

from __future__ import annotations

import html

import pandas as pd
import streamlit as st

from src.services.ai_service import provider_status
from src.solvers.backends import SOLVER_ORDER, SOLVERS, availability
from src.ui.studio import state

VIEWS = {"chat": "Chat", "playground": "Model Playground"}


def sync_query_view() -> None:
    requested = st.query_params.get("view")
    if requested in VIEWS and not st.session_state.get("_qp_synced"):
        state.set_pref("view", requested)
    st.session_state["_qp_synced"] = True
    if st.query_params.get("view") != state.pref("view"):
        st.query_params["view"] = state.pref("view")


def solver_options() -> list:
    return SOLVER_ORDER


def solver_format(key: str) -> str:
    info = availability().get(key, {})
    label = SOLVERS[key]["label"] if key != "auto" else "Auto"
    return label if info.get("available", True) else f"{label} (not installed)"


def render() -> None:
    w = state.ws()
    record = w.active()
    with st.container(key="ors_topbar", horizontal=True, vertical_alignment="center", gap="small"):
        st.html('<div class="ors-brand"><span class="mark" aria-hidden="true">OR</span><span class="word">OR Studio</span></div>')
        state.bound(
            st.segmented_control, "view", "nav",
            label="Navigation", options=list(VIEWS), format_func=lambda k: VIEWS[k],
            selection_mode="single", label_visibility="collapsed", required=True,
        )
        if record is not None:
            stats = record.working.stats()
            st.html(
                f'<div class="ors-model" title="Active model"><span class="material-symbols-rounded" aria-hidden="true">deployed_code</span>'
                f'<span class="sr-only">Active model:</span><b>{html.escape(record.name)}</b>'
                f'<span>· {stats["variables"]:,}×{stats["constraints"]:,}</span></div>'
            )
        else:
            st.html('<div class="ors-model"><span>No model loaded</span></div>')
        st.space("stretch")
        with st.popover("Settings", icon=":material/tune:", help="Solver and time limit"):
            settings_panel("hdr")
        with st.popover("Help", icon=":material/help:"):
            help_panel()


def settings_panel(where: str) -> None:
    st.markdown("**Default solver**")
    state.bound(st.selectbox, "solver", f"solver_{where}", label="Solver", options=solver_options(),
                format_func=lambda k: SOLVERS[k]["full"], label_visibility="collapsed")
    state.bound(st.number_input, "time_limit", f"tl_{where}", label="Time limit (seconds)", min_value=1, max_value=3600, step=5,
                help="Integer models that hit this limit report the best plan found as Feasible, not Optimal.")
    st.markdown("**Installed solvers**")
    rows = []
    for key in SOLVER_ORDER:
        if key == "auto":
            continue
        info = availability()[key]
        rows.append({
            "Solver": SOLVERS[key]["full"],
            "Status": "Available" if info["available"] else "Not installed",
            "Problems": "LP + MIP" if SOLVERS[key]["mip"] else "LP only",
            "Cancel": "Yes" if SOLVERS[key]["cancel"] else "Time limit only",
            "Version": info.get("version") or info.get("reason", ""),
        })
    st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")
    status = provider_status()
    if status["configured"]:
        st.caption(f"Natural-language chat: {status['provider']} {status['model']} configured.")
    else:
        st.caption(f"Natural-language chat needs an AI provider key. {status['reason']} Structured formats work offline.")


def help_panel() -> None:
    from src.modeling.orlearn_adapter import library_info

    lib = library_info()
    st.markdown(
        """
**Formats**
- **OR-Learn** — chained Python calls like `OR().maximize([45, 80]).subject_to(...)`. Parsed safely; pasted Python is never executed.
- **AMPL-style** — `var`, `param`, `set`, `maximize name:`, `subject to name:` with `sum{i in I}`. See *docs/AMPL_SUBSET.md*.
- **Natural Language** — needs an AI provider key.

**Shortcuts**
- <span class="ors-kbd"><kbd>Ctrl</kbd> + <kbd>Enter</kbd></span> solves from the composer.
- <span class="ors-kbd"><kbd>Esc</kbd></span> closes the Symbols keypad and dialogs.
""",
        unsafe_allow_html=True,
    )
    st.caption(f"OR-Learn {lib.get('version', '?')} @ {lib.get('commit', '?')[:8]}" + (" (pinned)" if lib.get("pinned") else ""))
