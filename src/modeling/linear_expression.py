"""Safe parser and formatter for scalar linear expressions."""

from __future__ import annotations

import ast
from typing import Union

from .model_spec import LinearExpression


class ExpressionError(ValueError):
    """Raised for invalid or nonlinear algebra."""


Number = Union[int, float]


def parse_linear_expression(text: str) -> LinearExpression:
    try:
        node = ast.parse(text.strip(), mode="eval").body
    except SyntaxError as exc:
        raise ExpressionError(
            f"Invalid expression near column {exc.offset}: {exc.msg}."
        ) from exc
    return _parse_node(node)


def _parse_node(node: ast.AST) -> LinearExpression:
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return LinearExpression(constant=float(node.value))
    if isinstance(node, ast.Name):
        return LinearExpression(coefficients={node.id: 1.0})
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
        value = _parse_node(node.operand)
        factor = -1.0 if isinstance(node.op, ast.USub) else 1.0
        return _scale(value, factor)
    if isinstance(node, ast.BinOp) and isinstance(node.op, (ast.Add, ast.Sub)):
        left, right = _parse_node(node.left), _parse_node(node.right)
        return (
            left.minus(_scale(right, -1.0))
            if isinstance(node.op, ast.Add)
            else left.minus(right)
        )
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Mult):
        left, right = _parse_node(node.left), _parse_node(node.right)
        if left.coefficients and right.coefficients:
            raise ExpressionError(
                "Nonlinear terms are not supported (variable × variable)."
            )
        if left.coefficients:
            return _scale(left, _constant_value(right))
        if right.coefficients:
            return _scale(right, _constant_value(left))
        return LinearExpression(constant=left.constant * right.constant)
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div):
        numerator, denominator = _parse_node(node.left), _parse_node(node.right)
        divisor = _constant_value(denominator)
        if divisor == 0:
            raise ExpressionError("Division by zero is not allowed.")
        return _scale(numerator, 1.0 / divisor)

    raise ExpressionError(
        "Only numbers, variable names, parentheses, and linear +, -, *, / operations are supported."
    )


def _constant_value(expression: LinearExpression) -> float:
    if expression.coefficients:
        raise ExpressionError(
            "A linear expression can only be multiplied or divided by a number."
        )
    return expression.constant


def _scale(expression: LinearExpression, factor: Number) -> LinearExpression:
    return LinearExpression(
        coefficients={
            name: value * float(factor)
            for name, value in expression.coefficients.items()
        },
        constant=expression.constant * float(factor),
    )


def format_number(value: float) -> str:
    if float(value).is_integer():
        return str(int(value))
    return f"{value:.6g}"


def format_expression(expression: LinearExpression) -> str:
    parts = []
    for name, coefficient in expression.coefficients.items():
        if abs(coefficient) < 1e-12:
            continue
        magnitude = abs(coefficient)
        term = name if magnitude == 1 else f"{format_number(magnitude)}·{name}"
        if not parts:
            parts.append(f"-{term}" if coefficient < 0 else term)
        else:
            parts.append(f"{'-' if coefficient < 0 else '+'} {term}")
    if expression.constant or not parts:
        constant = format_number(abs(expression.constant))
        if not parts:
            parts.append(f"-{constant}" if expression.constant < 0 else constant)
        else:
            parts.append(f"{'-' if expression.constant < 0 else '+'} {constant}")
    return " ".join(parts)
