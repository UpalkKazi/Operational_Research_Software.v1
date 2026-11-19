"""OR Studio — Streamlit entry point.

Chat and Model Playground share one workspace (models, revisions, runs).
The previous single-page interface is kept as ``legacy_app.py``.
"""

from __future__ import annotations

import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / ".env")

import streamlit as st  # noqa: E402

st.set_page_config(page_title="OR Studio", page_icon=":material/function:", layout="wide", initial_sidebar_state="collapsed")

from src.ui.studio import chat, header, load_problem, playground, state, styles  # noqa: E402


def main() -> None:
    workspace = state.ws()
    workspace.poll()
    chat.poll_messages()
    header.sync_query_view()
    view = state.pref("view")
    styles.inject(view)
    header.render()
    state.show_flashes()
    if view == "playground":
        playground.render()
    else:
        chat.render()
    where = st.session_state.get("dlg_load")
    if where:
        load_problem.dialog(where)
    state.show_flashes()


main()
