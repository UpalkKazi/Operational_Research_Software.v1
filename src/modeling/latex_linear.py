"""Safe conversion between LaTeX (as produced by MathLive) and linear expressions.

Only linear arithmetic over the model's declared variables is accepted:
numbers, + − × ÷, parentheses, ``\\frac`` with constant denominators and
constant powers.  Summations, products of variables, roots and functions are
rejected with a message explaining that the Live Editor cannot solve them.
"""

from __future__ import annotations

import re
from typing import Dict, Iterable, List, Optional, Tuple

from .model_spec import LinearExpression


class LatexError(ValueError):
    def __init__(self, message: str, unsupported: bool = False):
        super().__init__(message)
        self.unsupported = unsupported


# ---------------------------------------------------------------------------
#  Number and name rendering
# ---------------------------------------------------------------------------

def latex_number(value: float) -> str:
    value = float(value)
    if value.is_integer() and abs(value) < 1e15:
        return str(int(value))
    text = format(value, ".15g")
    if "e" in text:
        mantissa, exponent = text.split("e")
        return f"{mantissa}\\times10^{{{int(exponent)}}}"
    return text


_ESCAPES = {"\\": r"\backslash ", "_": r"\_", "#": r"\#", "$": r"\$", "%": r"\%", "&": r"\&", "{": r"\{", "}": r"\}", "^": r"\^{}", "~": r"\sim "}


def _escape(text: str) -> str:
    return "".join(_ESCAPES.get(ch, ch) for ch in text)


def _name_part(text: str) -> str:
    if len(text) == 1 and text.isalpha():
        return text
    if text.isdigit():
        return text
    return r"\mathrm{" + _escape(text) + "}"


def variable_latex(name: str) -> str:
    match = re.fullmatch(r"([A-Za-z])(\d+)", name)
    if match:
        return f"{match.group(1)}_{{{match.group(2)}}}"
    match = re.fullmatch(r"([A-Za-z][A-Za-z0-9_]*)\[([^\[\]]+)\]", name)
    if match:
        parts = [p.strip() for p in match.group(2).split(",")]
        return _name_part(match.group(1)) + "_{" + ",".join(_name_part(p) for p in parts) + "}"
    match = re.fullmatch(r"([A-Za-z])_(\d+)", name)
    if match:
        return f"{match.group(1)}_{{{match.group(2)}}}"
    return _name_part(name)


def latex_names(names: Iterable[str]) -> Dict[str, str]:
    """Map variable names to unambiguous LaTeX symbols."""
    names = list(names)
    proposed = {n: variable_latex(n) for n in names}
    seen: Dict[str, str] = {}
    result: Dict[str, str] = {}
    for name in names:
        form = normalize(proposed[name])
        if form in seen and seen[form] != name:
            result[name] = r"\mathrm{" + _escape(name) + "}"
        else:
            seen[form] = name
            result[name] = proposed[name]
    return result


def linear_to_latex(expression: LinearExpression, symbols: Dict[str, str], max_terms: Optional[int] = None) -> str:
    parts: List[str] = []
    items = [(n, c) for n, c in expression.coefficients.items() if c != 0]
    hidden = 0
    if max_terms is not None and len(items) > max_terms:
        hidden = len(items) - max_terms
        items = items[:max_terms]
    for name, coefficient in items:
        symbol = symbols.get(name) or variable_latex(name)
        magnitude = abs(coefficient)
        term = symbol if magnitude == 1 else f"{latex_number(magnitude)}\\,{symbol}"
        if not parts:
            parts.append(f"-{term}" if coefficient < 0 else term)
        else:
            parts.append(("-" if coefficient < 0 else "+") + term)
    if hidden:
        parts.append(r"+\cdots" + f"\\;\\text{{({hidden} more terms)}}")
    if expression.constant or not parts:
        constant = latex_number(abs(expression.constant))
        if not parts:
            parts.append(f"-{constant}" if expression.constant < 0 else constant)
        else:
            parts.append(("-" if expression.constant < 0 else "+") + constant)
    return "".join(parts)


# ---------------------------------------------------------------------------
#  Normalisation
# ---------------------------------------------------------------------------

