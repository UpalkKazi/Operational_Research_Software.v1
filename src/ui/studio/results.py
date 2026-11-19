"""Result cards: one per Run, rendered inline where the run was started."""

from __future__ import annotations

import time
from typing import Any, Dict, Optional

import pandas as pd
import streamlit as st

from src.services import exporters, jobs
from src.services.interpretation import fmt, key_decisions, offline_summary
from src.services.workspace import ModelRecord, Run
from src.solvers.backends import SOLVERS
from src.ui.studio import state
from src.ui.studio.mathview import bounds_text
from src.ui.studio.styles import chip

PAGE = 100


def status_kind(run: Run) -> str:
    if run.pending:
        return "running"
    if run.status == "failed":
        return "error"
    return (run.result or {}).get("kind", "error")


def solver_label(key: str) -> str:
    return SOLVERS.get(key, {}).get("full", key)


def paged_table(df: pd.DataFrame, key: str, search_column: str, page_size: int = PAGE, height: Optional[int] = None) -> None:
    total = len(df)
    if total > page_size:
        c1, c2, c3 = st.columns([3, 1.2, 1.6], vertical_alignment="bottom")
        query = c1.text_input("Search", key=f"{key}_q", placeholder=f"Filter by {search_column}…", label_visibility="collapsed")
        if query:
            df = df[df[search_column].astype(str).str.contains(query, case=False, regex=False)]
        pages = max(1, -(-len(df) // page_size))
        page = c2.number_input("Page", 1, pages, 1, key=f"{key}_p", label_visibility="collapsed")
        c3.caption(f"{len(df):,} of {total:,} rows · page {page}/{pages}")
        df = df.iloc[(page - 1) * page_size: page * page_size]
    if len(df) <= 20:
        st.table(df.set_index(df.columns[0]))
    else:
        st.dataframe(df, hide_index=True, width="stretch", height=height or 420)


@st.fragment(run_every=0.7)
def _live_progress(run_id: str) -> None:
    w = state.ws()
    w.poll()
    run = w.runs.get(run_id)
    if run is None or not run.pending:
        st.rerun(scope="app")
        return
    job = jobs.get(run.job_id)
    elapsed = job.elapsed if job else 0.0
    stage = job.progress.get("stage", "Running") if job else "Queued"
    limit = f" · limit {run.time_limit:g}s" if run.time_limit else ""
    st.markdown(f"{chip('running', 'Running')} &nbsp; {stage} · **{elapsed:.1f}s**{limit}", unsafe_allow_html=True)
    if job and job.cancellable:
        if st.button("Cancel solve", key=f"cancel_{run_id}", icon=":material/stop_circle:", help="Stops SCIP and keeps the best plan found so far."):
            job.cancel()
            st.toast("Cancellation requested.")
    else:
        st.caption(f"{solver_label(run.requested_solver)} can't be interrupted mid-solve; it will stop at the time limit.")


def _open_in_playground(model_id: str, revision_id: str) -> None:
    w = state.ws()
    w.open_revision(model_id, revision_id)
    state.bump_epoch(model_id)
    state.go("playground", "Live Editor")


def _resolve_without_cache(model_id: str, revision_id: str, solver: str, time_limit, origin: str) -> None:
    state.ws().submit_run(model_id, solver, time_limit, origin=origin, revision_id=revision_id, use_cache=False)


def render_run(run: Run, record: ModelRecord, where: str, open_button: bool = True, compact: bool = False) -> None:
    w = state.ws()
    spec = record.revisions.get(run.revision_id)
    result: Dict[str, Any] = run.result or {}
    kind = status_kind(run)
    rev_label = record.revision_label(run.revision_id)

    with st.container(border=True, key=f"run_{where}_{run.id}"):
        badges = [chip(kind, result.get("status") if not run.pending and result else "")]
        if run.historical:
            badges.append(chip("neutral", "Historical"))
        if run.cache_hit:
            badges.append(chip("info", "From cache"))
        st.markdown(
            " ".join(badges) + f' &nbsp;<span class="ors-kv"><b>{record.name}</b> · {rev_label}</span>',
            unsafe_allow_html=True,
        )

        if run.pending:
            _live_progress(run.id)
            return
        if run.status == "failed":
            st.error(f"The solve job failed: {run.error}", icon=":material/error:")
            return

        backend = result.get("backend") or solver_label(result.get("resolved") or run.requested_solver)
        cols = st.columns(3 if compact else 4)
        cols[0].metric("Objective", fmt(result.get("objective")))
        cols[1].metric("Solver", SOLVERS.get(result.get("resolved"), {}).get("label", "—"), help=backend)
        cols[2].metric("Time", f"{result.get('elapsed', 0):.2f}s" if not run.cache_hit else "cached")
        if not compact:
            gap = result.get("gap")
            cols[3].metric("Gap", "—" if gap is None else f"{gap * 100:.2f}%")

        if kind == "unsupported":
            st.warning(result.get("explanation") or "This solver can't run this model.", icon=":material/do_not_disturb_on:")
            st.button("Solve with Auto instead", key=f"auto_{where}_{run.id}", icon=":material/auto_mode:",
                      on_click=lambda: w.submit_run(record.id, "auto", run.time_limit, origin=run.origin, revision_id=run.revision_id))
            return

        decisions = key_decisions(result)
        if decisions:
            st.markdown("**Key decisions** &nbsp;" + " &nbsp;·&nbsp; ".join(f"`{n}` = **{fmt(v)}**" for n, v in decisions), unsafe_allow_html=True)
        summary = offline_summary(result, spec)
        st.markdown(summary["summary"])
        st.caption(f"Solved by {backend}" + (f" ({result.get('backend_version')})" if result.get("backend_version") else "")
                   + (f" · requested {solver_label(run.requested_solver)}" if run.requested_solver != result.get("resolved") else ""))

        _details(run, record, spec, result, summary, where)

        actions = st.container(horizontal=True)
        if open_button and spec is not None:
            actions.button("Open in Playground", key=f"open_{where}_{run.id}", icon=":material/open_in_new:",
                           on_click=_open_in_playground, args=(record.id, run.revision_id),
                           help=f"Opens {rev_label} of {record.name} in the Live Editor.")
        if run.cache_hit:
            actions.button("Re-solve (ignore cache)", key=f"nocache_{where}_{run.id}", icon=":material/refresh:",
                           on_click=_resolve_without_cache, args=(record.id, run.revision_id, run.requested_solver, run.time_limit, run.origin))


def _details(run: Run, record: ModelRecord, spec, result: Dict[str, Any], summary: Dict[str, Any], where: str) -> None:
    values = result.get("variables") or {}
    vmap = spec.variable_map() if spec else {}
    with st.expander(f"Variables ({len(values):,})", icon=":material/table_rows:"):
        reduced = result.get("reduced_costs") or {}
        rows = []
        for name, value in values.items():
            v = vmap.get(name)
            rows.append({
                "Variable": name, "Value": value,
                "Domain": v.variable_type if v else "",
                "Bounds": bounds_text(v.lower_bound, v.upper_bound) if v else "",
                "Reduced cost": reduced.get(name),
            })
        if rows:
            paged_table(pd.DataFrame(rows), f"vars_{where}_{run.id}", "Variable")
        else:
            st.caption("No variable values were returned.")

    constraints = result.get("constraints") or {}
    with st.expander(f"Constraints ({len(constraints):,})", icon=":material/rule:"):
        rows = [{
            "Constraint": name, "Activity": r.get("activity"), "Relation": {"<=": "≤", ">=": "≥", "=": "="}.get(r.get("sense"), r.get("sense")),
            "RHS": r.get("rhs"), "Slack": r.get("slack"), "Dual": r.get("dual"),
            "Status": "Binding" if r.get("binding") else "Slack",
        } for name, r in constraints.items()]
        if rows:
            paged_table(pd.DataFrame(rows), f"cons_{where}_{run.id}", "Constraint")
        else:
            st.caption("No constraint activity was returned.")

    with st.expander("Charts", icon=":material/bar_chart:"):
        nonzero = [(n, v) for n, v in values.items() if v is not None and abs(v) > 1e-9]
        if nonzero:
            nonzero.sort(key=lambda item: -abs(item[1]))
            top = nonzero[:25]
            st.caption("Decision values" + (f" (largest 25 of {len(nonzero):,} non-zero)" if len(nonzero) > 25 else ""))
            st.bar_chart(pd.DataFrame(top, columns=["Variable", "Value"]), x="Variable", y="Value", horizontal=True,
                         color="#1D4ED8", height=max(160, 28 * len(top)))
        usage = [(n, 100 * r["activity"] / r["rhs"]) for n, r in constraints.items()
                 if r.get("sense") == "<=" and r.get("rhs") and r["rhs"] > 0 and r.get("activity") is not None][:25]
        if usage:
            st.caption("Capacity used by ≤ constraints (%)")
            st.bar_chart(pd.DataFrame(usage, columns=["Constraint", "Used %"]), x="Constraint", y="Used %", horizontal=True,
                         color="#0F766E", height=max(140, 28 * len(usage)))
        if not nonzero and not usage:
            st.caption("Nothing to chart for this run.")

    with st.expander("Interpretation", icon=":material/lightbulb:"):
        st.markdown(summary["summary"])
        for bullet in summary["bullets"]:
            st.markdown(f"- {bullet}")
        st.caption("Generated offline from the solver output — no AI provider involved.")
        ai = result.get("ai_interpretation")
        if ai:
            st.markdown("**Provider explanation**")
            st.markdown(ai.get("summary") or ai.get("explanation") or str(ai))

    with st.expander("Diagnostics", icon=":material/monitor_heart:"):
        source = record.source
        info = {
            "Run": run.id, "Model revision": f"{record.revision_label(run.revision_id)} ({run.revision_id}, fingerprint {spec.fingerprint() if spec else '—'})",
            "Requested solver": solver_label(run.requested_solver),
            "Actual backend": (result.get("backend") or "—") + (f" · {result['backend_version']}" if result.get("backend_version") else ""),
            "Why this solver": result.get("explanation") or "—",
            "Status": result.get("status"), "Time limit": f"{run.time_limit:g}s" if run.time_limit else "none",
            "Elapsed (incl. model build)": f"{result.get('elapsed', 0):.3f}s", "Solver time": f"{result.get('solve_time') or 0:.3f}s",
            "Origin": run.origin, "Cache hit": "yes" if run.cache_hit else "no",
        }
        stats = result.get("stats") or (spec.stats() if spec else {})
        if stats:
            info["Size"] = f"{stats.get('variables', 0):,} variables ({stats.get('integer', 0):,} integer, {stats.get('binary', 0):,} binary) · {stats.get('constraints', 0):,} constraints · {stats.get('nonzeros', 0):,} non-zeros"
        orl = source.get("orlearn")
        if orl:
            lib = orl.get("library") or {}
            info["OR-Learn API invoked"] = orl.get("invoked") or "—"
            info["OR-Learn library"] = f"{lib.get('version', '?')} @ {lib.get('commit', '?')[:8]}" + (" (pinned)" if lib.get("pinned") else " (NOT the pinned commit)")
        check = result.get("library_check") or run.library_check
        if check:
            info["OR-Learn cross-check"] = (f"{check.get('call')} → {fmt(check.get('value'))}" if check.get("available")
                                            else f"unavailable ({check.get('error', 'not supported')})")
        st.table(pd.DataFrame({"Field": list(info.keys()), "Value": [str(v) for v in info.values()]}).set_index("Field"))
        for message in result.get("messages") or []:
            st.caption(f"• {message}")

    with st.expander("Exports", icon=":material/download:"):
        meta = {"run_id": run.id, "model": record.name, "revision": run.revision_id, "requested_solver": run.requested_solver,
                "time_limit": run.time_limit, "created": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(run.created))}
        slug = "".join(ch if ch.isalnum() else "_" for ch in record.name.lower())[:40] or "model"
        row = st.container(horizontal=True)
        row.download_button("Result (JSON)", exporters.result_json(result, spec, meta), f"{slug}_{run.revision_id}_result.json",
                            "application/json", key=f"dl_json_{where}_{run.id}", icon=":material/data_object:")
        row.download_button("Variables (CSV)", exporters.variables_csv(result, spec), f"{slug}_{run.revision_id}_variables.csv",
                            "text/csv", key=f"dl_vcsv_{where}_{run.id}", icon=":material/table_view:")
        row.download_button("Constraints (CSV)", exporters.constraints_csv(result), f"{slug}_{run.revision_id}_constraints.csv",
                            "text/csv", key=f"dl_ccsv_{where}_{run.id}", icon=":material/table_view:")
        if spec is not None:
            row.download_button("Model (AMPL-style)", exporters.spec_to_ampl(spec), f"{slug}_{run.revision_id}.mod",
                                "text/plain", key=f"dl_mod_{where}_{run.id}", icon=":material/function:")
            row.download_button("Model (LP format)", exporters.spec_to_lp(spec), f"{slug}_{run.revision_id}.lp",
                                "text/plain", key=f"dl_lp_{where}_{run.id}", icon=":material/description:")
