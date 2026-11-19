"""Reusable model and result views."""

from __future__ import annotations

import json
import math
from typing import Any, Dict

import pandas as pd
import plotly.express as px
import streamlit as st

from src.modeling.model_formatter import (
    constraint_rows,
    objective_text,
    variable_rows,
)
from src.modeling.model_spec import ModelSpec


def render_model_inspector(model: ModelSpec, key_prefix: str = "model") -> None:
    st.markdown("### Model inspector")
    st.markdown(
        f'<span class="or-chip">{model.source_syntax.upper()}</span>',
        unsafe_allow_html=True,
    )
    st.markdown(f"**{objective_text(model)}**")

    variable_tab, constraint_tab, source_tab = st.tabs(
        [
            f"Variables · {len(model.variables)}",
            f"Constraints · {len(model.constraints)}",
            "Source",
        ]
    )
    with variable_tab:
        st.dataframe(
            pd.DataFrame(variable_rows(model)),
            width="stretch",
            hide_index=True,
        )
    with constraint_tab:
        rows = constraint_rows(model)
        query = (
            st.text_input(
                "Filter constraints",
                placeholder="Search by name or expression",
                key=f"{key_prefix}_constraint_filter",
            )
            .strip()
            .lower()
        )
        if query:
            rows = [row for row in rows if query in " ".join(row.values()).lower()]
        page_size = 12
        pages = max(1, math.ceil(len(rows) / page_size))
        page = st.number_input(
            "Page",
            min_value=1,
            max_value=pages,
            value=1,
            step=1,
            key=f"{key_prefix}_constraint_page",
        )
        start = (int(page) - 1) * page_size
        st.dataframe(
            pd.DataFrame(rows[start : start + page_size]),
            width="stretch",
            hide_index=True,
            column_config={
                "Name": st.column_config.TextColumn(width="medium"),
                "Left-hand side": st.column_config.TextColumn(width="large"),
                "Sense": st.column_config.TextColumn(width="small"),
                "Right-hand side": st.column_config.TextColumn(width="small"),
            },
        )
        st.caption(
            f"Showing {min(len(rows), start + 1)}–{min(len(rows), start + page_size)} of {len(rows)}"
        )
    with source_tab:
        st.code(model.source_text or "Created with Easy Start", language="python")


def render_results(result: Dict[str, Any], summary: str = "") -> None:
    status = result.get("status", "Unknown")
    if result.get("is_optimal"):
        st.success(summary or "Optimal solution found.")
    else:
        st.error(result.get("error_message") or f"Solver status: {status}")

    left, middle, right = st.columns(3)
    left.metric("Status", status)
    objective = result.get("objective_value")
    middle.metric("Objective", "—" if objective is None else f"{objective:,.4f}")
    right.metric("Solve time", f"{result.get('solve_time', 0):.3f}s")

    variables = result.get("variables", {})
    rows = [
        {"Variable": name, "Value": value}
        for name, value in variables.items()
        if value is not None
    ]
    if rows:
        st.markdown("### Decision variables")
        frame = pd.DataFrame(rows).sort_values("Variable")
        st.dataframe(frame, width="stretch", hide_index=True)
        nonzero = frame[frame["Value"].abs() > 1e-9]
        if not nonzero.empty and len(nonzero) <= 30:
            figure = px.bar(
                nonzero,
                x="Variable",
                y="Value",
                title="Non-zero decisions",
                color_discrete_sequence=["#0a84ff"],
            )
            figure.update_layout(
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)",
                margin=dict(l=10, r=10, t=50, b=10),
            )
            st.plotly_chart(figure, width="stretch")

    st.download_button(
        "Download result JSON",
        data=json.dumps(result, indent=2, default=str),
        file_name="or-studio-result.json",
        mime="application/json",
    )