_WRAPPERS = ("mathrm", "text", "textrm", "operatorname", "mathit", "mathbf", "textit", "textbf", "mathsf", "boldsymbol", "mathnormal")
_DROP = (r"\left", r"\right", r"\!", r"\,", r"\;", r"\:", r"\quad", r"\qquad", r"\displaystyle", r"\limits", r"\bigl", r"\bigr", r"\Bigl", r"\Bigr", r"\big", r"\Big")
_REPLACE = [
    (r"\cdot", "*"), (r"\times", "*"), (r"\ast", "*"), (r"\div", "/"),
    (r"\leqslant", "<="), (r"\geqslant", ">="), (r"\leq", "<="), (r"\geq", ">="), (r"\le", "<="), (r"\ge", ">="),
    (r"\lt", "<"), (r"\gt", ">"), (r"\_", "_"), (r"\#", "#"), (r"\$", "$"), (r"\%", "%"), (r"\&", "&"),
    (r"\{", "\x01"), (r"\}", "\x02"), (r"\backslash", "\\\\"), (r"\^{}", "^"), (r"\sim", "~"),
    ("−", "-"), ("×", "*"), ("·", "*"), ("≤", "<="), ("≥", ">="), ("{,}", ""),
]


def _matching(text: str, start: int) -> int:
    depth = 0
    for index in range(start, len(text)):
        if text[index] == "{":
            depth += 1
        elif text[index] == "}":
            depth -= 1
            if depth == 0:
                return index
    raise LatexError("Unbalanced braces in the expression.")


def _unwrap(text: str) -> str:
    pattern = re.compile(r"\\(" + "|".join(_WRAPPERS) + r")\s*\{")
    while True:
        match = pattern.search(text)
        if not match:
            return text
        open_index = match.end() - 1
        close_index = _matching(text, open_index)
        inner = text[open_index + 1:close_index]
        text = text[:match.start()] + inner + text[close_index + 1:]


def _frac(text: str) -> str:
    pattern = re.compile(r"\\[dt]?frac\s*")
    while True:
        match = pattern.search(text)
        if not match:
            return text
        position = match.end()
        groups = []
        for _ in range(2):
            if position < len(text) and text[position] == "{":
                close = _matching(text, position)
                groups.append(text[position + 1:close])
                position = close + 1
            elif position < len(text):
                groups.append(text[position])
                position += 1
            else:
                raise LatexError("A fraction is missing its numerator or denominator.")
        text = text[:match.start()] + f"(({groups[0]})/({groups[1]}))" + text[position:]


def normalize(latex: str) -> str:
    text = latex or ""
    for token in _DROP:
        text = text.replace(token, "")
    text = _unwrap(text)
    text = _frac(text)
    for old, new in _REPLACE:
        text = text.replace(old, new)
    text = re.sub(r"\s+", "", text)
    text = re.sub(r"_([^{\s])", r"_{\1}", text)
    text = re.sub(r"\^([^{\s])", r"^{\1}", text)
    return text


# ---------------------------------------------------------------------------
#  Parsing
# ---------------------------------------------------------------------------

_UNSUPPORTED = {
    "sum": "Summations (∑) can't be solved in the Live Editor; write the terms out or use the Algebraic tab.",
    "prod": "Products (∏) are not linear.",
    "int": "Integrals are not supported in linear models.",
    "sqrt": "Square roots are not linear.",
    "log": "Logarithms are not linear.", "ln": "Logarithms are not linear.", "exp": "Exponentials are not linear.",
    "sin": "Trigonometric functions are not linear.", "cos": "Trigonometric functions are not linear.",
    "max": "max() is not linear; add separate constraints instead.", "min": "min() is not linear; add separate constraints instead.",
    "infty": "Infinity can't be used inside an expression; leave the bound empty for unbounded.",
}


