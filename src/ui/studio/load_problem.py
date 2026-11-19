"""Load Problem dialog: Examples, Upload and MIPLIB."""

from __future__ import annotations

import hashlib

import pandas as pd
import streamlit as st

from src.modeling.format_detect import FORMAT_LABELS
from src.services import catalog, jobs, miplib_service
from src.services.model_entry import MAX_UPLOAD_BYTES, UPLOAD_LABEL, UPLOAD_TYPES, import_upload
from src.ui.studio import state
from src.ui.studio.mathview import show_model


def close() -> None:
    st.session_state.pop("dlg_load", None)


def start_miplib_load(name: str, where: str) -> None:
    w = state.ws()
    try:
        name = miplib_service.validate_name(name)
    except miplib_service.MiplibError as exc:
        state.flash(str(exc), "error")
        return

    def work(job):
        def progress(received, total):
            detail = f"{received / 1e6:.2f} MB" + (f" of {total / 1e6:.2f} MB" if total else "")
            job.set_progress("Downloading from miplib.zib.de", received / total if total else None, detail)

        job.handle["cancellable_now"] = True
        if miplib_service.is_downloaded(name):
            job.set_progress("Found in the local file cache")
        path, from_cache = miplib_service.download(name, progress=progress, cancel=job.cancel_event)
        job.handle["cancellable_now"] = False
        job.set_progress("Reading the MPS file", None, path.name)
        spec = miplib_service.load_spec(name)
        return {"spec": spec, "from_cache": from_cache}

    job = jobs.submit("miplib", f"MIPLIB {name}", work, cancellable=True)
    w.add_message("assistant", "miplib_load", job_id=job.id, name=name, where=where)


def _example_to_chat(example_id: str) -> None:
    e = catalog.example(example_id)
    state.set_pref("draft", e["text"])
    state.set_pref("fmt", e["format"])
    state.go("chat")
    close()


def _example_to_algebraic(example_id: str) -> None:
    e = catalog.example(example_id)
    state.set_pref("alg_text", e["text"])
    state.set_pref("alg_fmt", e["format"])
    state.go("playground", "Algebraic")
    close()


def _examples_tab(where: str) -> None:
    category = st.pills("Category", catalog.CATEGORIES, default=catalog.CATEGORIES[0], key="lp_cat", required=True)
    for e in [e for e in catalog.EXAMPLES if e["category"] == category]:
        with st.container(border=True, key=f"ex_{e['id']}"):
            st.markdown(f"**{e['title']}**  \n<span class='ors-kv'>{FORMAT_LABELS[e['format']]} · {e['source']}"
                        + (f" · Expected: {e['expected']}" if e.get("expected") else "") + "</span>", unsafe_allow_html=True)
            with st.expander("Preview source"):
                st.code(e["text"], language="python" if e["format"] == "orlearn" else None)
            row = st.container(horizontal=True)
            chat_primary = where == "chat" or e["format"] == "natural"
            row.button("Use in Chat", key=f"exc_{e['id']}", icon=":material/chat:", type="primary" if chat_primary else "secondary",
                       on_click=_example_to_chat, args=(e["id"],))
            if e["format"] in ("orlearn", "ampl"):
                row.button("Open in Algebraic", key=f"exa_{e['id']}", icon=":material/function:",
                           type="secondary" if chat_primary else "primary", on_click=_example_to_algebraic, args=(e["id"],))


def _upload_model_to_chat(key: str) -> None:
    outcome = st.session_state["upload_outcomes"][key]
    w = state.ws()
    record = w.add_model(outcome.spec, outcome.spec.name or outcome.filename, {"kind": "upload", "filename": outcome.filename,
                                                                              "format": outcome.detected})
    message = w.add_message("user", "submission", text=f"Uploaded {outcome.filename}", format="auto", detected=outcome.detected,
                            solver=state.pref("solver"), time_limit=float(state.pref("time_limit")), note="file upload")
    w.submit_run(record.id, state.pref("solver"), float(state.pref("time_limit")), origin="chat")
    w.add_message("assistant", "run", submission=message["id"], model_id=record.id, format=outcome.detected, notes=[])
    state.go("chat")
    close()


