"""Credential-free core of OR Studio: parsing, solving, workspace revisions, imports, exports."""

from __future__ import annotations

import gzip
import io
import time
from pathlib import Path

import pytest

from src.modeling.format_detect import detect_format
from src.modeling.latex_linear import LatexError, latex_to_constraint, latex_to_linear
from src.services import catalog, exporters
from src.services.model_entry import MAX_UPLOAD_BYTES, import_upload, parse_structured
from src.services.workspace import EditError, Workspace
from src.solvers.backends import availability, solve_spec

FIXTURES = Path(__file__).parent / "fixtures" / "uploads"

FIXTURE_AMPL = """
var chairs >= 0;
var tables >= 0;
maximize profit: 45*chairs + 80*tables;
subject to wood: 5*chairs + 20*tables <= 400;
subject to labor: 10*chairs + 15*tables <= 450;
"""

EXPECTED_OBJECTIVE = {
    "orl-lp": 2200, "orl-quick": 9, "ampl-lp": 2200, "ampl-lp-indexed": 2200, "ampl-ip": 40,
    "orl-tp": 4000, "ampl-tp": 2280, "orl-assign": 13, "ampl-assign": 13, "ampl-sched": 5,
    "orl-knap": 220, "ampl-knap": 700,
}


def spec_of(text: str, fmt: str = "ampl"):
    outcome = parse_structured(text, fmt)
    assert outcome.ok, outcome.message
    return outcome.spec


def wait(ws: Workspace, timeout: float = 60) -> None:
    deadline = time.time() + timeout
    while ws.has_pending():
        assert time.time() < deadline, "background solve did not finish"
        ws.poll()
        time.sleep(0.05)
    ws.poll()


# ---------------------------------------------------------------------------
#  Parsing and format detection
# ---------------------------------------------------------------------------

def test_detects_each_format():
    assert detect_format(catalog.example("orl-lp")["text"]).format == "orlearn"
    assert detect_format(FIXTURE_AMPL).format == "ampl"
    assert detect_format("A bakery makes bread and cakes and wants to maximise profit.").format == "natural"
    assert detect_format("   ").format == "empty"


@pytest.mark.parametrize("example", [e for e in catalog.EXAMPLES if e["format"] in ("orlearn", "ampl")], ids=lambda e: e["id"])
def test_every_structured_example_parses_and_solves(example):
    outcome = parse_structured(example["text"], example["format"])
    assert outcome.ok, outcome.message
    if outcome.library_only:
        assert outcome.orlearn and outcome.orlearn["invoked"]
        return
    result = solve_spec(outcome.spec, "pulp_cbc", 30)
    assert result["kind"] == "optimal", result["messages"]
    if example["id"] in EXPECTED_OBJECTIVE:
        assert result["objective"] == pytest.approx(EXPECTED_OBJECTIVE[example["id"]], abs=1e-6)


def test_orlearn_readme_example_uses_pinned_library():
    outcome = parse_structured(catalog.example("orl-lp")["text"], "orlearn")
    assert outcome.ok
    assert outcome.orlearn["invoked"]
    assert "38355732" in str(outcome.orlearn["library"])


def test_ampl_error_reports_line_and_column():
    outcome = parse_structured("var x >= 0;\nmaximize z: x^2;\nsubject to c: x <= 1;", "ampl")
    assert not outcome.ok
    assert outcome.line == 2 and outcome.column


def test_ampl_indexed_sums_expand():
    spec = spec_of(catalog.example("ampl-lp-indexed")["text"])
    assert len(spec.variables) >= 2
    assert all(c.expression.coefficients for c in spec.constraints)


def test_latex_linear_round_trip():
    names = ["chairs", "tables"]
    expr = latex_to_linear(r"45\,\mathrm{chairs}+80\,\mathrm{tables}", names)
    assert expr.coefficients == {"chairs": 45.0, "tables": 80.0}
    lhs, rel, rhs = latex_to_constraint(r"5\mathrm{chairs}+20\mathrm{tables}\le 400", names)
    assert rel == "<=" and rhs == 400 and lhs.coefficients == {"chairs": 5.0, "tables": 20.0}


@pytest.mark.parametrize("latex", [r"\mathrm{chairs}\cdot\mathrm{tables}", r"\sqrt{\mathrm{chairs}}", r"\mathrm{chairs}^2", r"\mathrm{sofas}"])
def test_latex_rejects_nonlinear_and_unknown(latex):
    with pytest.raises(LatexError):
        latex_to_linear(latex, ["chairs", "tables"])


