"""Canonical, deterministic representation of a linear optimization model.

Every structured entry point (OR-Learn, AMPL-style, templates, MPS/MIPLIB,
the Live Editor and AI-generated PuLP models) is normalised into a
``ModelSpec``.  Instances are treated as immutable values: edits always build
a new spec with ``dataclasses.replace`` so earlier revisions stay intact.
"""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import asdict, dataclass, field, replace
from typing import Dict, Iterable, List, Literal, Optional

VariableType = Literal["continuous", "integer", "binary"]
ObjectiveSense = Literal["maximize", "minimize"]
ConstraintSense = Literal["<=", ">=", "="]

VARIABLE_TYPES = ("continuous", "integer", "binary")
CONSTRAINT_SENSES = ("<=", ">=", "=")


class ModelValidationError(ValueError):
    """Raised when a model is syntactically valid but mathematically incomplete."""

    def __init__(self, message: str, issues: Optional[List[dict]] = None):
        super().__init__(message)
        self.issues = issues or []


@dataclass(frozen=True)
class VariableSpec:
    name: str
    variable_type: VariableType = "continuous"
    lower_bound: Optional[float] = 0.0
    upper_bound: Optional[float] = None
    uid: str = ""


@dataclass(frozen=True)
class LinearExpression:
    coefficients: Dict[str, float] = field(default_factory=dict)
    constant: float = 0.0

    def minus(self, other: "LinearExpression") -> "LinearExpression":
        coefficients = dict(self.coefficients)
        for name, value in other.coefficients.items():
            coefficients[name] = coefficients.get(name, 0.0) - value
        return LinearExpression(
            coefficients={k: v for k, v in coefficients.items() if abs(v) > 1e-12},
            constant=self.constant - other.constant,
        )

    def plus(self, other: "LinearExpression") -> "LinearExpression":
        return self.minus(other.scaled(-1.0))

    def scaled(self, factor: float) -> "LinearExpression":
        return LinearExpression(
            {k: v * factor for k, v in self.coefficients.items()},
            self.constant * factor,
        )

    def renamed(self, old: str, new: str) -> "LinearExpression":
        if old not in self.coefficients:
            return self
        return LinearExpression(
            {(new if k == old else k): v for k, v in self.coefficients.items()},
            self.constant,
        )

    def without(self, name: str) -> "LinearExpression":
        if name not in self.coefficients:
            return self
        return LinearExpression(
            {k: v for k, v in self.coefficients.items() if k != name}, self.constant
        )


@dataclass(frozen=True)
class ObjectiveSpec:
    sense: ObjectiveSense
    expression: LinearExpression
    name: str = "objective"


@dataclass(frozen=True)
class ConstraintSpec:
    name: str
    expression: LinearExpression
    sense: ConstraintSense
    rhs: float
    source: str = ""
    uid: str = ""


