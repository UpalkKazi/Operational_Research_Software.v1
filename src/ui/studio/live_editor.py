"""Live Editor: edit the working model row by row, solve, compare and sweep.

Edits apply immediately to the working draft (no per-section Apply).  Only
one MathLive field is mounted at a time; its value is flushed before any
solve, and invalid input keeps the last valid model while pointing at the
field that needs fixing.
"""

from __future__ import annotations

import html
import math
import re
from typing import Any, Dict, List, Optional

import pandas as pd
import streamlit as st

from src.modeling.latex_linear import LatexError, latex_to_constraint, latex_to_linear
from src.services.interpretation import fmt as fmt_num
from src.services.workspace import EditError
from src.solvers.backends import SOLVERS
from src.ui.mathlive_component import mathlive_editor
from src.ui.studio import state
from src.ui.studio.mathview import REL_TEXT, lhs_latex, objective_latex, show_model, symbols
from src.ui.studio.results import paged_table, render_run, status_kind
from src.ui.studio.styles import chip

CON_PAGE = 25
VAR_PAGE = 200
RELATIONS = ["<=", ">=", "="]


def _k(mid: str, name: str) -> str:
    return f"le_{mid}_{state.epoch(mid)}_{name}"


def _ml_key(mid: str, target: str) -> str:
    return f"ml_{mid}_{state.epoch(mid)}_{target}"


def _errors() -> Dict[str, str]:
    return st.session_state.setdefault("le_eq_errors", {})


def _applied() -> Dict[str, str]:
    return st.session_state.setdefault("le_applied", {})


# ---------------------------------------------------------------------------
#  Equation editing
# ---------------------------------------------------------------------------

def _apply_latex(mid: str, target: str, latex: str) -> Optional[str]:
    w = state.ws()
    record = w.model(mid)
    spec = record.working
    names = [v.name for v in spec.variables]
    sym = symbols(spec)
    errors = _errors()
    try:
        if target == "obj":
            w.set_objective(mid, expression=latex_to_linear(latex, names, sym))
        else:
            lhs, relation, rhs = latex_to_constraint(latex, names, sym)
            w.set_constraint_expression(mid, target, lhs, relation, rhs)
            if relation is not None:
                st.session_state["_le_rerun"] = True
    except (LatexError, EditError) as exc:
        message = str(exc)
        if isinstance(exc, LatexError) and exc.unsupported:
            message += " The Live Editor solves linear models only."
        errors[target] = message
        return message
    errors.pop(target, None)
    return None


def flush_active(mid: str) -> Optional[str]:
    target = st.session_state.get("le_active_eq")
    if not target or target == "new":
        return None
    key = _ml_key(mid, target)
    latex = st.session_state.get(key)
    if latex is None:
        return _errors().get(target)
    if _applied().get(key) == latex:
        return _errors().get(target)
    _applied()[key] = latex
    return _apply_latex(mid, target, latex)


def _open_eq(mid: str, target: Optional[str]) -> None:
    flush_active(mid)
    current = st.session_state.get("le_active_eq")
    if current and current != target and current in _errors():
        st.session_state["le_active_eq"] = current
        state.flash("Fix the expression that's open before editing another one.", "warning")
        return
    st.session_state["le_initial"] = {}
    st.session_state["le_active_eq"] = target
    st.session_state["le_focus"] = ("eq", target, _focus_token())


def _focus_token() -> str:
    count = st.session_state.get("_focus_count", 0) + 1
    st.session_state["_focus_count"] = count
    return str(count)


def _palette(spec) -> List[Dict[str, str]]:
    sym = symbols(spec)
    return [{"name": v.name, "latex": sym[v.name]} for v in spec.variables[:24]]


