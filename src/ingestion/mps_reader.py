"""MPS reader that produces a canonical ``ModelSpec``.

Handles fixed and free MPS as used by MIPLIB: OBJSENSE (section or inline),
integer MARKER blocks, RHS on the objective row (objective constant), RANGES,
and all common BOUNDS types (UP, LO, FX, FR, MI, PL, BV, LI, UI, SC rejected).
"""

from __future__ import annotations

import gzip
import io
import math
import re
import zlib
from typing import Dict, List, Optional, Tuple

from src.modeling.model_spec import ConstraintSpec, LinearExpression, ModelSpec, ObjectiveSpec, VariableSpec

MAX_COMPRESSED_BYTES = 50 * 1024 * 1024
MAX_DECOMPRESSED_BYTES = 400 * 1024 * 1024


class MPSError(ValueError):
    def __init__(self, message: str, line: Optional[int] = None):
        self.line = line
        super().__init__(f"Line {line}: {message}" if line else message)


def decompress_limited(data: bytes, limit: int = MAX_DECOMPRESSED_BYTES) -> bytes:
    """Decompress gzip data, refusing anything larger than ``limit`` bytes."""
    out = io.BytesIO()
    try:
        with gzip.GzipFile(fileobj=io.BytesIO(data)) as handle:
            while True:
                chunk = handle.read(1 << 20)
                if not chunk:
                    break
                out.write(chunk)
                if out.tell() > limit:
                    raise MPSError(
                        f"The decompressed file exceeds the {limit // (1024 * 1024)} MB limit."
                    )
    except (OSError, EOFError, zlib.error) as exc:
        raise MPSError(f"The file is not a valid gzip archive ({exc}).") from exc
    return out.getvalue()


def read_mps_bytes(data: bytes, filename: str = "", name_hint: str = "") -> ModelSpec:
    if filename.lower().endswith(".gz") or data[:2] == b"\x1f\x8b":
        data = decompress_limited(data)
    text = data.decode("utf-8", errors="replace")
    return read_mps_text(text, name_hint or filename)


