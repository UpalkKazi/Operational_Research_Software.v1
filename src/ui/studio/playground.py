"""Model Playground: header, Easy Start, Algebraic and the Live Editor tab."""

from __future__ import annotations

import html
import re
from typing import Any, Dict, Optional

import pandas as pd
import streamlit as st

from src.modeling.format_detect import FORMAT_LABELS, detect_format
from src.services import catalog, jobs
from src.services.interpretation import fmt as fmt_num
from src.services.model_entry import ParseOutcome, parse_structured, source_hash
from src.solvers.backends import SOLVERS
from src.ui.studio import live_editor, state, styles
from src.ui.studio.header import solver_format, solver_options
from src.ui.studio.mathview import show_model
from src.ui.studio.results import render_run, status_kind
from src.ui.studio.styles import chip

TABS = ["Easy Start", "Algebraic", "Live Editor"]
TAB_ICONS = {"Easy Start": "auto_awesome_mosaic", "Algebraic": "function", "Live Editor": "edit_note"}


# ---------------------------------------------------------------------------
#  Header
# ---------------------------------------------------------------------------

def _activate(model_id: str) -> None:
    state.ws().activate(model_id)
    state.bump_epoch(model_id)


def _open_loader() -> None:
    st.session_state["dlg_load"] = "playground"


def model_status(record) -> tuple:
    w = state.ws()
    if w.has_unsolved_edits(record.id):
        return "edited", "Unsolved edits"
    run = w.current_run(record.id)
    if run is None:
        return "neutral", "Not solved"
    if run.pending:
        return "running", "Solving"
    return status_kind(run), (run.result or {}).get("status", run.status)


def source_label(record) -> str:
    source = record.source
    kind = source.get("kind")
    if kind == "miplib":
        return f"MIPLIB 2017 · {source.get('miplib')}"
    if kind == "upload":
        return f"Upload · {source.get('filename')}"
    if kind == "template":
        return f"Easy Start template · {source.get('template')}"
    fmt = FORMAT_LABELS.get(source.get("format"), source.get("format", ""))
    return f"{'Chat' if kind == 'chat' else 'Algebraic'} · {fmt}"


def render_header() -> None:
    w = state.ws()
    record = w.active()
    with st.container(border=True, key="pg_header"):
        with st.container(horizontal=True, vertical_alignment="center", gap="small"):
            if record is None:
                st.markdown("**No model loaded** <span class='ors-kv'>· choose a template, write one in Algebraic, or load a problem</span>",
                            unsafe_allow_html=True)
            else:
                stats = record.working.stats()
                kind, label = model_status(record)
                ints = stats["integer"] + stats["binary"]
                st.markdown(
                    f"<span style='font-size:1.1rem;font-weight:700'>{html.escape(record.name)}</span> &nbsp;{chip(kind, label)}<br>"
                    f"<span class='ors-kv'>{html.escape(source_label(record))} · <b>{stats['variables']:,}</b> variables"
                    + (f" ({ints:,} integer)" if ints else "")
                    + f" · <b>{stats['constraints']:,}</b> constraints · {record.working.problem_class()}"
                    + f" · {html.escape(record.revision_label(record.working_revision) if record.working_revision else 'Unsaved draft')}</span>",
                    unsafe_allow_html=True,
                )
            st.space("stretch")
            state.bound(st.selectbox, "solver", "pg_solver", label="Solver", options=solver_options(), format_func=solver_format,
                        label_visibility="collapsed", width=170, help="Solver used by every Solve button in the Playground.")
            with st.popover("Solver settings", icon=":material/tune:"):
                from src.ui.studio.header import settings_panel

                settings_panel("pg")
            if len(w.models) > 1:
                with st.popover("Models", icon=":material/stacks:", help="Switch between models in this session. Edits are kept."):
                    for model in reversed(list(w.models.values())):
                        active = record is not None and model.id == record.id
                        edited = " · edited" if model.is_edited else ""
                        st.button(f"{model.name}{edited}", key=f"sw_{model.id}", disabled=active, width="stretch",
                                  icon=":material/radio_button_checked:" if active else ":material/radio_button_unchecked:",
                                  on_click=_activate, args=(model.id,))
            st.button("Load Problem", key="pg_load", icon=":material/upload_file:", on_click=_open_loader)