# ---------------------------------------------------------------------------
#  Solver backends
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("key", ["auto", "pulp_cbc", "cvxpy_osqp", "cvxpy_glpk", "cvxpy_scip"])
def test_backends_agree_on_fixture(key):
    if key != "auto" and not availability()[key]["available"]:
        pytest.skip(f"{key} not installed")
    result = solve_spec(spec_of(FIXTURE_AMPL), key, 30)
    assert result["kind"] == "optimal", result["messages"]
    assert result["objective"] == pytest.approx(2200, rel=1e-3)
    assert result["variables"]["chairs"] == pytest.approx(24, abs=1e-2)
    assert result["resolved"] != ""


def test_manual_selection_is_respected_not_replaced():
    spec = spec_of(catalog.example("ampl-ip")["text"])
    result = solve_spec(spec, "cvxpy_osqp", 30)
    assert result["kind"] == "unsupported"
    assert "continuous problems only" in result["explanation"]


# ---------------------------------------------------------------------------
#  Workspace: baseline, edits, compare, sweep, reset, revisions
# ---------------------------------------------------------------------------

def _fixture_workspace():
    ws = Workspace()
    record = ws.add_model(spec_of(FIXTURE_AMPL), "Fixture", {"kind": "test"})
    wood = next(c.uid for c in record.working.constraints if c.name == "wood")
    return ws, record, wood


def test_fixture_baseline_edit_compare_sweep_reset():
    ws, record, wood = _fixture_workspace()
    base = ws.submit_run(record.id, "pulp_cbc", 30, "test")
    wait(ws)
    assert base.result["objective"] == pytest.approx(2200)
    assert base.result["variables"] == pytest.approx({"chairs": 24, "tables": 14})

    ws.set_rhs(record.id, wood, 300)
    assert ws.has_unsolved_edits(record.id)
    edited = ws.submit_run(record.id, "pulp_cbc", 30, "test")
    wait(ws)
    assert edited.revision_id != "r0"
    assert edited.result["objective"] == pytest.approx(2100)
    assert edited.result["variables"] == pytest.approx({"chairs": 36, "tables": 6})
    cmp = ws.compare(record.id)
    assert cmp["difference"] == pytest.approx(-100)
    assert cmp["baseline_objective"] == pytest.approx(2200)
    assert ws.baseline_run(record.id).result["objective"] == pytest.approx(2200)

    draft_before = record.working.fingerprint()
    sweep = ws.start_sweep(record.id, wood, [300, 350, 400], "pulp_cbc", 30)
    wait(ws)
    assert sweep.status == "done"
    assert [p["objective"] for p in sweep.points] == pytest.approx([2100, 2150, 2200])
    assert all(p["kind"] == "optimal" for p in sweep.points)
    assert record.working.fingerprint() == draft_before

    ws.reset_to_baseline(record.id)
    assert record.working.constraint_by_uid(wood).rhs == 400
    assert edited.historical


def test_older_revision_reopens_exactly():
    ws, record, wood = _fixture_workspace()
    ws.set_rhs(record.id, wood, 300)
    first = ws.submit_run(record.id, "pulp_cbc", 30, "test")
    ws.set_rhs(record.id, wood, 350)
    ws.submit_run(record.id, "pulp_cbc", 30, "test")
    wait(ws)
    ws.open_revision(record.id, first.revision_id)
    assert record.working.constraint_by_uid(wood).rhs == 300


def test_duplicate_submission_reuses_pending_run():
    ws, record, _ = _fixture_workspace()
    a = ws.submit_run(record.id, "pulp_cbc", 30, "test")
    b = ws.submit_run(record.id, "pulp_cbc", 30, "test")
    assert a.id == b.id or a.status == "done"
    wait(ws)


def test_late_completion_does_not_overwrite_newer_result():
    ws, record, wood = _fixture_workspace()
    old = ws.submit_run(record.id, "pulp_cbc", 30, "test")
    ws.set_rhs(record.id, wood, 300)
    new = ws.submit_run(record.id, "pulp_cbc", 30, "test")
    wait(ws)
    current = ws.current_run(record.id)
    assert current.id == new.id and old.id != new.id
    assert current.result["objective"] == pytest.approx(2100)


def test_variable_rename_updates_references_and_delete_keeps_model_valid():
    ws, record, _ = _fixture_workspace()
    chairs = next(v.uid for v in record.working.variables if v.name == "chairs")
    ws.rename_variable(record.id, chairs, "stools")
    assert "stools" in record.working.objective.expression.coefficients
    assert all("chairs" not in c.expression.coefficients for c in record.working.constraints)
    impact = ws.variable_impact(record.id, chairs)
    assert impact
    ws.remove_variable(record.id, chairs)
    record.working.validate()
    result = solve_spec(record.working, "pulp_cbc", 30)
    assert result["kind"] == "optimal"