class _Tokens:
    def __init__(self, text: str, forms: List[Tuple[str, str]]):
        self.items: List[Tuple[str, str]] = []
        position = 0
        word_re = re.compile(r"[A-Za-z][A-Za-z0-9_]*(?:_\{[^{}]*\})*")
        number_re = re.compile(r"\d+(?:\.\d*)?|\.\d+")
        lookup: Dict[str, List[Tuple[str, str]]] = {}
        for form, name in forms:
            lookup.setdefault(form[0], []).append((form, name))
        while position < len(text):
            char = text[position]
            candidates = lookup.get(char, [])
            match_name = None
            for form, name in candidates:
                if text.startswith(form, position):
                    end = position + len(form)
                    boundary = end >= len(text) or not (text[end].isalnum() or text[end] == "_") or not form[-1].isalnum()
                    if boundary:
                        match_name = (form, name)
                        break
            if match_name:
                self.items.append(("var", match_name[1]))
                position += len(match_name[0])
                continue
            if char.isalpha():
                word_match = word_re.match(text, position)
                word = word_match.group() if word_match else char
                pieces = _segment(word, forms)
                if pieces is None:
                    raise LatexError(f"'{word.replace('_{', '_').replace('}', '')}' is not a variable in this model.")
                self.items.extend(("var", p) for p in pieces)
                position += len(word)
                continue
            if char.isdigit() or char == ".":
                number_match = number_re.match(text, position)
                if not number_match:
                    raise LatexError(f"Unexpected '{char}'.")
                self.items.append(("num", number_match.group()))
                position = number_match.end()
                continue
            if char == "\\":
                command = re.match(r"\\([A-Za-z]+)", text[position:])
                name = command.group(1) if command else text[position:position + 2]
                if name in _UNSUPPORTED:
                    raise LatexError(_UNSUPPORTED[name], unsupported=True)
                raise LatexError(f"'\\{name}' is not supported in a linear expression.", unsupported=True)
            for op in ("<=", ">=", "=", "<", ">", "+", "-", "*", "/", "(", ")", "{", "}", "^", "[", "]"):
                if text.startswith(op, position):
                    if op in ("<", ">"):
                        raise LatexError("Strict inequalities (< or >) aren't allowed; use ≤ or ≥.")
                    self.items.append(("op", {"[": "(", "]": ")"}.get(op, op)))
                    position += len(op)
                    break
            else:
                if char == "_":
                    raise LatexError("A subscript must follow a variable name.")
                raise LatexError(f"Unexpected symbol '{char}'.")
        self.position = 0

    def peek(self) -> Optional[Tuple[str, str]]:
        return self.items[self.position] if self.position < len(self.items) else None

    def take(self) -> Tuple[str, str]:
        item = self.items[self.position]
        self.position += 1
        return item


def _segment(word: str, forms: List[Tuple[str, str]]) -> Optional[List[str]]:
    table = {form: name for form, name in forms}
    memo: Dict[int, Optional[List[str]]] = {}

    def rec(index: int) -> Optional[List[str]]:
        if index == len(word):
            return []
        if index in memo:
            return memo[index]
        best = None
        for end in range(len(word), index, -1):
            piece = word[index:end]
            if piece in table:
                rest = rec(end)
                if rest is not None:
                    best = [table[piece], *rest]
                    break
        memo[index] = best
        return best

    return rec(0)


def _forms(names: Iterable[str], symbols: Optional[Dict[str, str]] = None) -> List[Tuple[str, str]]:
    names = list(names)
    symbols = symbols or latex_names(names)
    table: Dict[str, Optional[str]] = {}

    def add(form: str, name: str) -> None:
        if not form:
            return
        if form in table and table[form] != name:
            table[form] = None
        else:
            table[form] = name

    for name in names:
        add(normalize(symbols[name]), name)
    for name in names:
        add(normalize(_escape(name)), name)
        add(name, name)
    forms = [(form, name) for form, name in table.items() if name is not None]
    forms.sort(key=lambda item: len(item[0]), reverse=True)
    return forms