# ---------------------------------------------------------------------------
#  Replacing the model in the editor
# ---------------------------------------------------------------------------

def _needs_confirm(target_model_id: Optional[str]) -> bool:
    w = state.ws()
    record = w.active()
    return record is not None and record.id != target_model_id and w.has_unsolved_edits(record.id)


@st.dialog("Replace the model in the editor?")
def confirm_replace() -> None:
    pending = st.session_state.get("pending_replace")
    if not pending:
        st.rerun(scope="app")
    record = state.ws().active()
    st.markdown(f"**{html.escape(record.name)}** has edits that haven't been solved. "
                "Loading the new model switches the editor to it; your edits stay available under **Models**.")
    row = st.container(horizontal=True)
    if row.button("Keep Editing", key="cr_keep", type="primary"):
        st.session_state.pop("pending_replace", None)
        state.go("playground", "Live Editor")
        st.rerun(scope="app")
    if row.button(pending.get("label", "Load"), key="cr_go"):
        st.session_state.pop("pending_replace", None)
        _perform(pending)
        st.rerun(scope="app")


def _perform(pending: Dict[str, Any]) -> None:
    if pending["kind"] == "template":
        _template_action(pending["key"], pending["action"], confirmed=True)
    elif pending["kind"] == "algebraic":
        _algebraic_action(pending["hash"], pending["action"], confirmed=True)


# ---------------------------------------------------------------------------
#  Easy Start
# ---------------------------------------------------------------------------

def _template_outcome(key: str) -> ParseOutcome:
    cache = st.session_state.setdefault("_tpl_parse", {})
    if key not in cache:
        cache[key] = parse_structured(catalog.template(key)["text"], "ampl")
    return cache[key]


def _template_model(key: str) -> str:
    w = state.ws()
    models = st.session_state.setdefault("tpl_models", {})
    existing = w.model(models.get(key))
    if existing is not None and not existing.is_edited:
        return existing.id
    tpl = catalog.template(key)
    outcome = _template_outcome(key)
    record = w.add_model(outcome.spec, tpl["subtitle"], {"kind": "template", "template": tpl["title"], "format": "ampl",
                                                        "text": tpl["text"], "ampl": outcome.ampl}, activate=False)
    models[key] = record.id
    return record.id


def _select_template(key: str) -> None:
    state.set_pref("tpl_selected", key)
    st.session_state["_scroll_to"] = "tpl_preview"


def _template_action(key: str, action: str, confirmed: bool = False) -> None:
    w = state.ws()
    models = st.session_state.setdefault("tpl_models", {})
    target = models.get(key)
    if not confirmed and _needs_confirm(target if w.model(target) and not w.model(target).is_edited else None):
        st.session_state["pending_replace"] = {"kind": "template", "key": key, "action": action,
                                               "label": "Load Template"}
        return
    model_id = _template_model(key)
    w.activate(model_id)
    state.bump_epoch(model_id)
    if action == "solve":
        w.submit_run(model_id, state.pref("solver"), float(state.pref("time_limit")), origin="easy_start")
    else:
        state.go("playground", "Live Editor")