def test_invalid_edits_are_rejected():
    ws, record, wood = _fixture_workspace()
    with pytest.raises(EditError):
        ws.set_rhs(record.id, wood, "abc")


# ---------------------------------------------------------------------------
#  Uploads: every accepted extension, limits, failures
# ---------------------------------------------------------------------------

def _xlsx() -> bytes:
    from openpyxl import Workbook

    wb = Workbook()
    ws = wb.active
    ws.append(["product", "profit", "wood"])
    ws.append(["chairs", 45, 5])
    ws.append(["tables", 80, 20])
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def _docx(text: str) -> bytes:
    import docx

    document = docx.Document()
    for line in text.strip().splitlines():
        document.add_paragraph(line)
    buf = io.BytesIO()
    document.save(buf)
    return buf.getvalue()


def _pdf(text: str) -> bytes:
    import fitz

    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), text, fontsize=11)
    return doc.tobytes()


@pytest.mark.parametrize("filename,maker,kind", [
    ("plan.xlsx", _xlsx, "document"),
    ("plan.csv", lambda: b"product,profit,wood\nchairs,45,5\ntables,80,20\n", "document"),
    ("model.docx", lambda: _docx(FIXTURE_AMPL), "model"),
    ("model.txt", lambda: FIXTURE_AMPL.encode(), "model"),
    ("notes.txt", lambda: b"We make chairs and tables and want the most profit.", "document"),
    ("brief.pdf", lambda: _pdf("Maximise profit from chairs and tables."), "document"),
    ("fixture.mps", lambda: (FIXTURES / "fixture.mps").read_bytes(), "model"),
    ("fixture.mps.gz", lambda: gzip.compress((FIXTURES / "fixture.mps").read_bytes()), "model"),
    ("textract_raw_text.doc", lambda: (FIXTURES / "textract_raw_text.doc").read_bytes(), "document"),
    ("textract_raw_text.xls", lambda: (FIXTURES / "textract_raw_text.xls").read_bytes(), "document"),
])
def test_upload_each_extension(filename, maker, kind):
    outcome = import_upload(filename, maker())
    assert outcome.ok, outcome.message
    assert outcome.kind == kind
    if kind == "model":
        result = solve_spec(outcome.spec, "pulp_cbc", 30)
        assert result["objective"] == pytest.approx(2200)
    else:
        assert outcome.text.strip()


@pytest.mark.parametrize("filename,data,needle", [
    ("corrupt.mps.gz", (FIXTURES / "corrupt.mps.gz").read_bytes(), "gzip"),
    ("empty.txt", b"", "empty"),
    ("archive.gz", gzip.compress(b"x"), ".mps.gz"),
    ("huge.txt", b"x" * (MAX_UPLOAD_BYTES + 1), "larger"),
])
def test_upload_failures_are_reported(filename, data, needle):
    outcome = import_upload(filename, data)
    assert not outcome.ok and outcome.kind == "error"
    assert needle in outcome.message


def test_decompression_limit():
    from src.ingestion.mps_reader import MPSError, decompress_limited

    with pytest.raises(MPSError):
        decompress_limited(gzip.compress(b"0" * 5000), limit=1000)


# ---------------------------------------------------------------------------
#  Exports and MIPLIB name validation
# ---------------------------------------------------------------------------

def test_exports_round_trip_through_ampl():
    spec = spec_of(FIXTURE_AMPL)
    again = spec_of(exporters.spec_to_ampl(spec))
    assert solve_spec(again, "pulp_cbc", 30)["objective"] == pytest.approx(2200)
    lp = exporters.spec_to_lp(spec)
    assert lp.lower().startswith("\\") or "maximize" in lp.lower()
    result = solve_spec(spec, "pulp_cbc", 30)
    assert "chairs" in exporters.variables_csv(result, spec)
    assert '"objective"' in exporters.result_json(result, spec, {"solver": "pulp_cbc"})


@pytest.mark.parametrize("bad", ["../etc/passwd", "a b", "", "x" * 200])
def test_miplib_rejects_unsafe_names(bad):
    from src.services import miplib_service

    with pytest.raises(miplib_service.MiplibError):
        miplib_service.validate_name(bad)


@pytest.mark.network
def test_miplib_flugpl_download_and_solve():
    from src.services import miplib_service

    miplib_service.download("flugpl")
    spec = miplib_service.load_spec("flugpl")
    result = solve_spec(spec, "auto", 60)
    assert result["kind"] == "optimal"
    assert result["objective"] == pytest.approx(1201500)
