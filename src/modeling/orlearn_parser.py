"""Safe reader for OR-Learn fluent-API snippets.

The pasted text is parsed with :mod:`ast` and checked against an allowlist.
Nothing is executed: the result is a *call plan* (method names plus literal
arguments) that :mod:`src.modeling.orlearn_adapter` replays against the real
OR-Learn library.

Accepted shape (matches the upstream README examples verbatim)::

    from orlearn import OR            # imports of orlearn names only
    costs = [[9, 2], [6, 4]]          # literal assignments
    result = (OR()                    # exactly one model chain
        .maximize([45, 80], names=['chairs', 'tables'])
        .subject_to([5, 20], "<=", 400, "Wood")
        .solve())
    print(result)                     # display statements are skipped
    result.visualize()
"""

from __future__ import annotations

import ast
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from .model_spec import ModelSpec


class ORLearnParseError(ValueError):
    """Raised when input is not in the supported OR-Learn subset."""

    def __init__(self, message: str, line: Optional[int] = None, column: Optional[int] = None):
        self.line = line
        self.column = column
        self.detail = message
        prefix = f"Line {line}: " if line else ""
        super().__init__(prefix + message)


ROOT_FUNCTIONS = {"OR", "lp", "ip", "transport", "assign", "network"}

# method -> (positional parameter names, allowed keyword names)
METHOD_SIGNATURES: Dict[str, Tuple[Tuple[str, ...], Tuple[str, ...]]] = {
    "maximize": (("coefficients", "names"), ("coefficients", "names")),
    "minimize": (("coefficients", "names"), ("coefficients", "names")),
    "subject_to": (("coefficients", "sense", "rhs", "name"), ("coefficients", "sense", "rhs", "name")),
    "st": (("coefficients", "sense", "rhs"), ("coefficients", "sense", "rhs")),
    "as_binary": ((), ()),
    "as_integer": ((), ()),
    "as_continuous": ((), ()),
    "transport": (("supply", "demand"), ("supply", "demand")),
    "costs": (("cost_matrix",), ("cost_matrix",)),
    "assign": (("cost_matrix",), ("cost_matrix", "names")),
    "network": (("edges", "directed"), ("edges", "directed")),
    "shortest_path": (("source", "target"), ("source", "target")),
    "max_flow": (("source", "sink"), ("source", "sink")),
    "mst": ((), ()),
    "solve": (("verbose",), ("verbose",)),
}
ROOT_SIGNATURES: Dict[str, Tuple[Tuple[str, ...], Tuple[str, ...]]] = {
    "OR": ((), ()),
    "lp": ((), ()),
    "ip": ((), ()),
    "transport": (("supply", "demand"), ("supply", "demand")),
    "assign": (("cost_matrix",), ("cost_matrix", "names")),
    "network": (("edges", "directed"), ("edges", "directed")),
}
TERMINAL_METHODS = {"solve", "shortest_path", "max_flow", "mst", "assign"}
DISPLAY_METHODS = {"show", "visualize", "visualize_animated"}


@dataclass
class ORLearnCall:
    method: str
    kwargs: Dict[str, Any]
    line: int

    def render(self) -> str:
        parts = [f"{k}={v!r}" for k, v in self.kwargs.items()]
        return f"{self.method}({', '.join(parts)})"


@dataclass
class ORLearnPlan:
    root: ORLearnCall
    calls: List[ORLearnCall]
    result_name: Optional[str]
    constants: Dict[str, Any] = field(default_factory=dict)
    skipped: List[str] = field(default_factory=list)
    text: str = ""

    @property
    def all_calls(self) -> List[ORLearnCall]:
        return [self.root, *self.calls]

    def render_chain(self) -> str:
        head = self.root.render()
        if self.root.method != "OR":
            head = f"orlearn.{head}"
        else:
            head = "orlearn.OR()"
        return head + "".join(f"\n    .{call.render()}" for call in self.calls)


def looks_like_orlearn(text: str) -> bool:
    lowered = text.lower()
    return (
        "from orlearn" in lowered
        or "import orlearn" in lowered
        or "or()" in lowered.replace(" ", "")
        or ".subject_to(" in lowered
        or "assign(" in lowered and "[" in lowered
    )