def render_easy_start() -> None:
    selected = state.pref("tpl_selected")
    st.markdown("### Start from a template")
    st.caption("Pick a classic model, preview it, then solve it or adjust it in the Live Editor.")
    templates = catalog.TEMPLATES
    for start in range(0, len(templates), 3):
        cols = st.columns(3)
        for col, tpl in zip(cols, templates[start:start + 3]):
            is_sel = tpl["key"] == selected
            with col.container(border=True, key=f"tplcard_{'sel_' if is_sel else ''}{tpl['key']}"):
                st.markdown(f"#### {tpl['icon']} {tpl['title']}")
                st.caption(tpl["subtitle"])
                st.button("Selected" if is_sel else "Select", key=f"tplsel_{tpl['key']}", width="stretch",
                          icon=":material/check:" if is_sel else None, type="primary" if is_sel else "secondary",
                          on_click=_select_template, args=(tpl["key"],),
                          help=f"Preview the {tpl['title'].lower()} template")
    if not selected:
        st.info("Select a template to preview its equations.", icon=":material/touch_app:")
        return
    tpl = catalog.template(selected)
    outcome = _template_outcome(selected)
    with st.container(border=True, key="tpl_preview"):
        stats = outcome.spec.stats()
        st.markdown(f"### {tpl['icon']} {tpl['title']} · {tpl['subtitle']}")
        st.caption(f"{stats['variables']} variables · {stats['constraints']} constraints · {outcome.spec.problem_class()} · "
                   f"solver: {SOLVERS[state.pref('solver')]['full']}")
        show_model(outcome.spec)
        with st.expander("AMPL-style source"):
            st.code(tpl["text"], language=None)
        row = st.container(horizontal=True)
        w = state.ws()
        model_id = st.session_state.get("tpl_models", {}).get(selected)
        pending = model_id is not None and w.pending_run(model_id, None) is not None
        row.button("Solve Template", key="tpl_solve", type="primary", icon=":material/play_arrow:", disabled=pending,
                   on_click=_template_action, args=(selected, "solve"))
        row.button("Edit in Live Editor", key="tpl_edit", icon=":material/edit_note:", on_click=_template_action, args=(selected, "edit"))
        if model_id and w.model(model_id):
            record = w.model(model_id)
            runs = [r for r in w.runs_for(model_id) if r.origin == "easy_start"]
            if runs:
                render_run(runs[-1], record, where="tpl")
                if len(runs) > 1:
                    st.caption(f"{len(runs) - 1} earlier run(s) of this template are listed in the Live Editor's run history.")


# ---------------------------------------------------------------------------
#  Algebraic
# ---------------------------------------------------------------------------

def _alg_parse(text: str, fmt: str) -> Dict[str, Any]:
    """Parse (memoised by content hash). Returns dict with resolved fmt and outcome."""
    resolved = fmt
    detection = None
    if fmt == "auto":
        detection = detect_format(text)
        resolved = detection.format
    key = source_hash(text, resolved)
    cache = st.session_state.setdefault("_alg_parse", {})
    if key not in cache:
        if len(cache) > 32:
            cache.clear()
        if resolved in ("orlearn", "ampl"):
            cache[key] = {"fmt": resolved, "outcome": parse_structured(text, resolved), "hash": key}
        else:
            cache[key] = {"fmt": resolved, "outcome": None, "hash": key, "detection": detection}
    return cache[key]


def _load_alg_example(example_id: str) -> None:
    e = catalog.example(example_id)
    state.set_pref("alg_text", e["text"])
    state.set_pref("alg_fmt", e["format"])