def _equation_editor(mid: str, target: str, initial: str, mode: str, label: str) -> None:
    record = state.ws().model(mid)
    key = _ml_key(mid, target)
    focus = st.session_state.get("le_focus")
    token = focus[2] if focus and focus[0] == "eq" and focus[1] == target else None
    pinned = st.session_state.setdefault("le_initial", {})
    initial = pinned.setdefault(key, initial)
    value = mathlive_editor(label, initial_latex=initial, key=key, mode=mode, variables=_palette(record.working), focus_token=token)
    if value is not None and _applied().get(key) != value:
        _applied()[key] = value
        _apply_latex(mid, target, value)
        if st.session_state.pop("_le_rerun", False):
            pinned.pop(key, None)
            st.rerun()
    error = _errors().get(target)
    if error:
        st.markdown(f"{chip('error', 'Not applied')} &nbsp;{html.escape(error)}", unsafe_allow_html=True)
        st.caption("The model keeps its last valid version until this is fixed.")
    row = st.container(horizontal=True, vertical_alignment="center")
    row.button("Close editor", key=f"close_{key}", icon=":material/check:", on_click=_open_eq, args=(mid, None))
    row.caption("Changes apply as you type. Use **Symbols** for ≤, ≥, fractions and subscripts.")


# ---------------------------------------------------------------------------
#  Callbacks for row widgets
# ---------------------------------------------------------------------------

def _guard(fn, *args) -> None:
    try:
        fn(*args)
    except (EditError, ValueError) as exc:
        state.flash(str(exc), "error")


def _set_sense(mid: str) -> None:
    _guard(state.ws().set_objective, mid, None, st.session_state[_k(mid, "sense")])


def _set_rel(mid: str, uid: str) -> None:
    _guard(state.ws().set_relation, mid, uid, st.session_state[_k(mid, f"rel_{uid}")])


def _set_rhs(mid: str, uid: str) -> None:
    value = st.session_state.get(_k(mid, f"rhs_{uid}"))
    if value is None:
        state.flash("The right-hand side needs a number.", "error")
        return
    _guard(state.ws().set_rhs, mid, uid, value)


def _rename_con(mid: str, uid: str) -> None:
    key = _k(mid, f"ren_{uid}")
    try:
        state.ws().rename_constraint(mid, uid, st.session_state[key])
    except EditError as exc:
        state.flash(str(exc), "error")
        record = state.ws().model(mid)
        st.session_state[key] = record.working.constraint_by_uid(uid).name


def _remove_con(mid: str, uid: str) -> None:
    if st.session_state.get("le_active_eq") == uid:
        st.session_state.pop("le_active_eq", None)
    _guard(state.ws().remove_constraint, mid, uid)


def _start_new_con(mid: str) -> None:
    flush_active(mid)
    st.session_state["le_active_eq"] = "new"
    st.session_state["le_focus"] = ("eq", "new", _focus_token())


def _add_new_con(mid: str) -> None:
    record = state.ws().model(mid)
    spec = record.working
    latex = st.session_state.get(_ml_key(mid, "new")) or ""
    name = (st.session_state.get(_k(mid, "new_name")) or "").strip() or None
    try:
        lhs, relation, rhs = latex_to_constraint(latex, [v.name for v in spec.variables], symbols(spec))
        if relation is None:
            raise LatexError("Include a relation (≤, ≥ or =) and a right-hand side, e.g. x + y ≤ 10.")
        state.ws().add_constraint(mid, name, lhs, relation, rhs)
    except (LatexError, EditError) as exc:
        _errors()["new"] = str(exc)
        return
    _errors().pop("new", None)
    st.session_state.pop("le_active_eq", None)
    st.session_state.pop(_k(mid, "new_name"), None)
    st.session_state.pop(_ml_key(mid, "new"), None)
    state.flash("Constraint added.", "success")


def _discard_new_con() -> None:
    st.session_state.pop("le_active_eq", None)
    _errors().pop("new", None)


# ---------------------------------------------------------------------------
#  Variables table
# ---------------------------------------------------------------------------

INFINITE = {"", "inf", "+inf", "-inf", "∞", "+∞", "-∞", "−∞", "none", "infinity", "-infinity", "+infinity"}


def _bound_text(value: Optional[float], lower: bool) -> str:
    if value is None:
        return "−∞" if lower else "+∞"
    return f"{value:g}"


