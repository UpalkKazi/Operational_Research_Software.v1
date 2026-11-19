"""Chat: one composer for OR-Learn, AMPL-style and natural-language problems."""

from __future__ import annotations

import html
import re
import time
from typing import Any, Dict, Optional

import streamlit as st

from src.modeling.format_detect import FORMAT_LABELS, detect_format
from src.services import jobs
from src.services.ai_service import provider_status, run_natural_language
from src.services.interpretation import fmt as fmt_num
from src.services.model_entry import parse_structured
from src.services.workspace import Run, _id
from src.solvers.backends import SOLVERS
from src.ui.studio import state, styles
from src.ui.studio.header import solver_format, solver_options
from src.ui.studio.results import render_run, solver_label
from src.ui.studio.styles import chip

FORMATS = ["auto", "natural", "orlearn", "ampl"]
STRUCTURED = ("orlearn", "ampl")
PLACEHOLDER = (
    "Describe a problem in plain words, or paste an OR-Learn or AMPL-style model, e.g.\n"
    "maximize profit: 45*chairs + 80*tables;"
)


# ---------------------------------------------------------------------------
#  Helpers
# ---------------------------------------------------------------------------

def title_from_text(text: str, fallback: str) -> str:
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("#"):
            title = line.lstrip("#").strip()
            if title:
                return title[:60]
        elif line and not line.startswith(("from ", "import ")):
            break
    return fallback


def clear_draft() -> None:
    state.set_pref("draft", "")
    st.session_state["w_draft"] = ""


def reply_for(message_id: str) -> Optional[Dict[str, Any]]:
    return next((m for m in state.ws().messages if m.get("submission") == message_id), None)


def submission_status(message: Dict[str, Any]) -> tuple:
    w = state.ws()
    reply = reply_for(message["id"])
    if reply is None:
        return "neutral", "Received"
    kind = reply["kind"]
    if kind == "choose_format":
        return ("info", "Format chosen") if reply.get("chosen") else ("edited", "Needs a format choice")
    if kind == "parse_error":
        return "error", "Parse error — not sent to AI"
    if kind == "credentials":
        return "edited", "Needs AI credentials"
    if kind in ("ai_job", "library_run") and not reply.get("handled"):
        return "running", "Working"
    if reply.get("error"):
        return "error", "Failed"
    if reply.get("model_id"):
        runs = [r for r in w.runs_for(reply["model_id"]) if r.origin == "chat"]
        if runs and runs[-1].pending:
            return "running", "Solving"
        if runs:
            result = runs[-1].result or {}
            return result.get("kind", "neutral"), result.get("status", "Done")
    if kind == "library_run":
        return "optimal", "Solved by OR-Learn"
    return "neutral", "Done"


# ---------------------------------------------------------------------------
#  Submission pipeline
# ---------------------------------------------------------------------------

def submit() -> None:
    w = state.ws()
    text = st.session_state.get("w_draft", state.pref("draft")) or ""
    state.set_pref("draft", text)
    if not text.strip():
        state.flash("Type a problem or load one first.", "warning")
        return
    submission = {"text": text, "format": state.pref("fmt"), "solver": state.pref("solver"), "time_limit": float(state.pref("time_limit"))}
    for message in reversed(w.messages):
        if message["kind"] == "submission":
            same = all(message.get(k) == v for k, v in submission.items())
            if same and submission_status(message)[0] == "running":
                state.flash("That exact problem is already being solved.", "info")
                return
            break
    message = w.add_message("user", "submission", **submission)
    process(message)