def _algebraic_action(expected_hash: str, action: str, confirmed: bool = False) -> None:
    w = state.ws()
    text = st.session_state.get("w_alg_text", state.pref("alg_text")) or ""
    state.set_pref("alg_text", text)
    parsed = _alg_parse(text, state.pref("alg_fmt"))
    if parsed["hash"] != expected_hash:
        state.flash("The source changed after it was validated. Review the preview, then try again.", "warning")
        return
    outcome: ParseOutcome = parsed["outcome"]
    if outcome is None or not outcome.ok:
        state.flash("Fix the highlighted problem first.", "warning")
        return
    if outcome.library_only:
        plan = outcome.orlearn["plan"]

        def work(job):
            from src.modeling.orlearn_adapter import reference_solve

            return reference_solve(plan)

        st.session_state.setdefault("alg_lib", {})[expected_hash] = jobs.submit("library", "OR-Learn network solve", work).id
        return
    models = st.session_state.setdefault("alg_models", {})
    target = models.get(expected_hash)
    record = w.model(target)
    if not confirmed and _needs_confirm(target if record is not None and not record.is_edited else None):
        st.session_state["pending_replace"] = {"kind": "algebraic", "hash": expected_hash, "action": action,
                                               "label": "Load Model"}
        return
    if record is None or record.is_edited:
        from src.ui.studio.chat import title_from_text

        source = {"kind": "algebraic", "format": parsed["fmt"], "text": text, "notes": outcome.notes, "hash": expected_hash}
        if outcome.orlearn:
            source["orlearn"] = {k: v for k, v in outcome.orlearn.items() if k != "plan"}
            source["orlearn_plan"] = outcome.orlearn["plan"]
        if outcome.ampl:
            source["ampl"] = outcome.ampl
        name = title_from_text(text, "OR-Learn model" if parsed["fmt"] == "orlearn" else "AMPL model")
        record = w.add_model(outcome.spec, name, source)
        models[expected_hash] = record.id
    w.activate(record.id)
    state.bump_epoch(record.id)
    if action == "solve":
        w.submit_run(record.id, state.pref("solver"), float(state.pref("time_limit")), origin="algebraic", revision_id="r0")
    else:
        state.go("playground", "Live Editor")


def _param_frames(params: Dict[str, Any], sets: Dict[str, list]):
    for name, param in params.items():
        if not isinstance(param, dict):
            yield name, None, param
            continue
        index_sets = param.get("index_sets") or []
        values = param.get("values") or {}
        if len(index_sets) == 1:
            frame = pd.DataFrame({index_sets[0]: [k[0] for k in values], name: list(values.values())})
            yield name, frame, None
        elif len(index_sets) == 2:
            rows = sets.get(index_sets[0]) or sorted({k[0] for k in values})
            cols = sets.get(index_sets[1]) or sorted({k[1] for k in values})
            data = {c: [values.get((r, c), param.get("default")) for r in rows] for c in cols}
            frame = pd.DataFrame(data, index=rows)
            frame.index.name = f"{index_sets[0]} \\ {index_sets[1]}"
            yield name, frame, None
        else:
            frame = pd.DataFrame([{**{s: k[i] for i, s in enumerate(index_sets)}, name: v} for k, v in values.items()])
            yield name, frame, None