def _parse_bound(value: Any, what: str) -> Optional[float]:
    """Empty or ∞ means unbounded; anything else must be a finite number."""
    if value is None:
        return None
    text = str(value).strip().lower().replace(",", "")
    if text in INFINITE:
        return None
    try:
        number = float(text.replace("−", "-"))
    except ValueError as exc:
        raise EditError(f"{what} must be a number, or empty / ∞ for no bound.") from exc
    if math.isnan(number) or math.isinf(number):
        return None
    return number


def _var_key(mid: str) -> str:
    return _k(mid, f"vars_{st.session_state.get('le_var_nonce', 0)}")


def _vars_changed(mid: str, uids: List[str]) -> None:
    w = state.ws()
    changes = st.session_state.get(_var_key(mid)) or {}
    messages = []
    for index, edit in (changes.get("edited_rows") or {}).items():
        uid = uids[int(index)]
        try:
            if "Name" in edit and edit["Name"]:
                w.rename_variable(mid, uid, str(edit["Name"]))
            current = w.model(mid).working.variable_by_uid(uid)
            domain = edit.get("Domain", current.variable_type)
            lower = _parse_bound(edit["Lower bound"], "The lower bound") if "Lower bound" in edit else current.lower_bound
            upper = _parse_bound(edit["Upper bound"], "The upper bound") if "Upper bound" in edit else current.upper_bound
            if domain == "binary" and current.variable_type != "binary":
                lower = 0.0 if "Lower bound" not in edit else lower
                upper = 1.0 if "Upper bound" not in edit else upper
            w.set_variable(mid, uid, domain, lower, upper)
        except EditError as exc:
            messages.append(str(exc))
    for row in changes.get("added_rows") or []:
        spec = w.model(mid).working
        name = (row.get("Name") or "").strip()
        if not name:
            index = len(spec.variables) + 1
            while f"x{index}" in spec.variable_map():
                index += 1
            name = f"x{index}"
        try:
            w.add_variable(mid, name, row.get("Domain") or "continuous",
                           _parse_bound(row["Lower bound"], "The lower bound") if "Lower bound" in row else 0.0,
                           _parse_bound(row.get("Upper bound"), "The upper bound"))
        except EditError as exc:
            messages.append(str(exc))
    deleted = [uids[int(i)] for i in changes.get("deleted_rows") or []]
    if deleted:
        st.session_state["le_pending_delete"] = deleted
    for message in messages:
        state.flash(message, "error")
    st.session_state["le_var_nonce"] = st.session_state.get("le_var_nonce", 0) + 1


def _confirm_delete(mid: str, uid: str) -> None:
    try:
        state.ws().remove_variable(mid, uid)
        state.flash("Variable removed.", "success")
    except EditError as exc:
        state.flash(str(exc), "error")
    pending = [u for u in st.session_state.get("le_pending_delete", []) if u != uid]
    st.session_state["le_pending_delete"] = pending


def _keep_variable(uid: str) -> None:
    st.session_state["le_pending_delete"] = [u for u in st.session_state.get("le_pending_delete", []) if u != uid]


def _render_delete_prompts(mid: str) -> None:
    w = state.ws()
    for uid in list(st.session_state.get("le_pending_delete", [])):
        try:
            impact = w.variable_impact(mid, uid)
        except EditError:
            _keep_variable(uid)
            continue
        with st.container(border=True, key=f"del_{uid}"):
            parts = []
            if impact["objective"] is not None:
                parts.append(f"the objective (coefficient {fmt_num(impact['objective'])})")
            if impact["constraints"]:
                shown = ", ".join(f"{n} ({fmt_num(c)})" for n, c in impact["constraints"][:6])
                more = f" and {len(impact['constraints']) - 6} more" if len(impact["constraints"]) > 6 else ""
                parts.append(f"{len(impact['constraints'])} constraint(s): {shown}{more}")
            used = " and ".join(parts) if parts else "nothing else"
            st.markdown(f"{chip('edited', 'Confirm removal')} &nbsp;Remove **{html.escape(impact['name'])}**? It appears in {used}.",
                        unsafe_allow_html=True)
            if impact["emptied_constraints"]:
                st.markdown("These constraints only use this variable and will be removed too: "
                            + ", ".join(f"`{n}`" for n in impact["emptied_constraints"]))
            if impact["objective_would_be_empty"]:
                st.warning("It's the only variable in the objective, so it can't be removed until the objective uses another variable.")
            row = st.container(horizontal=True)
            row.button("Remove variable", key=f"delok_{uid}", icon=":material/delete:", disabled=impact["objective_would_be_empty"],
                       on_click=_confirm_delete, args=(mid, uid))
            row.button("Keep it", key=f"delno_{uid}", on_click=_keep_variable, args=(uid,))