def process(message: Dict[str, Any], chosen: Optional[str] = None) -> None:
    w = state.ws()
    text, solver, limit = message["text"], message["solver"], message["time_limit"]
    fmt = chosen or message["format"]
    if fmt == "auto":
        detection = detect_format(text)
        message["detected"] = detection.format
        if detection.format == "ambiguous":
            w.add_message("assistant", "choose_format", submission=message["id"], candidates=detection.candidates, reasons=detection.reasons)
            return
        fmt = detection.format
    message["resolved_format"] = fmt

    if fmt in STRUCTURED:
        outcome = parse_structured(text, fmt)
        if not outcome.ok:
            lines = text.splitlines()
            snippet = lines[outcome.line - 1] if outcome.line and 0 < outcome.line <= len(lines) else ""
            w.add_message("assistant", "parse_error", submission=message["id"], format=fmt, message=outcome.message,
                          line=outcome.line, column=outcome.column, snippet=snippet)
            return
        if outcome.library_only:
            plan = outcome.orlearn["plan"]

            def work(job):
                from src.modeling.orlearn_adapter import reference_solve

                job.set_progress(f"Running OR-Learn {outcome.orlearn['invoked']}")
                return reference_solve(plan)

            job = jobs.submit("library", "OR-Learn network solve", work)
            w.add_message("assistant", "library_run", submission=message["id"], job_id=job.id, orlearn=_orl_info(outcome.orlearn),
                          notes=outcome.notes, reason=outcome.message)
            clear_draft()
            return
        name = title_from_text(text, outcome.spec.name or ("OR-Learn model" if fmt == "orlearn" else "AMPL model"))
        source = {"kind": "chat", "format": fmt, "text": text, "notes": outcome.notes, "hash": outcome.source_hash}
        if outcome.orlearn:
            source["orlearn"] = _orl_info(outcome.orlearn)
            source["orlearn_plan"] = outcome.orlearn["plan"]
        if outcome.ampl:
            source["ampl"] = outcome.ampl
        record = w.add_model(outcome.spec, name, source)
        w.submit_run(record.id, solver, limit, origin="chat")
        w.add_message("assistant", "run", submission=message["id"], model_id=record.id, format=fmt, notes=outcome.notes)
        clear_draft()
        return

    status = provider_status()
    if not status["configured"]:
        w.add_message("assistant", "credentials", submission=message["id"], reason=status["reason"])
        return
    job = jobs.submit("ai", "Natural-language solve", lambda job: run_natural_language(job, text, solver, limit))
    w.add_message("assistant", "ai_job", submission=message["id"], job_id=job.id, provider=status["provider"], model=status["model"])
    clear_draft()


def _orl_info(info: Dict[str, Any]) -> Dict[str, Any]:
    return {k: v for k, v in info.items() if k != "plan"}


def choose_format(choice_id: str, fmt: str) -> None:
    w = state.ws()
    choice = w.message(choice_id)
    submission = w.message(choice["submission"])
    choice["chosen"] = fmt
    message = w.add_message("user", "submission", **{k: submission[k] for k in ("text", "solver", "time_limit")}, format=fmt,
                            note=f"Resubmitted as {FORMAT_LABELS[fmt]}")
    process(message, chosen=fmt)


def poll_messages() -> None:
    """Fold finished background jobs (AI pipeline, OR-Learn network, MIPLIB load) into the history."""
    w = state.ws()
    for message in w.messages:
        if message.get("handled") or not message.get("job_id"):
            continue
        job = jobs.get(message["job_id"])
        if job is None:
            message.update(handled=True, error="The background job was lost (server restarted?).")
            continue
        if not job.done:
            continue
        message["handled"] = True
        message["elapsed"] = job.elapsed
        if job.error:
            message["cancelled"] = job.cancel_event.is_set() and "cancel" in job.error.lower()
            message["error"] = job.error.split(": ", 1)[-1]
            continue
        if message["kind"] == "ai_job":
            _finish_ai(message, job.result)
        elif message["kind"] == "library_run":
            message["result"] = job.result
        elif message["kind"] == "miplib_load":
            spec = job.result["spec"]
            record = w.add_model(spec, f"MIPLIB {message['name']}", {"kind": "miplib", "miplib": message["name"],
                                                                      "from_cache": job.result["from_cache"]})
            message["model_id"] = record.id
            message["from_cache"] = job.result["from_cache"]
            state.bump_epoch(record.id)
            if message.get("where") == "playground":
                state.flash(f"MIPLIB {message['name']} loaded into the Model Playground.", "success")


def _finish_ai(message: Dict[str, Any], payload: Dict[str, Any]) -> None:
    w = state.ws()
    submission = w.message(message["submission"]) or {}
    spec = payload["spec"]
    record = w.add_model(spec, spec.name, {"kind": "chat", "format": "natural", "text": submission.get("text", ""),
                                            "ai_steps": payload.get("steps")})
    result = dict(payload["result"])
    if payload.get("interpretation"):
        result["ai_interpretation"] = payload["interpretation"]
    run = Run(id=_id("run"), model_id=record.id, revision_id="r0", origin="chat",
              requested_solver=submission.get("solver", "auto"), time_limit=submission.get("time_limit"),
              job_id=None, status="done", result=result, finished=time.time())
    w.runs[run.id] = run
    record.run_ids.append(run.id)
    message["model_id"] = record.id
    message["steps"] = payload.get("steps")


# ---------------------------------------------------------------------------
#  Rendering
# ---------------------------------------------------------------------------