def _render_alg_preview(text: str, parsed: Dict[str, Any]) -> None:
    outcome: Optional[ParseOutcome] = parsed["outcome"]
    if not text.strip():
        st.info("Paste or type a model, or use **Load Example**.", icon=":material/edit:")
        return
    if outcome is None:
        detection = parsed.get("detection")
        if parsed["fmt"] == "ambiguous":
            st.warning("This could be more than one format (" + "; ".join(detection.reasons if detection else []) +
                       "). Choose OR-Learn or AMPL-style above.", icon=":material/help:")
        else:
            st.warning("This reads like a description, not a model. The Algebraic tab accepts OR-Learn or AMPL-style syntax; "
                       "descriptions go to Chat (needs an AI provider).", icon=":material/chat:")
        return
    if not outcome.ok:
        where = f"Line {outcome.line}" + (f", column {outcome.column}" if outcome.column else "") if outcome.line else "Input"
        st.markdown(f"{chip('error', 'Not valid')} &nbsp;**{where}**", unsafe_allow_html=True)
        st.markdown(html.escape(re.sub(r"^Line \d+(, column \d+)?:\s*", "", outcome.message)))
        lines = text.splitlines()
        if outcome.line and 0 < outcome.line <= len(lines):
            caret = " " * max(0, (outcome.column or 1) - 1) + "^"
            st.html(f'<div class="ors-error-line" role="note">{outcome.line:>4} | {html.escape(lines[outcome.line - 1])}\n     | {caret}</div>')
        return
    label = FORMAT_LABELS[parsed["fmt"]]
    if outcome.library_only:
        st.markdown(f"{chip('info', 'Valid · OR-Learn network problem')}", unsafe_allow_html=True)
        st.markdown(html.escape(outcome.message or ""))
    else:
        stats = outcome.spec.stats()
        st.markdown(f"{chip('optimal', 'Valid ' + label)} &nbsp;<span class='ors-kv'>{stats['variables']} variables · "
                    f"{stats['constraints']} constraints · {outcome.spec.problem_class()}</span>", unsafe_allow_html=True)
        show_model(outcome.spec, max_rows=30)
    if outcome.orlearn:
        info = outcome.orlearn
        lib = info.get("library") or {}
        with st.expander("OR-Learn call chain", expanded=True, icon=":material/code:"):
            st.code(info.get("chain", ""), language="python")
            st.caption(f"Replayed against the real OR-Learn library {lib.get('version', '?')} @ {lib.get('commit', '?')[:8]}"
                       + (" (pinned)" if lib.get("pinned") else " — not the pinned commit") + f" · invoked `{info.get('invoked')}`. "
                       "No pasted Python was executed.")
    if outcome.ampl:
        info = outcome.ampl
        if info.get("sets") or info.get("params") or info.get("indexed"):
            with st.expander("Sets, parameters and indexed variables", icon=":material/grid_on:"):
                for name, members in (info.get("sets") or {}).items():
                    st.markdown(f"**set {name}** = {{{', '.join(map(str, members))}}}")
                for name, frame, scalar in _param_frames(info.get("params") or {}, info.get("sets") or {}):
                    if frame is None:
                        st.markdown(f"**param {name}** = {fmt_num(scalar)}")
                    else:
                        st.markdown(f"**param {name}**")
                        st.dataframe(frame, width="stretch")
                for name, meta in (info.get("indexed") or {}).items():
                    st.markdown(f"**var {name}**{{{', '.join(meta['sets'])}}} → {meta['count']} {meta['domain']} variables, "
                                f"e.g. `{name}[{', '.join((info.get('sets') or {}).get(s, ['?'])[0] for s in meta['sets'])}]`")
    for note in outcome.notes:
        st.caption(f"Note: {note}")


@st.fragment(run_every=0.7)
def _lib_progress(job_id: str) -> None:
    job = jobs.get(job_id)
    if job is None or job.done:
        st.rerun(scope="app")
    st.markdown(f"{chip('running', 'Running OR-Learn')}", unsafe_allow_html=True)


