"""Shared entry points used by both Chat and the Model Playground.

* ``parse_structured`` — deterministic OR-Learn / AMPL-style parsing.
* ``import_upload`` — validated file import (never replaces the active model on failure).
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from src.modeling.format_detect import FORMAT_LABELS, detect_format
from src.modeling.model_spec import ModelSpec, ModelValidationError

MAX_UPLOAD_BYTES = 25 * 1024 * 1024
UPLOAD_TYPES = ["xlsx", "xls", "csv", "docx", "doc", "txt", "pdf", "mps", "gz"]
UPLOAD_LABEL = ".xlsx .xls .csv .docx .doc .txt .pdf .mps .mps.gz"


@dataclass
class ParseOutcome:
    ok: bool
    format: str
    spec: Optional[ModelSpec] = None
    message: str = ""
    line: Optional[int] = None
    column: Optional[int] = None
    notes: List[str] = field(default_factory=list)
    orlearn: Optional[Dict[str, Any]] = None
    ampl: Optional[Dict[str, Any]] = None
    source_hash: str = ""
    library_only: bool = False


def source_hash(text: str, fmt: str) -> str:
    return hashlib.sha1(f"{fmt}\n{text}".encode("utf-8")).hexdigest()[:12]


def parse_structured(text: str, fmt: str) -> ParseOutcome:
    digest = source_hash(text, fmt)
    if fmt == "orlearn":
        from src.modeling.orlearn_adapter import ORLearnUnavailable, build_from_plan
        from src.modeling.orlearn_parser import ORLearnParseError, parse_orlearn_plan

        try:
            plan = parse_orlearn_plan(text)
            outcome = build_from_plan(plan)
        except ORLearnParseError as exc:
            return ParseOutcome(False, fmt, message=exc.detail, line=exc.line, column=exc.column, source_hash=digest)
        except ORLearnUnavailable as exc:
            return ParseOutcome(False, fmt, message=str(exc), source_hash=digest)
        except ModelValidationError as exc:
            return ParseOutcome(False, fmt, message=str(exc), source_hash=digest)
        info = {
            "kind": outcome.kind, "invoked": outcome.invoked, "library": outcome.library,
            "plan": plan, "unsupported_reason": outcome.unsupported_reason, "chain": plan.render_chain(),
        }
        if outcome.spec is None:
            return ParseOutcome(True, fmt, None, notes=outcome.notes, orlearn=info, source_hash=digest, library_only=True,
                                message=outcome.unsupported_reason)
        return ParseOutcome(True, fmt, outcome.spec, notes=outcome.notes, orlearn=info, source_hash=digest)
    if fmt == "ampl":
        from src.modeling.ampl_parser import AmplParseError, parse_ampl_detailed

        try:
            result = parse_ampl_detailed(text)
        except AmplParseError as exc:
            return ParseOutcome(False, fmt, message=exc.detail, line=exc.line, column=exc.column, source_hash=digest)
        except ModelValidationError as exc:
            return ParseOutcome(False, fmt, message=str(exc), source_hash=digest)
        info = {"sets": result.sets, "params": result.params, "indexed": result.indexed_variables}
        return ParseOutcome(True, fmt, result.spec, notes=result.notes, ampl=info, source_hash=digest)
    return ParseOutcome(False, fmt, message=f"'{fmt}' is not a structured format.", source_hash=digest)


@dataclass
class ImportOutcome:
    ok: bool
    filename: str
    size: int
    kind: str  # "model" | "document" | "error"
    spec: Optional[ModelSpec] = None
    text: str = ""
    preview: Optional[Dict[str, Any]] = None
    message: str = ""
    detected: str = ""
    parse: Optional[ParseOutcome] = None


def import_upload(filename: str, data: bytes) -> ImportOutcome:
    size = len(data)
    lower = filename.lower()
    if size == 0:
        return ImportOutcome(False, filename, size, "error", message="The file is empty.")
    if size > MAX_UPLOAD_BYTES:
        return ImportOutcome(False, filename, size, "error", message=f"The file is larger than {MAX_UPLOAD_BYTES // (1024 * 1024)} MB.")
    if lower.endswith(".gz") and not lower.endswith(".mps.gz"):
        return ImportOutcome(False, filename, size, "error", message="Only .mps.gz archives are supported.")
    if lower.endswith((".mps", ".mps.gz")):
        from src.ingestion.mps_reader import MPSError, read_mps_bytes

        try:
            spec = read_mps_bytes(data, filename=filename, name_hint=filename.rsplit(".mps", 1)[0])
            spec.validate()
        except (MPSError, ModelValidationError, OSError, EOFError) as exc:
            return ImportOutcome(False, filename, size, "error", message=f"Could not read the MPS file: {exc}")
        return ImportOutcome(True, filename, size, "model", spec=spec, message="MPS model imported.", detected="mps")

    from src.ingestion.file_parser import FileParser

    parsed = FileParser().parse(data, filename=filename)
    if parsed.get("type") == "error":
        return ImportOutcome(False, filename, size, "error", message=parsed.get("error", "Unreadable file."))
    text = parsed.get("raw_text", "") or ""
    preview: Dict[str, Any] = {"type": parsed.get("type")}
    if parsed.get("type") in ("excel", "csv"):
        preview["sheets"] = [
            {"name": s["name"], "headers": s.get("headers", []), "rows": s.get("rows", [])[:50], "row_count": len(s.get("rows", []))}
            for s in parsed.get("sheets", [])
        ]
    elif parsed.get("type") == "pdf":
        preview["pages"] = len(parsed.get("pages", []))
    detection = detect_format(text)
    if detection.format in ("orlearn", "ampl"):
        label = FORMAT_LABELS[detection.format]
        outcome = parse_structured(text, detection.format)
        if outcome.ok and outcome.spec is not None:
            return ImportOutcome(True, filename, size, "model", spec=outcome.spec, text=text, preview=preview,
                                 message=f"Found an {label} model in the file.",
                                 detected=detection.format, parse=outcome)
        return ImportOutcome(True, filename, size, "document", text=text, preview=preview, detected=detection.format,
                             parse=outcome, message=f"The file looks like {label} but did not parse: {outcome.message}")
    return ImportOutcome(True, filename, size, "document", text=text, preview=preview, detected=detection.format,
                         message="Text and data extracted. Turning a description into a model needs an AI provider, or rewrite it in AMPL-style syntax.")
