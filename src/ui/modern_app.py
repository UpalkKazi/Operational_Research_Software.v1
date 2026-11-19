"""Modern Streamlit application shell for OR Studio."""

from __future__ import annotations

from typing import List

import pandas as pd
import streamlit as st

from src.modeling.linear_expression import parse_linear_expression
from src.modeling.model_spec import (
    ConstraintSpec,
    LinearExpression,
    ModelSpec,
    ObjectiveSpec,
    VariableSpec,
)
from src.modeling.playground_examples import EXAMPLES
from src.services.model_playground import (
    deterministic_summary,
    parse_playground_model,
    solve_model_spec,
)
from src.ui.model_components import render_model_inspector, render_results
from src.ui.session import clear_solution, init_session_state, load_example
from src.ui.theme import apply_theme


def render_app() -> None:
    st.set_page_config(
        page_title="OR Studio · Model Playground",
        page_icon="◉",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    apply_theme()
    init_session_state()
    _render_sidebar()

    st.markdown(
        """
        <section class="or-hero">
          <div class="or-eyebrow">OR Studio</div>
          <h1>Model Playground</h1>
          <p>Write, inspect, and solve optimization models without an AI API.
          Start with a guided model or use safe OR-Learn and AMPL-style syntax.</p>
        </section>
        """,
        unsafe_allow_html=True,
    )

    easy_tab, algebraic_tab, results_tab, learn_tab = st.tabs(
        ["Easy Start", "Algebraic", "Results", "Syntax guide"]
    )
    with easy_tab:
        _render_easy_start()
    with algebraic_tab:
        _render_algebraic()
    with results_tab:
        _render_results_tab()
    with learn_tab:
        _render_syntax_guide()


def _render_sidebar() -> None:
    with st.sidebar:
        st.markdown("## OR Studio")
        st.caption("Deterministic optimization workspace")
        st.markdown("---")
        st.selectbox(
            "Solver",
            ["pulp_cbc"],
            format_func=lambda value: "CBC · Open source",
            key="selected_solver",
        )
        st.slider("Time limit", 5, 300, 60, 5, key="solve_time_limit")
        st.markdown("---")
        st.markdown("**Runtime status**")
        st.success("AI-free mode")
        st.caption("Inputs are parsed locally and are never executed as Python.")
        if st.button("Clear workspace", width="stretch"):
            clear_solution()
            st.rerun()


def _render_easy_start() -> None:
    st.markdown("## Build your first model")
    st.caption("Edit the tables, preview the mathematical model, then solve.")

    objective_col, name_col = st.columns([1, 2])
    with objective_col:
        sense = st.segmented_control(
            "Objective",
            ["Maximize", "Minimize"],
            default="Maximize",
            key="easy_sense",
        )
    with name_col:
        model_name = st.text_input(
            "Model name", "Production plan", key="easy_model_name"
        )

    st.markdown("### Variables")
    variable_data = pd.DataFrame(
        [
            {
                "Name": "chairs",
                "Type": "Integer",
                "Lower": 0.0,
                "Upper": None,
                "Objective": 45.0,
            },
            {
                "Name": "tables",
                "Type": "Integer",
                "Lower": 0.0,
                "Upper": None,
                "Objective": 80.0,
            },
        ]
    )
    variables = st.data_editor(
        variable_data,
        num_rows="dynamic",
        width="stretch",
        hide_index=True,
        key="easy_variables",
        column_config={
            "Name": st.column_config.TextColumn(required=True),
            "Type": st.column_config.SelectboxColumn(
                options=["Continuous", "Integer", "Binary"], required=True
            ),
            "Lower": st.column_config.NumberColumn(),
            "Upper": st.column_config.NumberColumn(),
            "Objective": st.column_config.NumberColumn(required=True),
        },
    )

    st.markdown("### Constraints")
    st.caption("Use variable names from the table above. Expressions must be linear.")
    constraint_data = pd.DataFrame(
        [
            {
                "Name": "wood",
                "Left-hand side": "5*chairs + 20*tables",
                "Sense": "<=",
                "RHS": 400.0,
            },
            {
                "Name": "labor",
                "Left-hand side": "10*chairs + 15*tables",
                "Sense": "<=",
                "RHS": 450.0,
            },
        ]
    )
    constraints = st.data_editor(
        constraint_data,
        num_rows="dynamic",
        width="stretch",
        hide_index=True,
        key="easy_constraints",
        column_config={
            "Name": st.column_config.TextColumn(required=True),
            "Left-hand side": st.column_config.TextColumn(required=True, width="large"),
            "Sense": st.column_config.SelectboxColumn(
                options=["<=", ">=", "="], required=True
            ),
            "RHS": st.column_config.NumberColumn(required=True),
        },
    )

    try:
        model = _model_from_easy_start(
            model_name, sense or "Maximize", variables, constraints
        )
        st.session_state.easy_model_preview = model
        st.success("Model is valid and ready to solve.")
        render_model_inspector(model, "easy")
    except Exception as exc:
        model = None
        st.error(str(exc))

    if st.button(
        "Solve guided model",
        type="primary",
        disabled=model is None,
        width="stretch",
        key="solve_easy",
    ):
        _solve(model)
        st.rerun()


def _model_from_easy_start(
    model_name: str,
    sense: str,
    variable_frame: pd.DataFrame,
    constraint_frame: pd.DataFrame,
) -> ModelSpec:
    variable_specs: List[VariableSpec] = []
    objective_coefficients = {}
    for row in variable_frame.to_dict("records"):
        name = str(row.get("Name", "")).strip()
        if not name:
            continue
        variable_type = str(row.get("Type", "Continuous")).lower()
        lower = _optional_number(row.get("Lower"))
        upper = _optional_number(row.get("Upper"))
        if variable_type == "binary":
            lower, upper = 0.0, 1.0
        variable_specs.append(VariableSpec(name, variable_type, lower, upper))
        objective_coefficients[name] = float(row.get("Objective") or 0)

    constraint_specs = []
    for number, row in enumerate(constraint_frame.to_dict("records"), start=1):
        expression_text = str(row.get("Left-hand side", "")).strip()
        if not expression_text:
            continue
        constraint_specs.append(
            ConstraintSpec(
                name=str(row.get("Name") or f"constraint_{number}").strip(),
                expression=parse_linear_expression(expression_text),
                sense=str(row.get("Sense") or "<="),
                rhs=float(row.get("RHS") or 0),
                source=expression_text,
            )
        )

    return ModelSpec(
        name=(model_name or "Guided_Model").replace(" ", "_"),
        variables=variable_specs,
        objective=ObjectiveSpec(
            (sense or "Maximize").lower(),
            LinearExpression(objective_coefficients),
            "objective",
        ),
        constraints=constraint_specs,
        source_syntax="easy-start",
        metadata={"created_with": "Easy Start"},
    ).validate()


def _render_algebraic() -> None:
    st.markdown("## Algebraic editor")
    st.caption("One input area, two compact syntaxes, immediate validation.")

    example_col, syntax_col = st.columns([2, 1])
    with example_col:
        selected = st.selectbox(
            "Example",
            list(EXAMPLES),
            key="editor_example",
            on_change=_example_changed,
        )
        example = EXAMPLES[selected]
        st.caption(f"{example['description']} · {example['source']}")
    with syntax_col:
        st.selectbox(
            "Syntax",
            ["Auto detect", "ORLearn", "AMPL"],
            key="editor_syntax",
        )

    st.text_area(
        "Model source",
        key="editor_text",
        height=330,
        help="The safe parser accepts only linear model constructs; pasted Python is never executed.",
    )

    syntax_value = {
        "Auto detect": "auto",
        "ORLearn": "orlearn",
        "AMPL": "ampl",
    }[st.session_state.editor_syntax]
    try:
        model = parse_playground_model(st.session_state.editor_text, syntax_value)
        st.session_state.playground_error = ""
        st.success(f"Valid {model.source_syntax.upper()} model")
        render_model_inspector(model, "algebraic")
    except Exception as exc:
        model = None
        st.session_state.playground_error = str(exc)
        st.error(str(exc))

    action_col, reset_col = st.columns([3, 1])
    with action_col:
        if st.button(
            "Solve algebraic model",
            type="primary",
            disabled=model is None,
            width="stretch",
            key="solve_algebraic",
        ):
            _solve(model)
            st.rerun()
    with reset_col:
        if st.button("Reload example", width="stretch"):
            load_example(st.session_state.editor_example)
            st.rerun()


def _example_changed() -> None:
    load_example(st.session_state.editor_example)


def _solve(model: ModelSpec) -> None:
    with st.spinner("Solving model…"):
        result = solve_model_spec(
            model,
            solver=st.session_state.selected_solver,
            max_time=st.session_state.solve_time_limit,
        )
    st.session_state.model_spec = model
    st.session_state.solution = result
    st.session_state.solve_summary = deterministic_summary(result)


def _render_results_tab() -> None:
    if not st.session_state.solution:
        st.info("Solve a model in Easy Start or Algebraic to see results here.")
        return
    st.markdown("## Solution")
    render_results(st.session_state.solution, st.session_state.solve_summary)
    if st.session_state.model_spec:
        with st.expander("Solved model"):
            render_model_inspector(st.session_state.model_spec, "results")


def _render_syntax_guide() -> None:
    st.markdown("## Compact syntax guide")
    st.caption(
        "The first release intentionally supports a small, predictable linear subset."
    )
    left, right = st.columns(2)
    with left:
        st.markdown("### OR-Learn style")
        st.code(
            """model = (OR()
  .maximize([3, 2], names=["x", "y"])
  .subject_to([1, 1], "<=", 4, "capacity")
  .as_integer()
  .solve())""",
            language="python",
        )
        st.markdown(
            "Supported: `maximize`, `minimize`, `subject_to`, `as_binary`, "
            "`as_integer`, and `solve`."
        )
    with right:
        st.markdown("### AMPL style")
        st.code(
            """var x >= 0, integer;
var y >= 0;
maximize profit: 3*x + 2*y;
subject to capacity: x + y <= 4;
solve;""",
            language="text",
        )
        st.markdown(
            "Supported: scalar variables, bounds, continuous/integer/binary domains, "
            "one linear objective, and named linear constraints."
        )
    st.warning(
        "Indexed sets, summations, matrix notation, and nonlinear terms are not silently "
        "approximated. The editor reports them as unsupported so results remain trustworthy."
    )


def _optional_number(value):
    if value is None or pd.isna(value):
        return None
    return float(value)