class _Parser:
    def __init__(self, tokens: _Tokens):
        self.t = tokens

    def expression(self) -> LinearExpression:
        node = self.term()
        while self.t.peek() in (("op", "+"), ("op", "-")):
            op = self.t.take()[1]
            right = self.term()
            node = node.plus(right) if op == "+" else node.minus(right)
        return node

    def _starts_factor(self) -> bool:
        item = self.t.peek()
        return item is not None and (item[0] in ("num", "var") or item in (("op", "("), ("op", "{")))

    def term(self) -> LinearExpression:
        node = self.unary()
        while True:
            item = self.t.peek()
            if item in (("op", "*"), ("op", "/")):
                op = self.t.take()[1]
                right = self.unary()
            elif self._starts_factor():
                op, right = "*", self.unary()
            else:
                return node
            if op == "*":
                if node.coefficients and right.coefficients:
                    raise LatexError("Nonlinear term: two variables are multiplied together.", unsupported=True)
                node = node.scaled(right.constant) if node.coefficients else right.scaled(node.constant)
            else:
                if right.coefficients:
                    raise LatexError("Nonlinear term: division by a variable.", unsupported=True)
                if right.constant == 0:
                    raise LatexError("Division by zero.")
                node = node.scaled(1.0 / right.constant)

    def unary(self) -> LinearExpression:
        item = self.t.peek()
        if item == ("op", "-"):
            self.t.take()
            return self.unary().scaled(-1.0)
        if item == ("op", "+"):
            self.t.take()
            return self.unary()
        return self.power()

    def power(self) -> LinearExpression:
        base = self.atom()
        if self.t.peek() == ("op", "^"):
            self.t.take()
            exponent = self.atom()
            if base.coefficients or exponent.coefficients:
                raise LatexError("Powers of variables are not linear.", unsupported=True)
            return LinearExpression(constant=base.constant ** exponent.constant)
        return base

    def atom(self) -> LinearExpression:
        item = self.t.peek()
        if item is None:
            raise LatexError("The expression ends unexpectedly.")
        kind, value = self.t.take()
        if kind == "num":
            return LinearExpression(constant=float(value))
        if kind == "var":
            return LinearExpression({value: 1.0})
        if value in ("(", "{"):
            closing = ")" if value == "(" else "}"
            inner = self.expression()
            if self.t.peek() != ("op", closing):
                raise LatexError(f"Missing '{closing}'.")
            self.t.take()
            return inner
        raise LatexError(f"Unexpected '{value}'.")


def _split_relation(tokens: _Tokens) -> Tuple[List[Tuple[str, str]], Optional[str], List[Tuple[str, str]]]:
    depth = 0
    for index, item in enumerate(tokens.items):
        if item in (("op", "("), ("op", "{")):
            depth += 1
        elif item in (("op", ")"), ("op", "}")):
            depth -= 1
        elif depth == 0 and item[0] == "op" and item[1] in ("<=", ">=", "="):
            rest = tokens.items[index + 1:]
            if any(r[0] == "op" and r[1] in ("<=", ">=", "=") for r in rest):
                raise LatexError("Use a single relation (≤, ≥ or =) per constraint.")
            return tokens.items[:index], item[1], rest
    return tokens.items, None, []


def _parse_items(items: List[Tuple[str, str]], forms) -> LinearExpression:
    holder = _Tokens("", forms)
    holder.items = items
    parser = _Parser(holder)
    if not items:
        raise LatexError("The expression is empty.")
    result = parser.expression()
    if holder.position != len(items):
        raise LatexError(f"Unexpected '{items[holder.position][1]}'.")
    return result


def latex_to_linear(latex: str, names: Iterable[str], symbols: Optional[Dict[str, str]] = None) -> LinearExpression:
    forms = _forms(names, symbols)
    tokens = _Tokens(normalize(latex), forms)
    left, relation, _right = _split_relation(tokens)
    if relation is not None:
        raise LatexError("The objective can't contain ≤, ≥ or =.")
    return _parse_items(left, forms)


def latex_to_constraint(
    latex: str, names: Iterable[str], symbols: Optional[Dict[str, str]] = None
) -> Tuple[LinearExpression, Optional[str], Optional[float]]:
    """Parse a constraint left-hand side, optionally containing a relation.

    Returns ``(lhs, relation, rhs)``.  When the LaTeX contains a relation the
    variables are moved to the left and constants to the right.
    """
    forms = _forms(names, symbols)
    tokens = _Tokens(normalize(latex), forms)
    left, relation, right = _split_relation(tokens)
    lhs = _parse_items(left, forms)
    if relation is None:
        return lhs, None, None
    rhs = _parse_items(right, forms)
    diff = lhs.minus(rhs)
    if not diff.coefficients:
        raise LatexError("The constraint has no variables.")
    return LinearExpression(diff.coefficients, 0.0), relation, -diff.constant