def render_algebraic() -> None:
    left, right = st.columns([1, 1], gap="medium")
    with left:
        with st.container(horizontal=True, vertical_alignment="center", gap="small"):
            state.bound(st.selectbox, "alg_fmt", "alg_fmt", label="Format", options=["auto", "orlearn", "ampl"],
                        format_func=lambda k: FORMAT_LABELS[k], label_visibility="collapsed", width=170)
            with st.popover("Load Example", icon=":material/library_books:"):
                for e in catalog.ALGEBRAIC_EXAMPLES:
                    st.button(f"{e['title']}", key=f"algex_{e['id']}", width="stretch", on_click=_load_alg_example, args=(e["id"],),
                              help=f"{FORMAT_LABELS[e['format']]} · {e['source']}")
        styles.css(styles.MONO_TEXTAREA.format(key=".st-key-w_alg_text"))
        state.bound(st.text_area, "alg_text", "alg_text", label="Model source", height=420, label_visibility="collapsed",
                    placeholder="var x >= 0;\nvar y >= 0;\nmaximize profit: 3*x + 2*y;\nsubject to c1: x + y <= 4;")
        st.caption("OR-Learn code is parsed, never executed. AMPL-style supports sets, params, indexed variables and sums — "
                   "see docs/AMPL_SUBSET.md.")
    text = state.pref("alg_text") or ""
    parsed = _alg_parse(text, state.pref("alg_fmt"))
    outcome = parsed["outcome"]
    with right:
        with st.container(border=True, key="alg_preview"):
            _render_alg_preview(text, parsed)
    valid = outcome is not None and outcome.ok
    row = st.container(horizontal=True)
    w = state.ws()
    model_id = st.session_state.get("alg_models", {}).get(parsed["hash"])
    pending = model_id is not None and w.model(model_id) is not None and w.pending_run(model_id, "r0") is not None
    row.button("Solve Model", key="alg_solve", type="primary", icon=":material/play_arrow:", disabled=not valid or pending,
               on_click=_algebraic_action, args=(parsed["hash"], "solve"))
    row.button("Open in Live Editor", key="alg_open", icon=":material/edit_note:",
               disabled=not valid or bool(outcome and outcome.library_only),
               on_click=_algebraic_action, args=(parsed["hash"], "edit"),
               help="Network problems solved by OR-Learn's own algorithms can't be edited as LP/MIP." if outcome and outcome.library_only else None)
    lib_job = st.session_state.get("alg_lib", {}).get(parsed["hash"])
    if lib_job:
        job = jobs.get(lib_job)
        if job and not job.done:
            _lib_progress(lib_job)
        elif job and job.result:
            r = job.result
            with st.container(border=True):
                st.markdown(f"{chip('optimal' if r.get('optimal') else 'error', 'Solved by OR-Learn' if r.get('optimal') else 'Not solved')} "
                            f"&nbsp;**{fmt_num(r.get('value'))}** via `{r.get('call')}`", unsafe_allow_html=True)
                if isinstance(r.get("solution"), dict) and r["solution"].get("path"):
                    st.markdown("Route: " + " → ".join(f"`{n}`" for n in r["solution"]["path"]))
        elif job and job.error:
            st.error(job.error)
    if model_id and w.model(model_id):
        record = w.model(model_id)
        runs = [r for r in w.runs_for(model_id) if r.origin == "algebraic" and r.revision_id == "r0"]
        if runs:
            render_run(runs[-1], record, where="alg")


# ---------------------------------------------------------------------------
#  Page
# ---------------------------------------------------------------------------

SCROLL_JS = """
<script>
(function(){
  const doc = window.parent && window.parent.document ? window.parent.document : document;
  const target = "%s";
  let tries = 0;
  const go = () => {
    const el = doc.querySelector(".st-key-" + target);
    if (!el) { if (tries++ < 20) setTimeout(go, 100); return; }
    const narrow = (doc.defaultView || window).innerWidth < 900;
    // "auto" lands in one frame; a smooth animation can still be mid-flight
    // when the next rerun repaints, leaving the preview off screen.
    if (narrow || %s) el.scrollIntoView({behavior: "auto", block: "start"});
    const focusable = el.querySelector("button, [tabindex], input");
    if (focusable && narrow) focusable.focus({preventScroll: true});
  };
  setTimeout(go, 80);
})();
</script>
"""


def render() -> None:
    render_header()
    state.bound(st.segmented_control, "pg_tab", "pg_tab", label="Playground section", options=TABS,
                format_func=lambda t: f":material/{TAB_ICONS[t]}: {t}", required=True, label_visibility="collapsed")
    tab = state.pref("pg_tab")
    if tab == "Easy Start":
        render_easy_start()
    elif tab == "Algebraic":
        render_algebraic()
    else:
        live_editor.render()
    if st.session_state.get("pending_replace"):
        confirm_replace()
    scroll = st.session_state.pop("_scroll_to", None)
    if scroll:
        st.html(SCROLL_JS % (scroll, "false"), unsafe_allow_javascript=True)