def parse_orlearn_plan(text: str) -> ORLearnPlan:
    if not text.strip():
        raise ORLearnParseError("The editor is empty. Paste an OR-Learn example or load one.")
    try:
        tree = ast.parse(text)
    except SyntaxError as exc:
        raise ORLearnParseError(f"Python syntax error: {exc.msg}.", exc.lineno, exc.offset) from exc

    constants: Dict[str, Any] = {}
    plan: Optional[ORLearnPlan] = None
    skipped: List[str] = []

    for node in tree.body:
        line = getattr(node, "lineno", None)
        if isinstance(node, ast.ImportFrom):
            if node.module is None or not node.module.split(".")[0] == "orlearn":
                raise ORLearnParseError(f"Only imports from 'orlearn' are allowed (found '{node.module}').", line)
            continue
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.split(".")[0] != "orlearn":
                    raise ORLearnParseError(f"Only 'import orlearn' is allowed (found '{alias.name}').", line)
            continue

        value: Optional[ast.AST] = None
        target: Optional[str] = None
        if isinstance(node, ast.Assign):
            if len(node.targets) != 1 or not isinstance(node.targets[0], ast.Name):
                raise ORLearnParseError("Only simple assignments like 'result = ...' are allowed.", line)
            target = node.targets[0].id
            value = node.value
        elif isinstance(node, ast.Expr):
            value = node.value
        else:
            raise ORLearnParseError(
                f"'{type(node).__name__}' statements are not allowed. Use one OR() chain with literal data.", line
            )

        if _is_display_statement(value, plan.result_name if plan else None):
            skipped.append(ast.get_source_segment(text, node) or f"line {line}")
            continue

        if target is not None and plan is None and not _is_chain(value):
            try:
                constants[target] = ast.literal_eval(value)
            except (ValueError, TypeError, SyntaxError) as exc:
                raise ORLearnParseError(
                    f"'{target} = ...' must be a literal (numbers, strings, lists).", line
                ) from exc
            continue

        if not _is_chain(value):
            raise ORLearnParseError(
                "Unsupported Python. Only imports, literal assignments, one OR() chain, and print()/visualize() are accepted.",
                line,
            )
        if plan is not None:
            raise ORLearnParseError("Provide one OR-Learn model chain at a time.", line)
        root, calls = _unroll(value, constants)
        plan = ORLearnPlan(root=root, calls=calls, result_name=target, constants=constants, text=text)

    if plan is None:
        raise ORLearnParseError("No OR-Learn chain found. Start with OR().maximize(...) or assign(...).")
    plan.skipped = skipped
    _check_order(plan)
    return plan


def parse_orlearn(text: str) -> ModelSpec:
    """Parse and build the canonical model through the real OR-Learn library."""
    from .orlearn_adapter import build_from_plan

    plan = parse_orlearn_plan(text)
    outcome = build_from_plan(plan)
    if outcome.spec is None:
        raise ORLearnParseError(outcome.unsupported_reason or "This OR-Learn problem has no linear model.")
    return outcome.spec


# ---------------------------------------------------------------------------
#  helpers
# ---------------------------------------------------------------------------

def _is_chain(node: Optional[ast.AST]) -> bool:
    current = node
    while isinstance(current, ast.Call):
        if isinstance(current.func, ast.Name):
            return current.func.id in ROOT_FUNCTIONS
        if isinstance(current.func, ast.Attribute):
            if isinstance(current.func.value, ast.Name) and current.func.value.id == "orlearn":
                return current.func.attr in ROOT_FUNCTIONS
            current = current.func.value
            continue
        return False
    return False


FORMATTING_FUNCTIONS = {"round", "len", "str", "int", "float", "abs", "sum", "min", "max", "sorted", "list"}
STRING_METHODS = {"join", "format", "upper", "lower", "strip"}


def _is_formatting_call(node: ast.Call) -> bool:
    func = node.func
    if isinstance(func, ast.Name):
        return func.id in FORMATTING_FUNCTIONS
    return (
        isinstance(func, ast.Attribute)
        and func.attr in STRING_METHODS
        and isinstance(func.value, ast.Constant)
        and isinstance(func.value.value, str)
    )


