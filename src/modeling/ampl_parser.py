"""Parser for the documented AMPL-style LP/MIP subset.

Supported (see docs/AMPL_SUBSET.md for the full reference):

* ``set NAME := a b c;``  ``set NAME := {a, b};``  ``set T := 1..5;``
* ``param NAME := 3;``  ``param c{P} := chairs 45 tables 80;``
  ``param c{P} := [45, 80];``  ``param a{R,P} := [[5, 20], [10, 15]];``
  ``param a{R,P}: chairs tables := wood 5 20 labor 10 15;``  ``default v``
* ``var x;``  ``var x{P} >= 0, <= u[p], integer;``  (AMPL default bounds are free)
* ``maximize|minimize name: expr;`` with ``sum{i in I, j in J} ...``
* ``subject to|s.t. name{i in I}: expr <=|>=|= expr;`` and ``lo <= expr <= hi``
* ``solve; data; end; display ...; option ...;`` are accepted and ignored.

Everything is parsed with a tokenizer and recursive-descent parser; nothing
is evaluated as Python.  Errors carry the line and column of the offending
construct.
"""

from __future__ import annotations

import itertools
import re
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple, Union

from .model_spec import (
    ConstraintSpec,
    LinearExpression,
    ModelSpec,
    ObjectiveSpec,
    VariableSpec,
)


class AmplParseError(ValueError):
    """Actionable parser error with a source location."""

    def __init__(self, message: str, line: Optional[int] = None, column: Optional[int] = None):
        self.line = line
        self.column = column
        self.detail = message
        location = ""
        if line is not None:
            location = f"Line {line}" + (f", column {column}" if column is not None else "") + ": "
        super().__init__(location + message)


# ---------------------------------------------------------------------------
#  Tokenizer
# ---------------------------------------------------------------------------

_TOKEN_RE = re.compile(
    r"""
    (?P<ws>[ \t\r\f]+)
  | (?P<nl>\n)
  | (?P<comment>\#[^\n]*|//[^\n]*)
  | (?P<number>(?:\d+(?:\.(?!\.)\d*)?|\.\d+)(?:[eE][+-]?\d+)?)
  | (?P<string>'[^'\n]*'|"[^"\n]*")
  | (?P<ident>[A-Za-z_][A-Za-z0-9_]*)
  | (?P<op>:=|<=|>=|==|!=|\.\.|[;:,()\[\]{}+\-*/^=<>.])
  | (?P<bad>.)
    """,
    re.VERBOSE,
)

_UNICODE = {"≤": "<=", "≥": ">=", "−": "-", "×": "*", "·": "*", "∑": "sum"}


@dataclass
class Tok:
    kind: str
    value: str
    line: int
    col: int


def tokenize(text: str) -> List[Tok]:
    for symbol, replacement in _UNICODE.items():
        text = text.replace(symbol, replacement)
    tokens: List[Tok] = []
    line, line_start = 1, 0
    for match in _TOKEN_RE.finditer(text):
        kind = match.lastgroup or "bad"
        value = match.group()
        col = match.start() - line_start + 1
        if kind == "nl":
            line += 1
            line_start = match.end()
            continue
        if kind in ("ws", "comment"):
            continue
        if kind == "bad":
            raise AmplParseError(f"Unexpected character '{value}'.", line, col)
        tokens.append(Tok(kind, value, line, col))
    tokens.append(Tok("eof", "", line, max(1, len(text) - line_start + 1)))
    return tokens


# ---------------------------------------------------------------------------
#  AST
# ---------------------------------------------------------------------------

Member = Union[int, float, str]


@dataclass
class Node:
    line: int
    col: int


@dataclass
class Num(Node):
    value: float


@dataclass
class Ref(Node):
    name: str
    indices: List[Node] = field(default_factory=list)
    subscripted: bool = False


@dataclass
class Lit(Node):
    value: Member


@dataclass
class Bin(Node):
    op: str
    left: Node
    right: Node


@dataclass
class Neg(Node):
    operand: Node


@dataclass
class SetExpr(Node):
    kind: str  # "name" | "range" | "literal"
    name: str = ""
    low: Optional[Node] = None
    high: Optional[Node] = None
    members: List[Node] = field(default_factory=list)


@dataclass
class Indexing(Node):
    items: List[Tuple[Optional[str], SetExpr]]


@dataclass
class Sum(Node):
    indexing: Indexing
    body: Node


@dataclass
class VarDecl(Node):
    name: str
    indexing: Optional[Indexing]
    lower: Optional[Node] = None
    upper: Optional[Node] = None
    fixed: Optional[Node] = None
    domain: str = "continuous"
    free: bool = False


@dataclass
class ObjDecl(Node):
    sense: str
    name: str
    expr: Node