@st.fragment(run_every=0.7)
def job_progress(job_id: str, cancel_label: str = "Cancel") -> None:
    job = jobs.get(job_id)
    if job is None or job.done:
        st.rerun(scope="app")
        return
    progress = job.progress
    fraction = progress.get("fraction")
    label = f"{progress.get('stage', 'Working')}" + (f" · {progress['detail']}" if progress.get("detail") else "") + f" · {job.elapsed:.1f}s"
    if fraction is not None:
        st.progress(min(max(float(fraction), 0.0), 1.0), text=label)
    else:
        st.markdown(f"{chip('running', 'Working')} &nbsp; {html.escape(label)}", unsafe_allow_html=True)
    if job.cancellable and job.handle.get("cancellable_now", True):
        if st.button(cancel_label, key=f"jobcancel_{job_id}", icon=":material/stop_circle:"):
            job.cancel()


def _open_loader(where: str) -> None:
    st.session_state["dlg_load"] = where


def _go_templates() -> None:
    state.go("playground", "Easy Start")


def _use_ampl() -> None:
    state.set_pref("fmt", "ampl")


def render_submission(message: Dict[str, Any]) -> None:
    kind, status = submission_status(message)
    fmt = message.get("resolved_format") or message.get("format")
    structured = fmt in STRUCTURED or (fmt == "auto" and message.get("detected") in STRUCTURED)
    with st.chat_message("user", avatar=":material/person:"):
        meta = [FORMAT_LABELS.get(message.get("format"), message.get("format"))]
        if message.get("format") == "auto" and message.get("detected") in FORMAT_LABELS:
            meta[0] = f"Auto → {FORMAT_LABELS[message['detected']]}"
        meta += [SOLVERS.get(message["solver"], {}).get("label", message["solver"]), f"{message['time_limit']:g}s limit"]
        if message.get("note"):
            meta.append(message["note"])
        if structured:
            st.code(message["text"], language="python" if fmt == "orlearn" else None, height=min(360, 26 + 21 * message["text"].count("\n")) if message["text"].count("\n") > 16 else "content")
        else:
            st.html(f'<div class="ors-user">{html.escape(message["text"])}</div>')
        st.markdown(f"{chip(kind, status)} &nbsp;<span class='ors-kv'>{' · '.join(html.escape(m) for m in meta)}</span>", unsafe_allow_html=True)


def render_reply(message: Dict[str, Any]) -> None:
    w = state.ws()
    kind = message["kind"]
    with st.chat_message("assistant", avatar=":material/function:"):
        if kind == "choose_format":
            if message.get("chosen"):
                st.caption(f"Resubmitted as {FORMAT_LABELS[message['chosen']]}.")
                return
            st.markdown("**Which format is this?** It has features of more than one: " + "; ".join(message.get("reasons", [])) + ".")
            row = st.container(horizontal=True)
            for candidate in message.get("candidates", []):
                row.button(f"Treat as {FORMAT_LABELS[candidate]}", key=f"choose_{message['id']}_{candidate}",
                           on_click=choose_format, args=(message["id"], candidate),
                           type="primary" if candidate != "natural" else "secondary")
            return

        if kind == "parse_error":
            where = f"Line {message['line']}" + (f", column {message['column']}" if message.get("column") else "") if message.get("line") else "Input"
            st.markdown(f"{chip('error', 'Parse error')} &nbsp;**{FORMAT_LABELS.get(message['format'])} · {where}**", unsafe_allow_html=True)
            st.markdown(html.escape(re.sub(r"^Line \d+(, column \d+)?:\s*", "", message["message"])))
            if message.get("snippet"):
                caret = " " * max(0, (message.get("column") or 1) - 1) + "^"
                st.html(f'<div class="ors-error-line" role="note" aria-label="Offending line">{message["line"]:>4} | {html.escape(message["snippet"])}\n     | {caret}</div>')
            st.caption("Nothing was sent to an AI provider. Your text is still in the composer; fix the line and solve again.")
            return

        if kind == "credentials":
            st.markdown(f"{chip('edited', 'AI credentials required')}", unsafe_allow_html=True)
            st.markdown(
                "Natural-language problems are turned into models by an AI provider, and none is configured. "
                f"{html.escape(message.get('reason', ''))} Your text is still in the composer."
            )
            st.markdown("**Work offline instead:** write the model in OR-Learn or AMPL-style syntax, start from a template, or load a file or MIPLIB instance.")
            row = st.container(horizontal=True)
            row.button("Try a template", key=f"cred_tpl_{message['id']}", icon=":material/auto_awesome_mosaic:", on_click=_go_templates)
            row.button("Load Problem", key=f"cred_load_{message['id']}", icon=":material/upload_file:", on_click=_open_loader, args=("chat",))
            row.button("Switch format to AMPL-style", key=f"cred_ampl_{message['id']}", icon=":material/function:", on_click=_use_ampl)
            return

        if kind == "ai_job" and not message.get("handled"):
            st.markdown(f"Sent to **{message.get('provider')}** {message.get('model', '')}.")
            job_progress(message["job_id"])
            return

        if kind == "library_run":
            _render_library(message)
            return

        if kind == "miplib_load":
            _render_miplib(message)
            return

        if message.get("error"):
            st.error(message["error"], icon=":material/error:")
            if kind == "ai_job":
                st.caption("The provider call failed. Structured formats, templates and MIPLIB still work without it.")
            return

        if kind in ("run", "ai_job") and message.get("model_id"):
            record = w.model(message["model_id"])
            if record is None:
                return
            if message.get("steps"):
                st.caption(" → ".join(f"{s['step']}: {s['detail']}" for s in message["steps"]))
            orl = record.source.get("orlearn")
            if orl:
                lib = orl.get("library") or {}
                st.caption(f"Parsed with the OR-Learn library {lib.get('version', '')} @ {lib.get('commit', '')[:8]} · invoked `{orl.get('invoked')}`")
            for note in message.get("notes") or []:
                st.caption(f"Note: {note}")
            for run in [r for r in w.runs_for(record.id) if r.origin == "chat"]:
                render_run(run, record, where="chat")
            return

        if kind == "info":
            st.markdown(message.get("text", ""))