def _render_variables(mid: str) -> None:
    record = state.ws().model(mid)
    spec = record.working
    usage: Dict[str, int] = {}
    for c in spec.constraints:
        for name in c.expression.coefficients:
            usage[name] = usage.get(name, 0) + 1
    variables = spec.variables
    st.markdown(f"#### Variables · {len(variables):,}")
    if len(variables) > VAR_PAGE:
        c1, c2, c3 = st.columns([3, 1.2, 1.6], vertical_alignment="bottom")
        query = c1.text_input("Search variables", key=_k(mid, "var_q"), placeholder="Filter by name…", label_visibility="collapsed")
        if query:
            variables = [v for v in variables if query.lower() in v.name.lower()]
        pages = max(1, -(-len(variables) // VAR_PAGE))
        page = c2.number_input("Page", 1, pages, 1, key=_k(mid, "var_page"), label_visibility="collapsed")
        c3.caption(f"{len(variables):,} of {len(spec.variables):,} · page {page}/{pages}")
        variables = variables[(page - 1) * VAR_PAGE: page * VAR_PAGE]
    uids = [v.uid for v in variables]
    frame = pd.DataFrame([{
        "Name": v.name, "Domain": v.variable_type,
        "Lower bound": _bound_text(v.lower_bound, True), "Upper bound": _bound_text(v.upper_bound, False),
        "In objective": v.name in spec.objective.expression.coefficients, "Constraints": usage.get(v.name, 0),
    } for v in variables], columns=["Name", "Domain", "Lower bound", "Upper bound", "In objective", "Constraints"])
    st.data_editor(
        frame, key=_var_key(mid), num_rows="dynamic", hide_index=True, width="stretch",
        height="auto" if len(frame) <= 12 else 420,
        disabled=["In objective", "Constraints"],
        column_config={
            "Name": st.column_config.TextColumn("Name", required=True, help="Renaming updates every reference."),
            "Domain": st.column_config.SelectboxColumn("Domain", options=["continuous", "integer", "binary"], required=True),
            "Lower bound": st.column_config.TextColumn("Lower bound", help="A number, or −∞ / empty for no lower bound. 0 means ≥ 0."),
            "Upper bound": st.column_config.TextColumn("Upper bound", help="A number, or +∞ / empty for no upper bound."),
            "In objective": st.column_config.CheckboxColumn("In objective"),
            "Constraints": st.column_config.NumberColumn("Used in", help="Number of constraints using this variable."),
        },
        on_change=_vars_changed, args=(mid, uids),
    )
    st.caption("Add a row to create a variable (defaults to ≥ 0). ∞ means unbounded, which is different from 0. "
               "Deleting a row asks before anything is removed.")
    _render_delete_prompts(mid)


# ---------------------------------------------------------------------------
#  Actions
# ---------------------------------------------------------------------------

def _solve(mid: str) -> None:
    w = state.ws()
    error = flush_active(mid)
    active = st.session_state.get("le_active_eq")
    if error and active:
        st.session_state["le_focus"] = ("eq", active, _focus_token())
        state.flash(f"Not solved: {error}", "error")
        return
    issues = w.model(mid).working.issues()
    if issues:
        first = issues[0]
        if first["target"] == "constraint" and first["uid"]:
            st.session_state["le_focus"] = ("rhs", first["uid"], _focus_token())
        state.flash(f"Not solved: {first['message']}", "error")
        return
    w.submit_run(mid, state.pref("solver"), float(state.pref("time_limit")), origin="live_editor")


def _reset(mid: str) -> None:
    state.ws().reset_to_baseline(mid)
    state.bump_epoch(mid)
    _errors().clear()
    state.flash("Reset to the baseline. Results from edited versions are kept as historical.", "success")


def _toggle_preview() -> None:
    st.session_state["le_preview"] = not st.session_state.get("le_preview", False)


def _open_rev(mid: str, rev: str) -> None:
    state.ws().open_revision(mid, rev)
    state.bump_epoch(mid)
    _errors().clear()


def _start_sweep(mid: str) -> None:
    w = state.ws()
    flush_active(mid)
    uid = st.session_state.get(_k(mid, "sw_con"))
    raw = st.session_state.get(_k(mid, "sw_vals")) or ""
    try:
        values = [float(v) for v in re.split(r"[,\s;]+", raw.strip()) if v]
    except ValueError:
        state.flash("Sweep values must be numbers separated by commas.", "error")
        return
    try:
        w.start_sweep(mid, uid, values, state.pref("solver"), float(state.pref("time_limit")))
    except (EditError, Exception) as exc:
        state.flash(str(exc), "error")


def _cancel_sweep(sweep_id: str) -> None:
    from src.services import jobs

    sweep = state.ws().sweeps.get(sweep_id)
    job = jobs.get(sweep.job_id) if sweep else None
    if job:
        job.cancel()


@st.fragment(run_every=0.7)
def _sweep_progress(sweep_id: str) -> None:
    from src.services import jobs

    w = state.ws()
    w.poll()
    sweep = w.sweeps.get(sweep_id)
    if sweep is None or sweep.status != "running":
        st.rerun(scope="app")
        return
    job = jobs.get(sweep.job_id)
    progress = job.progress if job else {}
    st.progress(min(1.0, progress.get("fraction") or 0.0), text=f"{progress.get('stage', 'Running')} · {progress.get('detail', '')}")
    st.button("Cancel sweep", key=f"swc_{sweep_id}", icon=":material/stop_circle:", on_click=_cancel_sweep, args=(sweep_id,),
              help="Stops after the point that is currently solving.")


def _render_sweep(mid: str) -> None:
    w = state.ws()
    record = w.model(mid)
    spec = record.working
    with st.expander("Sensitivity sweep", icon=":material/stacked_line_chart:"):
        st.caption("Re-solves copies of the model with different right-hand sides. Your draft is not changed.")
        options = [c.uid for c in spec.constraints]
        names = {c.uid: c.name for c in spec.constraints}
        c1, c2 = st.columns([1.2, 2], vertical_alignment="bottom")
        con_key = _k(mid, "sw_con")
        if st.session_state.get(con_key) not in options:
            st.session_state[con_key] = options[0]
        c1.selectbox("Constraint", options, format_func=lambda u: names.get(u, u), key=con_key)
        current = spec.constraint_by_uid(st.session_state[con_key])
        vals_key = _k(mid, "sw_vals")
        if vals_key not in st.session_state and current is not None:
            base = current.rhs
            st.session_state[vals_key] = ", ".join(f"{v:g}" for v in (base * 0.75, base * 0.875, base)) if base else "0, 5, 10"
        c2.text_input("Right-hand-side values", key=vals_key, help="Comma-separated, up to 200 values.")
        latest = next((w.sweeps[s] for s in reversed(record.sweep_ids) if s in w.sweeps), None)
        running = latest is not None and latest.status == "running"
        st.button("Run sweep", key=_k(mid, "sw_go"), icon=":material/play_arrow:", disabled=running, on_click=_start_sweep, args=(mid,))
        if latest is None:
            return
        st.markdown(f"**{html.escape(latest.constraint_name)}** · {record.revision_label(latest.revision_id)} · "
                    f"{SOLVERS.get(latest.solver, {}).get('full', latest.solver)}")
        if running:
            _sweep_progress(latest.id)
            return
        if latest.error:
            st.error(latest.error)
            return
        rows = [{"RHS": p["rhs"], "Status": p["status"], "Objective": p["objective"], "Solver": p["solver"]} for p in latest.points]
        if latest.status == "cancelled":
            st.caption(f"Cancelled after {len(rows)} of {len(latest.values)} points.")
        if rows:
            frame = pd.DataFrame(rows)
            if len(frame) <= 50:
                shown = frame.assign(RHS=frame["RHS"].map(fmt_num), Objective=frame["Objective"].map(fmt_num))
                st.table(shown.set_index("RHS"))
            else:
                st.dataframe(frame, hide_index=True, width="stretch")
            ok = frame.dropna(subset=["Objective"])
            if len(ok) > 1:
                st.line_chart(ok, x="RHS", y="Objective", color="#1D4ED8", height=220)


def _render_compare(mid: str) -> None:
    w = state.ws()
    data = w.compare(mid)
    if not data:
        return
    with st.container(border=True, key=f"cmp_{mid}"):
        st.markdown("#### Compare with baseline")
        c1, c2, c3 = st.columns(3)
        c1.metric("Baseline objective", fmt_num(data["baseline_objective"]), help=data.get("baseline_status"))
        c2.metric("Edited objective", fmt_num(data["edited_objective"]), help=data.get("edited_status"))
        diff = data["difference"]
        c3.metric("Difference", "—" if diff is None else fmt_num(diff),
                  delta=None if diff in (None, 0) else fmt_num(diff), delta_color="normal")
        if data["changes"]:
            st.markdown("**What changed:** " + "; ".join(html.escape(c) for c in data["changes"][:12]))
        rows = [r for r in data["variables"] if r["change"] is None or abs(r["change"]) > 1e-9] or data["variables"]
        if rows:
            frame = pd.DataFrame(rows).rename(columns={"variable": "Variable", "baseline": "Baseline", "edited": "Edited", "change": "Change"})
            paged_table(frame, f"cmp_{mid}", "Variable", page_size=50)


def _render_history(mid: str) -> None:
    w = state.ws()
    record = w.model(mid)
    runs = w.runs_for(mid)
    if not runs:
        return
    with st.expander(f"Run history ({len(runs)})", icon=":material/history:"):
        for run in reversed(runs):
            result = run.result or {}
            row = st.container(horizontal=True, vertical_alignment="center", key=f"hist_{run.id}")
            label = result.get("status", "Running" if run.pending else run.status)
            row.markdown(f"{chip(status_kind(run), label)} &nbsp;**{record.revision_label(run.revision_id)}** · "
                         f"objective {fmt_num(result.get('objective'))} · {SOLVERS.get(result.get('resolved') or run.requested_solver, {}).get('label', '')}"
                         f" · {run.origin.replace('_', ' ')}" + (" · historical" if run.historical else ""), unsafe_allow_html=True)
            row.space("stretch")
            current = run.revision_id == record.working_revision
            row.button("Current" if current else "Open this version", key=f"hopen_{run.id}", disabled=current,
                       on_click=_open_rev, args=(mid, run.revision_id))


FOCUS_JS = """
<script>
(function(){
  const doc = window.parent && window.parent.document ? window.parent.document : document;
  let tries = 0;
  const go = () => {
    const el = doc.querySelector(".st-key-%s input, .st-key-%s textarea");
    if (!el) { if (tries++ < 20) setTimeout(go, 100); return; }
    el.scrollIntoView({block: "center"}); el.focus(); el.select && el.select();
  };
  setTimeout(go, 100);
})();
</script>
"""


# ---------------------------------------------------------------------------
#  Page
# ---------------------------------------------------------------------------

def _empty() -> None:
    st.info("No model is open. Start from a template, write one in the Algebraic tab, or load a problem.", icon=":material/edit_note:")
    row = st.container(horizontal=True)
    row.button("Easy Start", key="le_empty_tpl", icon=":material/auto_awesome_mosaic:", on_click=state.go, args=("playground", "Easy Start"))
    row.button("Algebraic", key="le_empty_alg", icon=":material/function:", on_click=state.go, args=("playground", "Algebraic"))


def render() -> None:
    w = state.ws()
    record = w.active()
    if record is None:
        _empty()
        return
    mid = record.id
    spec = record.working
    active = st.session_state.get("le_active_eq")
    issues = spec.issues()
    issue_by_uid: Dict[str, List[str]] = {}
    for issue in issues:
        if issue["uid"]:
            issue_by_uid.setdefault(issue["uid"], []).append(issue["message"])

    # Objective ----------------------------------------------------------
    with st.container(border=True, key=f"le_obj_{mid}"):
        st.markdown("#### Objective")
        sense_key = _k(mid, "sense")
        if st.session_state.get(sense_key) != spec.objective.sense:
            st.session_state[sense_key] = spec.objective.sense
        cols = st.columns([1.4, 5], vertical_alignment="center")
        cols[0].segmented_control("Direction", ["maximize", "minimize"], key=sense_key, required=True,
                                  format_func=lambda s: s.title(), label_visibility="collapsed", on_change=_set_sense, args=(mid,))
        if active == "obj":
            cols[1].caption("Editing below")
        else:
            cols[1].button(f"${objective_latex(spec, 10)}$", key=_k(mid, "obj_btn"), type="tertiary",
                           help="Edit the objective expression", on_click=_open_eq, args=(mid, "obj"))
        if active == "obj":
            _equation_editor(mid, "obj", objective_latex(spec), "objective", "Objective expression")

    # Constraints --------------------------------------------------------
    with st.container(border=True, key=f"le_cons_{mid}"):
        constraints = spec.constraints
        head = st.container(horizontal=True, vertical_alignment="center")
        head.markdown(f"#### Constraints · {len(constraints):,}")
        head.space("stretch")
        head.button("Add Constraint", key=_k(mid, "add_con"), icon=":material/add:", on_click=_start_new_con, args=(mid,))
        if len(constraints) > CON_PAGE:
            c1, c2, c3 = st.columns([3, 1.2, 1.6], vertical_alignment="bottom")
            query = c1.text_input("Search constraints", key=_k(mid, "con_q"), placeholder="Filter by name…", label_visibility="collapsed")
            if query:
                constraints = [c for c in constraints if query.lower() in c.name.lower()]
            pages = max(1, -(-len(constraints) // CON_PAGE))
            page = c2.number_input("Page", 1, pages, 1, key=_k(mid, "con_page"), label_visibility="collapsed")
            c3.caption(f"{len(constraints):,} of {len(spec.constraints):,} · page {page}/{pages}")
            constraints = constraints[(page - 1) * CON_PAGE: page * CON_PAGE]
        with st.container(key="le_con_head"):
            labels = st.columns([1.3, 4.4, 1.1, 1.5, 0.9])
            for col, text in zip(labels, ["Name", "Expression", "Relation", "Right-hand side", ""]):
                col.caption(text)
        for c in constraints:
            uid = c.uid
            rel_key, rhs_key = _k(mid, f"rel_{uid}"), _k(mid, f"rhs_{uid}")
            if st.session_state.get(rel_key) != c.sense:
                st.session_state[rel_key] = c.sense
            if st.session_state.get(rhs_key) != c.rhs:
                st.session_state[rhs_key] = float(c.rhs)
            with st.container(key=f"crow_{uid}"):
                cols = st.columns([1.3, 4.4, 1.1, 1.5, 0.9], vertical_alignment="center")
                cols[0].markdown(f"**{html.escape(c.name)}**")
                if active == uid:
                    cols[1].caption("Editing below")
                else:
                    cols[1].button(f"${lhs_latex(spec, c, 8)}$", key=_k(mid, f"btn_{uid}"), type="tertiary",
                                   help=f"Edit the expression of {c.name}", on_click=_open_eq, args=(mid, uid))
                cols[2].selectbox("Relation", RELATIONS, key=rel_key, format_func=lambda s: REL_TEXT[s],
                                  label_visibility="collapsed", on_change=_set_rel, args=(mid, uid))
                cols[3].number_input("Right-hand side", key=rhs_key, label_visibility="collapsed", step=1.0, format="%g",
                                     on_change=_set_rhs, args=(mid, uid))
                with cols[4].popover("", icon=":material/more_vert:", help=f"Rename or remove {c.name}"):
                    ren_key = _k(mid, f"ren_{uid}")
                    if ren_key not in st.session_state:
                        st.session_state[ren_key] = c.name
                    st.text_input("Rename constraint", key=ren_key, on_change=_rename_con, args=(mid, uid))
                    st.button("Remove constraint", key=_k(mid, f"rm_{uid}"), icon=":material/delete:", disabled=len(spec.constraints) == 1,
                              on_click=_remove_con, args=(mid, uid))
                for message in issue_by_uid.get(uid, []):
                    st.markdown(f"{chip('error', 'Invalid')} &nbsp;{html.escape(message)}", unsafe_allow_html=True)
                if active == uid:
                    _equation_editor(mid, uid, lhs_latex(spec, c), "expression", f"Left-hand side of {c.name}")
        if active == "new":
            with st.container(border=True, key=f"le_new_{mid}"):
                st.markdown("**New constraint**")
                st.text_input("Name (optional)", key=_k(mid, "new_name"), placeholder="e.g. Storage")
                focus = st.session_state.get("le_focus")
                mathlive_editor("New constraint", initial_latex="", key=_ml_key(mid, "new"), mode="expression",
                                variables=_palette(spec), focus_token=focus[2] if focus and focus[1] == "new" else None)
                if _errors().get("new"):
                    st.markdown(f"{chip('error', 'Not added')} &nbsp;{html.escape(_errors()['new'])}", unsafe_allow_html=True)
                row = st.container(horizontal=True)
                row.button("Add", key=_k(mid, "new_ok"), icon=":material/add:", on_click=_add_new_con, args=(mid,))
                row.button("Discard", key=_k(mid, "new_no"), on_click=_discard_new_con)

    # Variables -----------------------------------------------------------
    with st.container(border=True, key=f"le_vars_{mid}"):
        _render_variables(mid)

    # Actions -------------------------------------------------------------
    unsolved = w.has_unsolved_edits(mid)
    current = w.current_run(mid)
    pending = current is not None and current.pending
    with st.container(key="le_actions", horizontal=True, vertical_alignment="center", gap="small"):
        st.button("Solve Edited Model" if record.is_edited else "Solve Model", key=_k(mid, "solve"), type="primary",
                  icon=":material/play_arrow:", disabled=pending, on_click=_solve, args=(mid,),
                  help=f"{SOLVERS[state.pref('solver')]['full']} · {state.pref('time_limit')}s limit")
        st.button("Hide Math" if st.session_state.get("le_preview") else "Preview Math", key=_k(mid, "preview"),
                  icon=":material/functions:", on_click=_toggle_preview)
        st.button("Reset to Baseline", key=_k(mid, "reset"), icon=":material/restart_alt:", disabled=not record.is_edited,
                  on_click=_reset, args=(mid,))
        st.space("stretch")
        if unsolved:
            st.markdown(chip("edited", "Unsolved edits"), unsafe_allow_html=True)
        elif record.is_edited:
            st.markdown(chip("info", f"{record.revision_label(record.working_revision)} solved"), unsafe_allow_html=True)
        else:
            st.markdown(chip("neutral", "Baseline"), unsafe_allow_html=True)

    if st.session_state.get("le_preview"):
        with st.container(border=True, key=f"le_preview_{mid}"):
            show_model(spec, max_rows=200)

    if current is not None:
        render_run(current, record, where="le", open_button=False)
    elif unsolved:
        st.caption("These edits haven't been solved yet. The results below belong to earlier versions.")
    _render_compare(mid)
    _render_sweep(mid)
    _render_history(mid)

    focus = st.session_state.pop("le_focus", None) if st.session_state.get("le_focus", ("",))[0] == "rhs" else None
    if focus:
        key = _k(mid, f"rhs_{focus[1]}")
        st.html(FOCUS_JS % (key, key), unsafe_allow_javascript=True)