@dataclass
class ConDecl(Node):
    name: str
    indexing: Optional[Indexing]
    parts: List[Node]
    relations: List[str]


@dataclass
class ParamDecl(Node):
    name: str
    index_sets: List[str]
    default: Optional[float] = None


@dataclass
class AmplResult:
    spec: ModelSpec
    sets: Dict[str, List[Member]]
    params: Dict[str, Dict[str, Any]]
    indexed_variables: Dict[str, Dict[str, Any]]
    notes: List[str]


# ---------------------------------------------------------------------------
#  Parser
# ---------------------------------------------------------------------------

_IGNORED_STATEMENTS = {"solve", "data", "model", "end", "reset", "display", "option", "printf", "print", "expand", "show"}
_RELATIONS = ("<=", ">=", "=", "==")


class _Parser:
    def __init__(self, text: str):
        self.tokens = tokenize(text)
        self.pos = 0
        self.sets: Dict[str, Optional[List[Member]]] = {}
        self.set_locs: Dict[str, Tok] = {}
        self.params: Dict[str, ParamDecl] = {}
        self.param_values: Dict[str, Dict[Tuple[Member, ...], float]] = {}
        self.var_decls: List[VarDecl] = []
        self.objective: Optional[ObjDecl] = None
        self.constraints: List[ConDecl] = []
        self.notes: List[str] = []
        self._pending_set_data: Dict[str, Tuple[Tok, List[Node]]] = {}

    # -- token helpers ---------------------------------------------------
    @property
    def tok(self) -> Tok:
        return self.tokens[self.pos]

    def peek(self, offset: int = 1) -> Tok:
        return self.tokens[min(self.pos + offset, len(self.tokens) - 1)]

    def advance(self) -> Tok:
        token = self.tokens[self.pos]
        if token.kind != "eof":
            self.pos += 1
        return token

    def at(self, *values: str) -> bool:
        token = self.tok
        return token.kind in ("op", "ident") and token.value in values

    def at_kw(self, *values: str) -> bool:
        return self.tok.kind == "ident" and self.tok.value.lower() in values

    def expect(self, value: str, context: str = "") -> Tok:
        if self.tok.value != value or self.tok.kind not in ("op", "ident"):
            found = self.tok.value or "end of input"
            hint = f" {context}" if context else ""
            raise AmplParseError(f"Expected '{value}'{hint} but found '{found}'.", self.tok.line, self.tok.col)
        return self.advance()

    def expect_ident(self, what: str) -> Tok:
        if self.tok.kind != "ident":
            found = self.tok.value or "end of input"
            raise AmplParseError(f"Expected {what} but found '{found}'.", self.tok.line, self.tok.col)
        return self.advance()

    def error(self, message: str, token: Optional[Tok] = None) -> AmplParseError:
        token = token or self.tok
        return AmplParseError(message, token.line, token.col)

    # -- statements --------------------------------------------------------
    def parse(self) -> None:
        if self.tok.kind == "eof":
            raise AmplParseError("The editor is empty. Load an example or define a model.", 1, 1)
        while self.tok.kind != "eof":
            if self.at(";"):
                self.advance()
                continue
            self.statement()

    def statement(self) -> None:
        token = self.tok
        if token.kind != "ident":
            raise self.error(f"A statement cannot start with '{token.value}'.")
        keyword = token.value.lower()
        if keyword == "set":
            self.set_statement()
        elif keyword == "param":
            self.param_statement()
        elif keyword == "var":
            self.var_statement()
        elif keyword in ("maximize", "minimize", "max", "min"):
            self.objective_statement()
        elif keyword in ("subject", "subj"):
            self.advance()
            self.expect("to", "after 'subject'")
            self.constraint_body()
        elif keyword == "s" and self.peek().value == ".":
            self.advance()
            self.expect(".")
            if not (self.tok.kind == "ident" and self.tok.value.lower() == "t"):
                raise self.error("Write 's.t.' or 'subject to' before a constraint.")
            self.advance()
            if self.at("."):
                self.advance()
            self.constraint_body()
        elif keyword in _IGNORED_STATEMENTS:
            self.advance()
            depth = 0
            while self.tok.kind != "eof" and not (self.at(";") and depth == 0):
                if self.at("{", "(", "["):
                    depth += 1
                elif self.at("}", ")", "]"):
                    depth -= 1
                self.advance()
            if keyword not in ("solve", "data", "model", "end"):
                self.notes.append(f"Line {token.line}: '{keyword}' statement ignored (display/scripting commands are not executed).")
            if self.at(";"):
                self.advance()
        elif self.peek().value in (":", "{") and keyword not in ("sum",):
            # AMPL allows constraints without the 'subject to' keyword.
            self.constraint_body()
        else:
            raise self.error(
                f"Unsupported statement '{token.value}'. Use set, param, var, "
                "maximize/minimize, subject to, or solve."
            )

    def end_statement(self, what: str) -> None:
        if not self.at(";"):
            found = self.tok.value or "end of input"
            raise self.error(f"Expected ';' to end the {what} but found '{found}'.")
        self.advance()

    # set ---------------------------------------------------------------
    def set_statement(self) -> None:
        self.advance()
        name_tok = self.expect_ident("a set name")
        name = name_tok.value
        if self.at("dimen", "within", "ordered", "circular"):
            raise self.error(f"Set attribute '{self.tok.value}' is not supported.")
        if self.at(";"):
            self.advance()
            self.sets.setdefault(name, None)
            self.set_locs.setdefault(name, name_tok)
            return
        if not (self.at(":=") or self.at("=")):
            raise self.error(f"Expected ':=' with members for set '{name}'.")
        self.advance()
        members = self.set_data(name)
        self.end_statement(f"set '{name}'")
        if name in self.sets and self.sets[name] is not None:
            raise self.error(f"Set '{name}' is defined twice.", name_tok)
        self.sets[name] = members
        self.set_locs.setdefault(name, name_tok)

    def set_data(self, name: str) -> List[Member]:
        if self.at("{"):
            self.advance()
            members: List[Member] = []
            while not self.at("}"):
                if self.tok.kind == "eof":
                    raise self.error(f"Set '{name}' is missing a closing '}}'.")
                members.extend(self.set_member_or_range())
                if self.at(","):
                    self.advance()
            self.advance()
            return _dedupe(members, name)
        members = []
        while not self.at(";"):
            if self.tok.kind == "eof":
                raise self.error(f"Set '{name}' needs a closing ';'.")
            members.extend(self.set_member_or_range())
            if self.at(","):
                self.advance()
        if not members:
            raise self.error(f"Set '{name}' has no members.")
        return _dedupe(members, name)

    def set_member_or_range(self) -> List[Member]:
        first = self.data_member()
        if self.at(".."):
            self.advance()
            last_tok = self.tok
            last = self.data_member()
            if not (isinstance(first, int) and isinstance(last, int)):
                raise self.error("Ranges 'a..b' need integer endpoints.", last_tok)
            if last < first:
                raise self.error("Range end is smaller than its start.", last_tok)
            if last - first > 100000:
                raise self.error("Range is too large (more than 100,000 members).", last_tok)
            return list(range(first, last + 1))
        return [first]

    def data_member(self) -> Member:
        token = self.tok
        negative = False
        if self.at("-"):
            negative = True
            self.advance()
            token = self.tok
        if token.kind == "number":
            self.advance()
            value = float(token.value)
            value = -value if negative else value
            return int(value) if value.is_integer() else value
        if negative:
            raise self.error("Expected a number after '-'.")
        if token.kind == "string":
            self.advance()
            return token.value[1:-1]
        if token.kind == "ident":
            self.advance()
            return token.value
        raise self.error(f"Expected a set member but found '{token.value or 'end of input'}'.")

    # param ---------------------------------------------------------------
    def param_statement(self) -> None:
        self.advance()
        name_tok = self.expect_ident("a parameter name")
        name = name_tok.value
        index_sets: List[str] = []
        if self.at("{"):
            indexing = self.indexing()
            for dummy, set_expr in indexing.items:
                if set_expr.kind != "name":
                    raise self.error("Parameter indexing must use named sets.", name_tok)
                index_sets.append(set_expr.name)
        decl = self.params.get(name)
        if decl is None:
            decl = ParamDecl(name_tok.line, name_tok.col, name, index_sets)
            self.params[name] = decl
            self.param_values[name] = {}
        elif index_sets and decl.index_sets and index_sets != decl.index_sets:
            raise self.error(f"Parameter '{name}' is redeclared with different indexing.", name_tok)
        elif index_sets:
            decl.index_sets = index_sets

        # attributes before data
        while self.at("default", ">=", "<=", "integer", ">", "<", ","):
            if self.at(","):
                self.advance()
                continue
            if self.at("default"):
                self.advance()
                decl.default = self.signed_number("default value")
            elif self.at("integer"):
                self.advance()
            else:
                self.advance()
                self.signed_number("bound")
                self.notes.append(f"Line {name_tok.line}: parameter bound checks on '{name}' are not enforced.")

        if self.at(";"):
            self.advance()
            return
        columns: Optional[List[Member]] = None
        if self.at(":"):
            self.advance()
            columns = []
            while not self.at(":="):
                if self.tok.kind == "eof" or self.at(";"):
                    raise self.error(f"Expected ':=' after the column labels of '{name}'.")
                columns.append(self.data_member())
        if not (self.at(":=") or self.at("=")):
            raise self.error(f"Expected ':=' with data for parameter '{name}'.")
        self.advance()
        values = self.param_values[name]
        if columns is not None:
            self.table_data(decl, columns, values)
        elif self.at("["):
            self.list_data(decl, values)
        elif not decl.index_sets:
            values[()] = self.signed_number(f"value for '{name}'")
        else:
            self.pair_data(decl, values)
        self.end_statement(f"parameter '{name}'")

    def signed_number(self, what: str) -> float:
        sign = 1.0
        if self.at("-"):
            sign = -1.0
            self.advance()
        elif self.at("+"):
            self.advance()
        if self.tok.kind != "number":
            raise self.error(f"Expected a number for the {what} but found '{self.tok.value or 'end of input'}'.")
        return sign * float(self.advance().value)

    def table_data(self, decl: ParamDecl, columns: List[Member], values: Dict) -> None:
        if len(decl.index_sets) != 2:
            raise self.error(f"Table data needs a parameter indexed over two sets (e.g. param {decl.name}{{R, C}}).")
        while not self.at(";"):
            if self.tok.kind == "eof":
                raise self.error(f"Parameter '{decl.name}' needs a closing ';'.")
            row = self.data_member()
            for column in columns:
                if self.at("."):
                    self.advance()
                    continue
                values[(row, column)] = self.signed_number(f"{decl.name}[{row},{column}]")

    def list_data(self, decl: ParamDecl, values: Dict) -> None:
        token = self.tok
        data = self.nested_list()
        depth = len(decl.index_sets)
        if depth == 0:
            raise self.error(f"Parameter '{decl.name}' is scalar; give a single number.", token)
        self._pending_list = getattr(self, "_pending_list", {})
        self._pending_list[decl.name] = (token, data)

    def nested_list(self) -> Any:
        self.expect("[")
        items: List[Any] = []
        while not self.at("]"):
            if self.tok.kind == "eof":
                raise self.error("A list is missing its closing ']'.")
            if self.at("["):
                items.append(self.nested_list())
            else:
                items.append(self.signed_number("list entry"))
            if self.at(","):
                self.advance()
        self.advance()
        return items

    def pair_data(self, decl: ParamDecl, values: Dict) -> None:
        width = len(decl.index_sets)
        while not self.at(";"):
            if self.tok.kind == "eof":
                raise self.error(f"Parameter '{decl.name}' needs a closing ';'.")
            if self.at("["):
                raise self.error("Mixing list and key/value data is not supported.")
            key = tuple(self.data_member() for _ in range(width))
            values[key] = self.signed_number(f"{decl.name}{list(key)}")
            if self.at(","):
                self.advance()

    # var -----------------------------------------------------------------
    def var_statement(self) -> None:
        self.advance()
        name_tok = self.expect_ident("a variable name")
        indexing = self.indexing() if self.at("{") else None
        decl = VarDecl(name_tok.line, name_tok.col, name_tok.value, indexing)
        while not self.at(";"):
            if self.tok.kind == "eof":
                raise self.error(f"Variable '{decl.name}' needs a closing ';'.")
            if self.at(","):
                self.advance()
            elif self.at(">="):
                self.advance()
                decl.lower = self.expression()
            elif self.at("<="):
                self.advance()
                decl.upper = self.expression()
            elif self.at("=", ":="):
                op = self.advance().value
                value = self.expression()
                if op == "=":
                    decl.fixed = value
            elif self.at_kw("integer", "int"):
                self.advance()
                decl.domain = "integer"
            elif self.at_kw("binary", "bin"):
                self.advance()
                decl.domain = "binary"
            elif self.at_kw("free"):
                self.advance()
                decl.free = True
            elif self.at_kw("continuous"):
                self.advance()
            else:
                raise self.error(
                    f"Unsupported variable attribute '{self.tok.value}'. Use >=, <=, integer, binary, or free."
                )
        self.advance()
        if any(v.name == decl.name for v in self.var_decls):
            raise AmplParseError(f"Variable '{decl.name}' is declared twice.", name_tok.line, name_tok.col)
        self.var_decls.append(decl)

    # objective -------------------------------------------------------------
    def objective_statement(self) -> None:
        sense_tok = self.advance()
        sense = "maximize" if sense_tok.value.lower().startswith("max") else "minimize"
        name = "objective"
        if self.tok.kind == "ident" and self.peek().value == ":":
            name = self.advance().value
            self.advance()
        elif self.at(":"):
            self.advance()
        expr = self.expression()
        self.end_statement("objective")
        if self.objective is not None:
            raise AmplParseError("Only one objective is supported.", sense_tok.line, sense_tok.col)
        self.objective = ObjDecl(sense_tok.line, sense_tok.col, sense, name, expr)

    # constraint ------------------------------------------------------------
    def constraint_body(self) -> None:
        start = self.tok
        name = f"constraint_{len(self.constraints) + 1}"
        indexing = None
        if self.tok.kind == "ident" and self.peek().value in (":", "{"):
            name = self.advance().value
            if self.at("{"):
                indexing = self.indexing()
            self.expect(":", f"after the constraint name '{name}'")
        elif self.at(":"):
            self.advance()
        parts = [self.expression()]
        relations: List[str] = []
        while self.at(*_RELATIONS, "<", ">"):
            rel_tok = self.advance()
            if rel_tok.value in ("<", ">"):
                raise AmplParseError(
                    f"Strict inequality '{rel_tok.value}' is not allowed in linear programs; use '{rel_tok.value}='.",
                    rel_tok.line, rel_tok.col,
                )
            relations.append("=" if rel_tok.value == "==" else rel_tok.value)
            parts.append(self.expression())
        if not relations:
            raise AmplParseError(
                f"Constraint '{name}' needs a relation (<=, >=, or =).", start.line, start.col
            )
        if len(relations) > 2:
            raise AmplParseError(f"Constraint '{name}' has too many relations.", start.line, start.col)
        if len(relations) == 2 and (relations[0] != relations[1] or relations[0] == "="):
            raise AmplParseError(
                f"Double inequality '{name}' must use the same direction twice (lo <= expr <= hi).",
                start.line, start.col,
            )
        self.end_statement(f"constraint '{name}'")
        if any(c.name == name for c in self.constraints):
            raise AmplParseError(f"Constraint name '{name}' is used twice.", start.line, start.col)
        self.constraints.append(ConDecl(start.line, start.col, name, indexing, parts, relations))

    # indexing ----------------------------------------------------------------
    def indexing(self) -> Indexing:
        open_tok = self.expect("{")
        items: List[Tuple[Optional[str], SetExpr]] = []
        while True:
            if self.at("("):
                raise self.error("Tuple indexing such as (i,j) in ARCS is not supported; use i in I, j in J.")
            dummy: Optional[str] = None
            if self.tok.kind == "ident" and self.peek().kind == "ident" and self.peek().value.lower() == "in":
                dummy = self.advance().value
                self.advance()
            items.append((dummy, self.set_expression()))
            if self.at(","):
                self.advance()
                continue
            break
        if self.at(":"):
            raise self.error("Conditional indexing ({i in I: condition}) is not supported.")
        self.expect("}", "to close the indexing expression")
        return Indexing(open_tok.line, open_tok.col, items)

    def set_expression(self) -> SetExpr:
        token = self.tok
        if self.at("{"):
            self.advance()
            members: List[Node] = []
            while not self.at("}"):
                members.append(self.primary())
                if self.at(","):
                    self.advance()
            self.advance()
            return SetExpr(token.line, token.col, "literal", members=members)
        if token.kind == "ident" and self.peek().value != "..":
            self.advance()
            return SetExpr(token.line, token.col, "name", name=token.value)
        low = self.additive()
        self.expect("..", "in the range")
        high = self.additive()
        return SetExpr(token.line, token.col, "range", low=low, high=high)

    # expressions -----------------------------------------------------------
    def expression(self) -> Node:
        return self.additive()

    def additive(self) -> Node:
        node = self.term()
        while self.at("+", "-"):
            op_tok = self.advance()
            right = self.term()
            node = Bin(op_tok.line, op_tok.col, op_tok.value, node, right)
        return node

    def term(self) -> Node:
        node = self.unary()
        while self.at("*", "/"):
            op_tok = self.advance()
            right = self.unary()
            node = Bin(op_tok.line, op_tok.col, op_tok.value, node, right)
        return node

    def unary(self) -> Node:
        if self.at("-"):
            token = self.advance()
            return Neg(token.line, token.col, self.unary())
        if self.at("+"):
            self.advance()
            return self.unary()
        return self.power()

    def power(self) -> Node:
        node = self.primary()
        if self.at("^", "**"):
            op_tok = self.advance()
            exponent = self.unary()
            node = Bin(op_tok.line, op_tok.col, "^", node, exponent)
        return node

    def primary(self) -> Node:
        token = self.tok
        if token.kind == "number":
            self.advance()
            return Num(token.line, token.col, float(token.value))
        if token.kind == "string":
            self.advance()
            return Lit(token.line, token.col, token.value[1:-1])
        if self.at("("):
            self.advance()
            node = self.expression()
            self.expect(")", "to close the parenthesis")
            return node
        if token.kind == "ident" and token.value.lower() == "sum":
            self.advance()
            if not self.at("{"):
                raise self.error("'sum' must be followed by an indexing expression like {i in I}.")
            indexing = self.indexing()
            body = self.term()
            return Sum(token.line, token.col, indexing, body)
        if token.kind == "ident" and token.value.lower() in ("if", "max", "min", "abs", "prod", "exp", "log", "sqrt"):
            raise self.error(f"'{token.value}' is not supported in a linear model.")
        if token.kind == "ident":
            self.advance()
            ref = Ref(token.line, token.col, token.value)
            if self.at("["):
                self.advance()
                ref.subscripted = True
                while True:
                    ref.indices.append(self.additive())
                    if self.at(","):
                        self.advance()
                        continue
                    break
                self.expect("]", f"to close the subscript of '{token.value}'")
            return ref
        found = token.value or "end of input"
        raise self.error(f"Expected a number, name, or '(' but found '{found}'.")