@dataclass
class ModelSpec:
    name: str
    variables: List[VariableSpec]
    objective: ObjectiveSpec
    constraints: List[ConstraintSpec]
    source_syntax: str
    source_text: str = ""
    metadata: Dict[str, str] = field(default_factory=dict)

    # ------------------------------------------------------------------
    #  Validation
    # ------------------------------------------------------------------
    def issues(self) -> List[dict]:
        """Return structured validation issues (empty list when valid)."""
        issues: List[dict] = []
        names = [variable.name for variable in self.variables]

        def add(target: str, message: str, uid: str = "") -> None:
            issues.append({"target": target, "uid": uid, "message": message})

        if not names:
            add("variables", "Define at least one decision variable.")
        seen: Dict[str, int] = {}
        for variable in self.variables:
            seen[variable.name] = seen.get(variable.name, 0) + 1
        for duplicate in sorted(n for n, c in seen.items() if c > 1):
            add("variables", f"Variable name '{duplicate}' is used more than once.")

        known = set(names)
        unknown = sorted(set(self.objective.expression.coefficients) - known)
        if unknown:
            add("objective", f"Objective references undeclared variables: {', '.join(unknown)}.")
        for constraint in self.constraints:
            missing = sorted(set(constraint.expression.coefficients) - known)
            if missing:
                add(
                    "constraint",
                    f"Constraint '{constraint.name}' references undeclared variables: "
                    f"{', '.join(missing)}.",
                    constraint.uid,
                )
            if not constraint.expression.coefficients:
                add(
                    "constraint",
                    f"Constraint '{constraint.name}' has no variables left.",
                    constraint.uid,
                )
            if constraint.sense not in CONSTRAINT_SENSES:
                add("constraint", f"Constraint '{constraint.name}' has an unknown relation.", constraint.uid)
            if not _finite(constraint.rhs):
                add("constraint", f"Constraint '{constraint.name}' needs a finite right-hand side.", constraint.uid)

        cnames: Dict[str, int] = {}
        for constraint in self.constraints:
            cnames[constraint.name] = cnames.get(constraint.name, 0) + 1
        for duplicate in sorted(n for n, c in cnames.items() if c > 1):
            add("constraint", f"Constraint name '{duplicate}' is used more than once.")

        for variable in self.variables:
            if not variable.name or any(ch.isspace() for ch in variable.name):
                add("variable", f"Variable '{variable.name}' needs a name without spaces.", variable.uid)
            if variable.variable_type not in VARIABLE_TYPES:
                add("variable", f"Variable '{variable.name}' has an unknown domain.", variable.uid)
            lo, hi = variable.lower_bound, variable.upper_bound
            if lo is not None and hi is not None and lo > hi:
                add("variable", f"Variable '{variable.name}' has a lower bound above its upper bound.", variable.uid)
            if variable.variable_type == "binary" and (
                (lo is not None and lo < 0) or (hi is not None and hi > 1)
            ):
                add("variable", f"Binary variable '{variable.name}' must stay within [0, 1].", variable.uid)

        if not self.objective.expression.coefficients:
            add("objective", "The objective must reference at least one decision variable.")
        if not self.constraints:
            add("constraints", "Define at least one constraint.")
        return issues

    def validate(self) -> "ModelSpec":
        issues = self.issues()
        if issues:
            raise ModelValidationError("\n".join(i["message"] for i in issues), issues)
        return self

    # ------------------------------------------------------------------
    #  Helpers
    # ------------------------------------------------------------------
    def variable_map(self) -> Dict[str, VariableSpec]:
        return {variable.name: variable for variable in self.variables}

    def constraint_by_uid(self, uid: str) -> Optional[ConstraintSpec]:
        return next((c for c in self.constraints if c.uid == uid), None)

    def variable_by_uid(self, uid: str) -> Optional[VariableSpec]:
        return next((v for v in self.variables if v.uid == uid), None)

    def with_uids(self) -> "ModelSpec":
        """Assign stable row ids to rows that do not have one yet."""
        used = {v.uid for v in self.variables if v.uid} | {c.uid for c in self.constraints if c.uid}
        counters: Dict[str, int] = {}

        def fresh(prefix: str) -> str:
            while True:
                counters[prefix] = counters.get(prefix, 0) + 1
                candidate = f"{prefix}{counters[prefix]}"
                if candidate not in used:
                    used.add(candidate)
                    return candidate

        variables = [v if v.uid else replace(v, uid=fresh("v")) for v in self.variables]
        constraints = [c if c.uid else replace(c, uid=fresh("c")) for c in self.constraints]
        return replace(self, variables=variables, constraints=constraints)

    def new_uid(self, prefix: str) -> str:
        used = {v.uid for v in self.variables} | {c.uid for c in self.constraints}
        index = len(used) + 1
        while f"{prefix}{index}" in used:
            index += 1
        return f"{prefix}{index}"

    def stats(self) -> Dict[str, int]:
        counts = {"continuous": 0, "integer": 0, "binary": 0}
        for variable in self.variables:
            counts[variable.variable_type] = counts.get(variable.variable_type, 0) + 1
        nonzeros = sum(len(c.expression.coefficients) for c in self.constraints)
        return {
            "variables": len(self.variables),
            "constraints": len(self.constraints),
            "nonzeros": nonzeros,
            **counts,
        }

    @property
    def is_mip(self) -> bool:
        return any(v.variable_type != "continuous" for v in self.variables)

    def problem_class(self) -> str:
        if not self.is_mip:
            return "LP"
        if all(v.variable_type != "continuous" for v in self.variables):
            return "IP"
        return "MIP"

    def fingerprint(self) -> str:
        """Content hash used to identify an exact model revision."""
        payload = {
            "sense": self.objective.sense,
            "objective": sorted(self.objective.expression.coefficients.items()),
            "objective_constant": self.objective.expression.constant,
            "variables": [
                (v.name, v.variable_type, v.lower_bound, v.upper_bound) for v in self.variables
            ],
            "constraints": [
                (c.name, sorted(c.expression.coefficients.items()), c.expression.constant, c.sense, c.rhs)
                for c in self.constraints
            ],
        }
        raw = json.dumps(payload, sort_keys=True, default=str).encode("utf-8")
        return hashlib.sha1(raw).hexdigest()[:12]

    def to_dict(self) -> Dict[str, object]:
        return asdict(self)


def _finite(value: object) -> bool:
    try:
        return math.isfinite(float(value))
    except (TypeError, ValueError):
        return False


def infer_variables(expressions: Iterable[LinearExpression]) -> List[str]:
    """Return variable names in first-seen order."""
    seen: Dict[str, None] = {}
    for expression in expressions:
        for name in expression.coefficients:
            seen.setdefault(name, None)
    return list(seen)