def _upload_model_to_editor(key: str) -> None:
    outcome = st.session_state["upload_outcomes"][key]
    w = state.ws()
    record = w.add_model(outcome.spec, outcome.spec.name or outcome.filename, {"kind": "upload", "filename": outcome.filename,
                                                                              "format": outcome.detected})
    state.bump_epoch(record.id)
    state.go("playground", "Live Editor")
    close()


def _upload_text_to_chat(key: str) -> None:
    outcome = st.session_state["upload_outcomes"][key]
    state.set_pref("draft", outcome.text[:20000])
    state.set_pref("fmt", "auto")
    state.go("chat")
    close()


def _upload_tab() -> None:
    st.caption(f"Accepted: {UPLOAD_LABEL} · up to {MAX_UPLOAD_BYTES // (1024 * 1024)} MB "
               "(compressed MPS files may expand to at most 400 MB). A file that fails to import never replaces your current model.")
    upload = st.file_uploader("Choose a file", type=UPLOAD_TYPES, key="lp_upload", max_upload_size=MAX_UPLOAD_BYTES // (1024 * 1024))
    if upload is None:
        return
    data = upload.getvalue()
    key = hashlib.sha1(upload.name.encode() + data).hexdigest()[:12]
    outcomes = st.session_state.setdefault("upload_outcomes", {})
    if key not in outcomes:
        with st.spinner(f"Reading {upload.name}…"):
            outcomes[key] = import_upload(upload.name, data)
    outcome = outcomes[key]
    if not outcome.ok:
        st.error(f"{upload.name}: {outcome.message}", icon=":material/error:")
        st.caption("Your active model is unchanged.")
        return
    if outcome.kind == "model":
        spec = outcome.spec
        stats = spec.stats()
        st.success(f"{outcome.message} {stats['variables']:,} variables · {stats['constraints']:,} constraints · "
                   f"{stats['nonzeros']:,} non-zeros ({spec.problem_class()}).", icon=":material/check_circle:")
        if stats["constraints"] <= 30 and stats["variables"] <= 40:
            show_model(spec)
        row = st.container(horizontal=True)
        row.button("Solve in Chat", key=f"upc_{key}", type="primary", icon=":material/play_arrow:", on_click=_upload_model_to_chat, args=(key,))
        row.button("Open in Live Editor", key=f"upe_{key}", icon=":material/edit:", on_click=_upload_model_to_editor, args=(key,))
        return
    st.info(outcome.message, icon=":material/description:")
    preview = outcome.preview or {}
    for sheet in (preview.get("sheets") or [])[:3]:
        st.caption(f"Sheet {sheet['name']} · {sheet['row_count']:,} rows")
        if sheet["rows"]:
            st.dataframe(pd.DataFrame(sheet["rows"]), hide_index=True, height=220)
    if preview.get("pages"):
        st.caption(f"{preview['pages']} page(s) of text extracted.")
    if outcome.text:
        st.text_area("Extracted text", outcome.text[:4000], height=180, disabled=True, key=f"upt_{key}")
    st.button("Put text in the composer", key=f"upx_{key}", icon=":material/chat:", on_click=_upload_text_to_chat, args=(key,))


def _miplib_go(name: str, where: str) -> None:
    start_miplib_load(name, where)
    close()
    if where == "chat":
        state.go("chat")


def _miplib_tab(where: str) -> None:
    section = st.segmented_control("Section", ["Recommended", "Browse", "By name", "Cached"], default="Recommended",
                                   key="lp_mip_section", required=True, label_visibility="collapsed")
    st.caption("Loading downloads the instance (cancellable) and reads it. Solving is a separate step afterwards.")
    if section == "Recommended":
        for item in miplib_service.RECOMMENDED:
            cached = miplib_service.is_downloaded(item["name"])
            with st.container(horizontal=True, vertical_alignment="center", key=f"mip_rec_{item['name']}"):
                st.markdown(f"**{item['name']}** <span class='ors-kv'>· {item['desc']}" + (" · cached" if cached else "") + "</span>",
                            unsafe_allow_html=True)
                st.space("stretch")
                st.button("Load" if cached else "Download & load", key=f"mipl_{item['name']}",
                          icon=":material/folder_open:" if cached else ":material/download:",
                          on_click=_miplib_go, args=(item["name"], where))
    elif section == "Browse":
        names = st.session_state.get("mip_easy")
        row = st.container(horizontal=True, vertical_alignment="center")
        if row.button("Fetch the MIPLIB 2017 'easy' list" if not names else "Refresh list", key="mip_fetch", icon=":material/cloud_download:"):
            try:
                with st.spinner("Contacting miplib.zib.de…"):
                    names, from_cache = miplib_service.easy_instances(force=bool(names))
                st.session_state["mip_easy"] = names
                st.session_state["mip_easy_cached"] = from_cache
            except miplib_service.MiplibError as exc:
                st.error(str(exc))
        if names:
            row.caption(f"{len(names):,} instances" + (" (from the local list cache)" if st.session_state.get("mip_easy_cached") else ""))
            query = st.text_input("Search instances", key="mip_q", placeholder="e.g. neos, air, markshare")
            matches = [n for n in names if query.lower() in n.lower()] if query else names
            pick = st.selectbox(f"{len(matches):,} match(es)", matches[:500], key="mip_pick")
            if pick:
                st.button(f"Load {pick}", key="mip_browse_go", type="primary", icon=":material/download:", on_click=_miplib_go, args=(pick, where))
    elif section == "By name":
        name = st.text_input("Instance name", key="mip_name", placeholder="e.g. flugpl or neos5.mps.gz")
        error = None
        if name:
            try:
                miplib_service.validate_name(name)
            except miplib_service.MiplibError as exc:
                error = str(exc)
        if error:
            st.error(error)
        st.button("Load", key="mip_name_go", type="primary", icon=":material/download:", disabled=not name or bool(error),
                  on_click=_miplib_go, args=(name, where))
    else:
        files = miplib_service.downloaded_files()
        st.markdown("**Downloaded instances**")
        if files:
            st.dataframe(pd.DataFrame(files).rename(columns={"name": "Instance", "size_kb": "Size (KB)", "modified": "Downloaded"}),
                         hide_index=True, width="stretch")
            pick = st.selectbox("Instance", [f["name"] for f in files], key="mip_cached_pick")
            st.button(f"Load {pick}", key="mip_cached_go", icon=":material/folder_open:", on_click=_miplib_go, args=(pick, where))
        else:
            st.caption("No instances downloaded yet.")
        st.markdown("**Cached solutions**")
        cached = miplib_service.list_cached_solutions()
        if cached:
            st.dataframe(pd.DataFrame([{"Instance": c["instance"], "Solver": c.get("solver_used") or c["solver_key"],
                                        "Objective": c.get("objective_value"), "Cached at": (c.get("timestamp") or "")[:16]} for c in cached]),
                         hide_index=True, width="stretch")
        else:
            st.caption("No solutions cached yet. Solving a MIPLIB instance stores its result here.")
        confirm = st.checkbox("I understand cached data will be deleted", key="mip_clear_ok")
        row = st.container(horizontal=True)
        if row.button("Clear solution cache", key="mip_clear_sol", disabled=not confirm, icon=":material/delete_sweep:"):
            miplib_service.clear_solution_cache()
            st.toast("Solution cache cleared.")
        if row.button("Delete downloaded files", key="mip_clear_files", disabled=not confirm, icon=":material/delete:"):
            count = miplib_service.clear_file_cache()
            st.toast(f"Deleted {count} file(s).")


@st.dialog("Load Problem", width="large", on_dismiss=close)
def dialog(where: str) -> None:
    if "dlg_load" not in st.session_state:
        st.rerun(scope="app")
    examples, upload, miplib = st.tabs(["Examples", "Upload", "MIPLIB"])
    with examples:
        _examples_tab(where)
    with upload:
        _upload_tab()
    with miplib:
        _miplib_tab(where)