def _is_display_statement(node: Optional[ast.AST], result_name: Optional[str]) -> bool:
    if not isinstance(node, ast.Call):
        return False
    func = node.func
    if isinstance(func, ast.Name) and func.id == "print":
        for inner in ast.walk(node):
            if inner is node or not isinstance(inner, ast.Call):
                continue
            if not (_is_display_statement(inner, result_name) or _is_formatting_call(inner)):
                raise ORLearnParseError(
                    "print(...) may only show values or result methods; it cannot call other functions.",
                    getattr(inner, "lineno", None),
                )
        return True
    if (
        result_name
        and isinstance(func, ast.Attribute)
        and func.attr in DISPLAY_METHODS
        and isinstance(func.value, ast.Name)
        and func.value.id == result_name
    ):
        return True
    return False


def _unroll(node: ast.AST, constants: Dict[str, Any]) -> Tuple[ORLearnCall, List[ORLearnCall]]:
    chain: List[ast.Call] = []
    current = node
    while isinstance(current, ast.Call) and isinstance(current.func, ast.Attribute):
        if isinstance(current.func.value, ast.Name) and current.func.value.id == "orlearn":
            break
        chain.append(current)
        current = current.func.value
    if not isinstance(current, ast.Call):
        raise ORLearnParseError("The chain must begin with OR() or an orlearn function.", getattr(node, "lineno", None))
    root_name = current.func.id if isinstance(current.func, ast.Name) else current.func.attr
    if root_name not in ROOT_SIGNATURES:
        raise ORLearnParseError(f"'{root_name}()' is not a supported OR-Learn entry point.", current.lineno)
    root = _call(root_name, current, ROOT_SIGNATURES[root_name], constants)
    calls: List[ORLearnCall] = []
    for call in reversed(chain):
        method = call.func.attr
        if method in DISPLAY_METHODS:
            raise ORLearnParseError(
                f".{method}() inside the chain is not run; call it on the result instead.", call.lineno
            )
        if method not in METHOD_SIGNATURES:
            raise ORLearnParseError(f"Method '.{method}()' is not part of the supported OR-Learn API.", call.lineno)
        calls.append(_call(method, call, METHOD_SIGNATURES[method], constants))
    return root, calls


def _call(method: str, node: ast.Call, signature, constants: Dict[str, Any]) -> ORLearnCall:
    positional, allowed = signature
    kwargs: Dict[str, Any] = {}
    if len(node.args) > len(positional):
        raise ORLearnParseError(f".{method}() takes at most {len(positional)} positional argument(s).", node.lineno)
    for name, arg in zip(positional, node.args):
        kwargs[name] = _literal(arg, constants, method)
    for keyword in node.keywords:
        if keyword.arg is None:
            raise ORLearnParseError("'**kwargs' expansion is not allowed.", node.lineno)
        if keyword.arg not in allowed:
            raise ORLearnParseError(f".{method}() does not accept '{keyword.arg}='.", node.lineno)
        if keyword.arg in kwargs:
            raise ORLearnParseError(f".{method}() got '{keyword.arg}' twice.", node.lineno)
        kwargs[keyword.arg] = _literal(keyword.value, constants, method)
    return ORLearnCall(method, kwargs, node.lineno)


def _literal(node: ast.AST, constants: Dict[str, Any], method: str) -> Any:
    if isinstance(node, ast.Name):
        if node.id in constants:
            return constants[node.id]
        if node.id in ("True", "False", "None"):
            return {"True": True, "False": False, "None": None}[node.id]
        raise ORLearnParseError(f"'{node.id}' is not defined (only literal values are allowed).", node.lineno)
    try:
        return ast.literal_eval(node)
    except (ValueError, TypeError, SyntaxError) as exc:
        raise ORLearnParseError(
            f"Arguments to .{method}() must be literal numbers, strings, or lists.", getattr(node, "lineno", None)
        ) from exc


def _check_order(plan: ORLearnPlan) -> None:
    names = [c.method for c in plan.calls]
    for index, call in enumerate(plan.calls[:-1]):
        if call.method in TERMINAL_METHODS:
            raise ORLearnParseError(f".{call.method}() must be the last call in the chain.", call.line)
    root = plan.root.method
    if root in ("OR", "lp", "ip"):
        uses_lp = any(n in ("maximize", "minimize") for n in names)
        uses_tp = "transport" in names
        uses_net = "network" in names
        if not (uses_lp or uses_tp or uses_net or "assign" in names):
            raise ORLearnParseError("Call .maximize(...) or .minimize(...) to define the objective.", plan.root.line)
        if uses_lp and sum(n in ("maximize", "minimize") for n in names) > 1:
            raise ORLearnParseError("Only one objective is supported.", plan.root.line)