def read_mps_text(text: str, name_hint: str = "") -> ModelSpec:
    section = ""
    problem_name = ""
    sense = "minimize"
    comment_sense: Optional[str] = None
    explicit_sense = False
    objective_row: Optional[str] = None
    row_types: Dict[str, str] = {}
    row_order: List[str] = []
    columns: Dict[str, Dict[str, float]] = {}
    column_order: List[str] = []
    integer_columns: set = set()
    rhs: Dict[str, float] = {}
    ranges: Dict[str, float] = {}
    bounds: Dict[str, List[Optional[float]]] = {}
    binaries: set = set()
    in_marker = False
    free_obj_rows: List[str] = []

    for lineno, raw in enumerate(text.splitlines(), 1):
        if not raw.strip():
            continue
        if raw.startswith("*"):
            # PuLP's writeMPS records a maximize objective only as "*SENSE:Maximize".
            match = re.match(r"\*\s*SENSE\s*:\s*(\w+)", raw, re.IGNORECASE)
            if match:
                try:
                    comment_sense = _sense(match.group(1), lineno)
                except MPSError:
                    comment_sense = None
            continue
        fields = raw.split()
        if not raw[0].isspace():
            head = fields[0].upper()
            if head == "NAME":
                section = "NAME"
                problem_name = fields[1] if len(fields) > 1 else ""
                continue
            if head == "OBJSENSE":
                section = "OBJSENSE"
                if len(fields) > 1:
                    sense = _sense(fields[1], lineno)
                    explicit_sense = True
                    section = ""
                continue
            if head == "OBJSENSE" or head == "OBJSENCE":
                section = "OBJSENSE"
                continue
            if head in ("ROWS", "COLUMNS", "RHS", "RANGES", "BOUNDS", "ENDATA", "OBJNAME"):
                section = head
                if head == "ENDATA":
                    break
                continue
            if head in ("QUADOBJ", "QMATRIX", "QSECTION", "QCMATRIX", "CSECTION", "SOS", "INDICATORS"):
                raise MPSError(f"Section '{head}' (quadratic/conic/SOS) is not supported; only linear models.", lineno)
            raise MPSError(f"Unknown section '{fields[0]}'.", lineno)

        if section == "OBJSENSE":
            sense = _sense(fields[0], lineno)
            explicit_sense = True
        elif section == "OBJNAME":
            objective_row = fields[0]
        elif section == "ROWS":
            if len(fields) < 2:
                raise MPSError("ROWS entries need a type and a name.", lineno)
            kind, name = fields[0].upper(), fields[1]
            if kind not in ("N", "L", "G", "E"):
                raise MPSError(f"Unknown row type '{kind}'.", lineno)
            if name in row_types:
                raise MPSError(f"Row '{name}' is defined twice.", lineno)
            row_types[name] = kind
            if kind == "N":
                if objective_row is None:
                    objective_row = name
                else:
                    free_obj_rows.append(name)
            else:
                row_order.append(name)
        elif section == "COLUMNS":
            if len(fields) >= 3 and fields[1].upper().strip("'\"") == "MARKER":
                tag = fields[2].upper().strip("'\"")
                if tag == "INTORG":
                    in_marker = True
                elif tag == "INTEND":
                    in_marker = False
                continue
            column = fields[0]
            if column not in columns:
                columns[column] = {}
                column_order.append(column)
            if in_marker:
                integer_columns.add(column)
            pairs = fields[1:]
            if len(pairs) % 2:
                raise MPSError(f"Column '{column}' has an incomplete (row, value) pair.", lineno)
            for i in range(0, len(pairs), 2):
                row, value = pairs[i], _float(pairs[i + 1], lineno)
                if row not in row_types:
                    raise MPSError(f"Column '{column}' references unknown row '{row}'.", lineno)
                columns[column][row] = columns[column].get(row, 0.0) + value
        elif section in ("RHS", "RANGES"):
            pairs = fields[1:] if len(fields) % 2 == 1 else fields
            target = rhs if section == "RHS" else ranges
            for i in range(0, len(pairs), 2):
                row, value = pairs[i], _float(pairs[i + 1], lineno)
                if row not in row_types:
                    raise MPSError(f"{section} references unknown row '{row}'.", lineno)
                target[row] = value
        elif section == "BOUNDS":
            kind = fields[0].upper()
            if kind in ("FR", "MI", "PL", "BV"):
                column = fields[2] if len(fields) >= 3 else fields[1]
                value = None
                if kind == "BV" and len(fields) >= 4:
                    value = _float(fields[3], lineno)
            else:
                if len(fields) < 3:
                    raise MPSError(f"Bound '{kind}' needs a value.", lineno)
                column = fields[2] if len(fields) >= 4 else fields[1]
                value = _float(fields[-1], lineno)
            if column not in columns:
                raise MPSError(f"Bound on unknown column '{column}'.", lineno)
            entry = bounds.setdefault(column, [0.0, math.inf])
            if kind == "UP":
                entry[1] = value
                if value < 0 and entry[0] == 0.0:
                    entry[0] = -math.inf
            elif kind == "LO":
                entry[0] = value
            elif kind == "FX":
                entry[0] = entry[1] = value
            elif kind == "FR":
                entry[0], entry[1] = -math.inf, math.inf
            elif kind == "MI":
                entry[0] = -math.inf
            elif kind == "PL":
                entry[1] = math.inf
            elif kind == "BV":
                entry[0], entry[1] = 0.0, 1.0
                binaries.add(column)
            elif kind == "LI":
                entry[0] = value
                integer_columns.add(column)
            elif kind == "UI":
                entry[1] = value
                integer_columns.add(column)
                if value < 0 and entry[0] == 0.0:
                    entry[0] = -math.inf
            elif kind == "SC":
                raise MPSError("Semi-continuous (SC) bounds are not supported.", lineno)
            else:
                raise MPSError(f"Unknown bound type '{kind}'.", lineno)

    if comment_sense and not explicit_sense:
        sense = comment_sense
    if objective_row is None:
        raise MPSError("The file has no objective (N) row.")
    if not columns:
        raise MPSError("The file defines no columns (variables).")

    variables: List[VariableSpec] = []
    for column in column_order:
        lo, hi = bounds.get(column, [0.0, math.inf])
        if column in binaries:
            vtype = "binary"
        elif column in integer_columns:
            vtype = "integer"
            if column not in bounds:
                hi = math.inf
            if lo == 0.0 and hi == 1.0:
                vtype = "binary"
        else:
            vtype = "continuous"
        variables.append(VariableSpec(
            column, vtype,
            None if lo == -math.inf else float(lo),
            None if hi == math.inf else float(hi),
        ))

    rows: Dict[str, Dict[str, float]] = {name: {} for name in row_order}
    objective: Dict[str, float] = {}
    for column in column_order:
        for row, value in columns[column].items():
            if row == objective_row:
                objective[column] = value
            elif row in rows and value != 0.0:
                rows[row][column] = value

    constraints: List[ConstraintSpec] = []
    sense_map = {"L": "<=", "G": ">=", "E": "="}
    for name in row_order:
        kind = row_types[name]
        value = rhs.get(name, 0.0)
        expression = LinearExpression(rows[name])
        if not rows[name]:
            continue
        if name in ranges:
            r = ranges[name]
            if kind == "L":
                lo, hi = value - abs(r), value
            elif kind == "G":
                lo, hi = value, value + abs(r)
            else:
                lo, hi = (value, value + r) if r >= 0 else (value + r, value)
            constraints.append(ConstraintSpec(f"{name}", expression, ">=", lo, "mps:range"))
            constraints.append(ConstraintSpec(f"{name}__ub", expression, "<=", hi, "mps:range"))
        else:
            constraints.append(ConstraintSpec(name, expression, sense_map[kind], value, "mps"))

    constant = -rhs.get(objective_row, 0.0)
    spec = ModelSpec(
        name=problem_name or name_hint or "MPS model",
        variables=variables,
        objective=ObjectiveSpec(sense, LinearExpression(objective, constant), objective_row),
        constraints=constraints,
        source_syntax="mps",
        source_text="",
        metadata={"mps_name": problem_name, "ranges": str(len(ranges)), "extra_n_rows": str(len(free_obj_rows))},
    )
    if not objective:
        # Feasibility problems are valid MPS; keep them solvable with a zero objective.
        first = variables[0].name
        spec = ModelSpec(spec.name, spec.variables, ObjectiveSpec(sense, LinearExpression({first: 0.0}, constant), objective_row),
                         spec.constraints, spec.source_syntax, "", dict(spec.metadata, feasibility="yes"))
    return spec.with_uids()


def _sense(token: str, lineno: int) -> str:
    token = token.upper()
    if token in ("MAX", "MAXIMIZE", "MAXIMISE"):
        return "maximize"
    if token in ("MIN", "MINIMIZE", "MINIMISE"):
        return "minimize"
    raise MPSError(f"Unknown OBJSENSE '{token}'.", lineno)


def _float(token: str, lineno: int) -> float:
    try:
        return float(token)
    except ValueError as exc:
        raise MPSError(f"'{token}' is not a number.", lineno) from exc