def _render_library(message: Dict[str, Any]) -> None:
    orl = message.get("orlearn") or {}
    if not message.get("handled"):
        st.markdown(f"Running OR-Learn `{orl.get('invoked', '')}`…")
        job_progress(message["job_id"])
        return
    if message.get("error"):
        st.error(f"OR-Learn failed: {message['error']}")
        return
    result = message.get("result") or {}
    ok = result.get("optimal")
    st.markdown(f"{chip('optimal' if ok else 'error', 'Solved by OR-Learn' if ok else 'Not solved')}", unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    c1.metric("Value", fmt_num(result.get("value")))
    c2.metric("Algorithm", result.get("call", "—"))
    solution = result.get("solution")
    if isinstance(solution, dict) and solution.get("path"):
        st.markdown("**Route** " + " → ".join(f"`{n}`" for n in solution["path"]))
    elif solution:
        st.json(solution, expanded=False)
    lib = orl.get("library") or {}
    st.caption(f"Network problems run on OR-Learn's own algorithm ({lib.get('version', '')} @ {lib.get('commit', '')[:8]}). "
               "They are not LP/MIP models here, so they can't be opened in the Live Editor.")


def _solve_loaded(model_id: str) -> None:
    w = state.ws()
    w.submit_run(model_id, state.pref("solver"), float(state.pref("time_limit")), origin="chat")


def _open_loaded(model_id: str) -> None:
    state.ws().activate(model_id)
    state.bump_epoch(model_id)
    state.go("playground", "Live Editor")


def _retry_miplib(name: str, where: str) -> None:
    from src.ui.studio.load_problem import start_miplib_load

    start_miplib_load(name, where)


def _render_miplib(message: Dict[str, Any]) -> None:
    w = state.ws()
    name = message["name"]
    origin = " (from the Model Playground)" if message.get("where") == "playground" else ""
    if not message.get("handled"):
        st.markdown(f"Loading MIPLIB instance **{name}**{origin}")
        job_progress(message["job_id"], cancel_label="Cancel download")
        return
    if message.get("error"):
        if message.get("cancelled"):
            st.markdown(f"{chip('cancelled', 'Download cancelled')} &nbsp;**{name}**", unsafe_allow_html=True)
        else:
            st.markdown(f"{chip('error', 'Load failed')} &nbsp;**{name}**", unsafe_allow_html=True)
            st.markdown(html.escape(message["error"]))
        st.caption("The active model was not changed.")
        st.button("Retry", key=f"retry_{message['id']}", icon=":material/refresh:", on_click=_retry_miplib, args=(name, message.get("where", "chat")))
        return
    record = w.model(message.get("model_id"))
    if record is None:
        return
    stats = record.baseline.stats()
    source = "local file cache" if message.get("from_cache") else "miplib.zib.de"
    st.markdown(f"{chip('info', 'Model loaded')} &nbsp;**{name}** from {source} in {message.get('elapsed', 0):.1f}s", unsafe_allow_html=True)
    st.markdown(f"{stats['variables']:,} variables ({stats['binary']:,} binary, {stats['integer']:,} integer, {stats['continuous']:,} continuous) · "
                f"{stats['constraints']:,} constraints · {stats['nonzeros']:,} non-zeros")
    runs = [r for r in w.runs_for(record.id) if r.origin == "chat"]
    row = st.container(horizontal=True)
    pending = any(r.pending for r in runs)
    row.button("Solve", key=f"solve_{message['id']}", type="primary", icon=":material/play_arrow:", disabled=pending,
               on_click=_solve_loaded, args=(record.id,),
               help=f"Solves with {solver_label(state.pref('solver'))}, {state.pref('time_limit')}s limit. Change in Settings.")
    row.button("Open in Playground", key=f"openml_{message['id']}", icon=":material/open_in_new:", on_click=_open_loaded, args=(record.id,))
    for run in runs:
        render_run(run, record, where="chat")


def render_empty() -> None:
    st.html('<div class="ors-hero"><h1>What would you like to optimize?</h1>'
            '<p>Describe a problem, or paste an OR-Learn or AMPL-style model. Structured models solve offline.</p></div>')


def _toolbar_mono_css(draft: str) -> None:
    fmt = state.pref("fmt")
    mono = fmt in STRUCTURED or (fmt == "auto" and detect_format(draft).format in STRUCTURED)
    if mono:
        styles.css(styles.MONO_TEXTAREA.format(key=".st-key-w_draft"))


CTRL_ENTER_JS = """
<script>
(function () {
  const doc = window.parent && window.parent.document ? window.parent.document : document;
  if (doc.__orsCtrlEnter) return;
  doc.__orsCtrlEnter = true;
  doc.addEventListener("keydown", function (e) {
    if (!(e.key === "Enter" && (e.ctrlKey || e.metaKey))) return;
    const box = e.target && e.target.closest ? e.target.closest(".st-key-w_draft") : null;
    if (!box) return;
    e.preventDefault(); e.stopPropagation();
    e.target.blur();
    setTimeout(function () {
      const button = doc.querySelector(".st-key-chat_solve button");
      if (button && !button.disabled) button.click();
    }, 150);
  }, true);
})();
</script>
"""


def render_composer() -> None:
    draft = state.pref("draft") or ""
    _toolbar_mono_css(draft)
    with st.container(border=True, key="composer"):
        state.bound(st.text_area, "draft", "draft", label="Problem", placeholder=PLACEHOLDER,
                    height=150 if not state.ws().messages else 110, label_visibility="collapsed")
        fmt = state.pref("fmt")
        if fmt == "auto" and draft.strip():
            detection = detect_format(draft)
            label = {"orlearn": "OR-Learn", "ampl": "AMPL-style", "natural": "Natural Language", "ambiguous": "unclear — you'll be asked"}.get(detection.format)
            if label:
                st.caption(f"Detected: {label}")
        with st.container(horizontal=True, vertical_alignment="center", gap="small"):
            st.button("Load Problem", key="chat_load", icon=":material/upload_file:", on_click=_open_loader, args=("chat",))
            state.bound(st.selectbox, "fmt", "chat_fmt", label="Format", options=FORMATS, format_func=lambda k: FORMAT_LABELS[k],
                        label_visibility="collapsed", width=180, help="Auto detects OR-Learn and AMPL-style syntax.")
            state.bound(st.selectbox, "solver", "chat_solver", label="Solver", options=solver_options(), format_func=solver_format,
                        label_visibility="collapsed", width=170, help="Auto picks CBC, or SCIP for large integer models.")
            st.space("stretch")
            st.html('<span class="ors-kbd"><kbd>Ctrl</kbd>+<kbd>Enter</kbd></span>', width="content")
            st.button("Solve Problem", key="chat_solve", type="primary", icon=":material/play_arrow:", on_click=submit)
    st.html(CTRL_ENTER_JS, unsafe_allow_javascript=True)


def _insert_example(example_id: str) -> None:
    from src.services.catalog import example

    e = example(example_id)
    state.set_pref("draft", e["text"])
    state.set_pref("fmt", e["format"] if e["format"] != "natural" else "natural")


def render() -> None:
    w = state.ws()
    if not w.messages:
        render_empty()
        render_composer()
        row = st.container(horizontal=True, horizontal_alignment="center")
        row.button("Try a template", key="empty_tpl", icon=":material/auto_awesome_mosaic:", on_click=_go_templates)
        row.button("Load Problem", key="empty_load", icon=":material/upload_file:", on_click=_open_loader, args=("chat",))
        row.button("OR-Learn example", key="empty_orl", icon=":material/code:", on_click=_insert_example, args=("orl-lp",),
                   help="Puts the OR-Learn README production example in the composer.")
        return
    for message in w.messages:
        if message["role"] == "user":
            render_submission(message)
        else:
            render_reply(message)
    st.space("medium")
    render_composer()