def _dedupe(members: List[Member], name: str) -> List[Member]:
    seen: Dict[Member, None] = {}
    for member in members:
        seen.setdefault(member, None)
    return list(seen)


# ---------------------------------------------------------------------------
#  Expansion
# ---------------------------------------------------------------------------

class _Expander:
    def __init__(self, parser: _Parser, text: str):
        self.p = parser
        self.text = text
        self.sets: Dict[str, List[Member]] = {}
        self.var_index: Dict[str, VarDecl] = {}
        self.var_names: Dict[str, Dict[Tuple[Member, ...], str]] = {}

    def run(self) -> AmplResult:
        p = self.p
        for name, members in p.sets.items():
            if members is None:
                loc = p.set_locs[name]
                raise AmplParseError(f"Set '{name}' is declared but has no members. Add 'set {name} := ...;'.", loc.line, loc.col)
            self.sets[name] = members
        self._resolve_list_params()

        variables: List[VariableSpec] = []
        indexed_meta: Dict[str, Dict[str, Any]] = {}
        for decl in p.var_decls:
            self.var_index[decl.name] = decl
            names: Dict[Tuple[Member, ...], str] = {}
            combos = list(self.combinations(decl.indexing, {})) if decl.indexing else [({}, ())]
            for env, key in combos:
                full_name = _element_name(decl.name, key) if decl.indexing else decl.name
                names[key] = full_name
                variables.append(self.make_variable(decl, full_name, env))
            self.var_names[decl.name] = names
            if decl.indexing:
                indexed_meta[decl.name] = {
                    "sets": [s.name if s.kind == "name" else "range" for _, s in decl.indexing.items],
                    "count": len(names),
                    "domain": decl.domain,
                }
        if len(variables) > 200000:
            raise AmplParseError("The expanded model has more than 200,000 variables.")

        if p.objective is None:
            raise AmplParseError("Define an objective with 'maximize name: ...;' or 'minimize name: ...;'.")
        obj_expr = self.linear(p.objective.expr, {})
        objective = ObjectiveSpec(p.objective.sense, obj_expr, p.objective.name)

        constraints: List[ConstraintSpec] = []
        for decl in p.constraints:
            combos = list(self.combinations(decl.indexing, {})) if decl.indexing else [({}, ())]
            for env, key in combos:
                base = _element_name(decl.name, key) if decl.indexing else decl.name
                constraints.extend(self.make_constraints(decl, base, env))

        unconstrained = [v.name for v in variables if v.lower_bound is None and v.variable_type == "continuous"]
        notes = list(p.notes)
        if unconstrained and len(unconstrained) <= 6:
            notes.append(
                "No lower bound on " + ", ".join(unconstrained)
                + " (AMPL default is free). Add '>= 0' if they should be nonnegative."
            )
        elif unconstrained:
            notes.append(f"{len(unconstrained)} variables have no lower bound (AMPL default is free).")

        spec = ModelSpec(
            name="AMPL_Model",
            variables=variables,
            objective=objective,
            constraints=constraints,
            source_syntax="ampl",
            source_text=self.text,
        ).with_uids().validate()

        params_out: Dict[str, Dict[str, Any]] = {}
        for name, decl in p.params.items():
            params_out[name] = {
                "index_sets": decl.index_sets,
                "values": dict(p.param_values.get(name, {})),
                "default": decl.default,
            }
        return AmplResult(spec, dict(self.sets), params_out, indexed_meta, notes)

    def _resolve_list_params(self) -> None:
        pending = getattr(self.p, "_pending_list", {})
        for name, (token, data) in pending.items():
            decl = self.p.params[name]
            index_lists = []
            for set_name in decl.index_sets:
                if set_name not in self.sets:
                    raise AmplParseError(f"Parameter '{name}' is indexed over unknown set '{set_name}'.", token.line, token.col)
                index_lists.append(self.sets[set_name])
            values = self.p.param_values[name]

            def fill(level: int, prefix: Tuple[Member, ...], item: Any) -> None:
                if level == len(index_lists):
                    if isinstance(item, list):
                        raise AmplParseError(f"Parameter '{name}' list is nested too deeply.", token.line, token.col)
                    values[prefix] = float(item)
                    return
                members = index_lists[level]
                if not isinstance(item, list) or len(item) != len(members):
                    got = len(item) if isinstance(item, list) else 1
                    raise AmplParseError(
                        f"Parameter '{name}' expects {len(members)} entries for set "
                        f"'{decl.index_sets[level]}' but the list has {got}.",
                        token.line, token.col,
                    )
                for member, sub in zip(members, item):
                    fill(level + 1, prefix + (member,), sub)

            fill(0, (), data)

    # -- helpers -------------------------------------------------------------
    def members_of(self, set_expr: SetExpr, env: Dict[str, Member]) -> List[Member]:
        if set_expr.kind == "name":
            if set_expr.name not in self.sets:
                raise AmplParseError(f"Unknown set '{set_expr.name}'.", set_expr.line, set_expr.col)
            return self.sets[set_expr.name]
        if set_expr.kind == "range":
            low = self.constant(set_expr.low, env, "range start")
            high = self.constant(set_expr.high, env, "range end")
            if not (float(low).is_integer() and float(high).is_integer()):
                raise AmplParseError("Range endpoints must be integers.", set_expr.line, set_expr.col)
            return list(range(int(low), int(high) + 1))
        return [self.member_value(node, env) for node in set_expr.members]

    def combinations(self, indexing: Optional[Indexing], env: Dict[str, Member]) -> Iterable[Tuple[Dict[str, Member], Tuple[Member, ...]]]:
        if indexing is None:
            yield dict(env), ()
            return

        def rec(i: int, current: Dict[str, Member], key: Tuple[Member, ...]):
            if i == len(indexing.items):
                yield current, key
                return
            dummy, set_expr = indexing.items[i]
            for member in self.members_of(set_expr, current):
                nxt = dict(current)
                if dummy:
                    if dummy in self.var_index or dummy in self.p.params:
                        raise AmplParseError(f"Index name '{dummy}' clashes with a variable or parameter.", set_expr.line, set_expr.col)
                    nxt[dummy] = member
                yield from rec(i + 1, nxt, key + (member,))

        yield from rec(0, dict(env), ())

    def member_value(self, node: Node, env: Dict[str, Member]) -> Member:
        if isinstance(node, Lit):
            return node.value
        if isinstance(node, Ref) and not node.subscripted:
            if node.name in env:
                return env[node.name]
            if node.name not in self.var_index and node.name not in self.p.params and self._is_member(node.name):
                return node.name
        value = self.constant(node, env, "subscript")
        return int(value) if float(value).is_integer() else value

    def _is_member(self, name: str) -> bool:
        return any(name in members for members in self.sets.values())

    def constant(self, node: Node, env: Dict[str, Member], what: str) -> float:
        expr = self.linear(node, env)
        if expr.coefficients:
            raise AmplParseError(f"The {what} must be a constant, not a variable expression.", node.line, node.col)
        return expr.constant

    def param_value(self, ref: Ref, env: Dict[str, Member]) -> float:
        decl = self.p.params[ref.name]
        if len(ref.indices) != len(decl.index_sets):
            raise AmplParseError(
                f"Parameter '{ref.name}' needs {len(decl.index_sets)} subscript(s); got {len(ref.indices)}.",
                ref.line, ref.col,
            )
        key = tuple(self.member_value(node, env) for node in ref.indices)
        for set_name, member in zip(decl.index_sets, key):
            if set_name in self.sets and member not in self.sets[set_name]:
                raise AmplParseError(f"'{member}' is not a member of set '{set_name}' (in {ref.name}).", ref.line, ref.col)
        values = self.p.param_values.get(ref.name, {})
        if key in values:
            return values[key]
        if decl.default is not None:
            return decl.default
        label = ref.name + (f"[{', '.join(str(k) for k in key)}]" if key else "")
        raise AmplParseError(f"No value was given for parameter {label}.", ref.line, ref.col)

    def linear(self, node: Node, env: Dict[str, Member]) -> LinearExpression:
        if isinstance(node, Num):
            return LinearExpression(constant=node.value)
        if isinstance(node, Lit):
            raise AmplParseError(f"Text '{node.value}' cannot be used as a number.", node.line, node.col)
        if isinstance(node, Neg):
            return self.linear(node.operand, env).scaled(-1.0)
        if isinstance(node, Sum):
            total = LinearExpression()
            for inner_env, _ in self.combinations(node.indexing, env):
                total = total.plus(self.linear(node.body, inner_env))
            return total
        if isinstance(node, Bin):
            left = self.linear(node.left, env)
            right = self.linear(node.right, env)
            if node.op == "+":
                return left.plus(right)
            if node.op == "-":
                return left.minus(right)
            if node.op == "*":
                if left.coefficients and right.coefficients:
                    raise AmplParseError("Nonlinear term: a variable is multiplied by a variable.", node.line, node.col)
                if left.coefficients:
                    return left.scaled(right.constant)
                return right.scaled(left.constant)
            if node.op == "/":
                if right.coefficients:
                    raise AmplParseError("Nonlinear term: division by a variable.", node.line, node.col)
                if right.constant == 0:
                    raise AmplParseError("Division by zero.", node.line, node.col)
                return left.scaled(1.0 / right.constant)
            if node.op == "^":
                if left.coefficients or right.coefficients:
                    raise AmplParseError("Nonlinear term: powers of variables are not linear.", node.line, node.col)
                return LinearExpression(constant=left.constant ** right.constant)
        if isinstance(node, Ref):
            return self.reference(node, env)
        raise AmplParseError("Unsupported expression.", node.line, node.col)

    def reference(self, ref: Ref, env: Dict[str, Member]) -> LinearExpression:
        name = ref.name
        if name in env and not ref.subscripted:
            value = env[name]
            if isinstance(value, str):
                raise AmplParseError(f"Index '{name}' has the text value '{value}' and cannot be used as a number.", ref.line, ref.col)
            return LinearExpression(constant=float(value))
        if name in self.var_index:
            decl = self.var_index[name]
            expected = len(decl.indexing.items) if decl.indexing else 0
            if len(ref.indices) != expected:
                raise AmplParseError(
                    f"Variable '{name}' needs {expected} subscript(s); got {len(ref.indices)}.", ref.line, ref.col
                )
            key = tuple(self.member_value(node, env) for node in ref.indices)
            full = self.var_names.get(name, {}).get(key)
            if full is None:
                label = f"{name}[{', '.join(str(k) for k in key)}]"
                raise AmplParseError(f"{label} is outside the declared index sets.", ref.line, ref.col)
            return LinearExpression({full: 1.0})
        if name in self.p.params:
            return LinearExpression(constant=self.param_value(ref, env))
        if name in self.sets:
            raise AmplParseError(f"Set '{name}' cannot be used as a number.", ref.line, ref.col)
        raise AmplParseError(f"'{name}' is not a declared variable, parameter, or index.", ref.line, ref.col)

    def make_variable(self, decl: VarDecl, full_name: str, env: Dict[str, Member]) -> VariableSpec:
        lower: Optional[float] = None
        upper: Optional[float] = None
        if decl.lower is not None:
            lower = self.constant(decl.lower, env, "lower bound")
        if decl.upper is not None:
            upper = self.constant(decl.upper, env, "upper bound")
        if decl.fixed is not None:
            lower = upper = self.constant(decl.fixed, env, "fixed value")
        if decl.domain == "binary":
            lower = 0.0 if lower is None else max(0.0, lower)
            upper = 1.0 if upper is None else min(1.0, upper)
        if decl.free:
            lower = upper = None
        return VariableSpec(full_name, decl.domain, lower, upper)

    def make_constraints(self, decl: ConDecl, base: str, env: Dict[str, Member]) -> List[ConstraintSpec]:
        exprs = [self.linear(part, env) for part in decl.parts]
        source = f"line {decl.line}"
        if len(decl.relations) == 1:
            diff = exprs[0].minus(exprs[1])
            if not diff.coefficients:
                raise AmplParseError(f"Constraint '{base}' contains no variables.", decl.line, decl.col)
            return [ConstraintSpec(base, LinearExpression(diff.coefficients, 0.0), decl.relations[0], -diff.constant, source)]
        low_expr, mid, high_expr = exprs
        if low_expr.coefficients or high_expr.coefficients:
            raise AmplParseError(f"In '{base}', the outer bounds of 'lo <= expr <= hi' must be constants.", decl.line, decl.col)
        if decl.relations[0] == ">=":
            low_expr, high_expr = high_expr, low_expr
        body = LinearExpression(mid.coefficients, 0.0)
        return [
            ConstraintSpec(f"{base}_lo", body, ">=", low_expr.constant - mid.constant, source),
            ConstraintSpec(f"{base}_hi", body, "<=", high_expr.constant - mid.constant, source),
        ]


def _element_name(base: str, key: Sequence[Member]) -> str:
    return f"{base}[{','.join(_member_text(k) for k in key)}]"


def _member_text(member: Member) -> str:
    if isinstance(member, float) and member.is_integer():
        return str(int(member))
    return str(member)


# ---------------------------------------------------------------------------
#  Public API
# ---------------------------------------------------------------------------

def parse_ampl_detailed(text: str) -> AmplResult:
    parser = _Parser(text)
    parser.parse()
    return _Expander(parser, text).run()


def parse_ampl(text: str) -> ModelSpec:
    return parse_ampl_detailed(text).spec
