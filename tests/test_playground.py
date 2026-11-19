"""Tests for deterministic Model Playground workflows."""

import pytest

from src.modeling.ampl_parser import AmplParseError
from src.modeling.orlearn_parser import ORLearnParseError
from src.modeling.playground_examples import EXAMPLES
from src.modeling.playground_parser import detect_syntax, parse_model
from src.services.model_playground import solve_model_spec

AMPL_MODEL = """
var x >= 0;
var y >= 0;
maximize profit: 3*x + 2*y;
subject to capacity: x + y <= 4;
subject to resource: 2*x + y <= 5;
solve;
"""


def test_detects_both_syntaxes():
    assert detect_syntax(AMPL_MODEL) == "ampl"
    assert (
        detect_syntax(EXAMPLES["Production planning · OR-Learn"]["text"]) == "orlearn"
    )


def test_parses_ampl_domains_and_constraints():
    spec = parse_model(
        "var x >= -2 <= 9, integer; var y binary; "
        "minimize cost: 2*x-y; subject to balance: x+y >= 3;"
    )
    assert spec.variables[0].variable_type == "integer"
    assert spec.variables[0].lower_bound == -2
    assert spec.variables[0].upper_bound == 9
    assert spec.variables[1].variable_type == "binary"
    assert spec.constraints[0].sense == ">="


def test_parses_orlearn_example():
    spec = parse_model(EXAMPLES["Binary knapsack · OR-Learn"]["text"])
    assert len(spec.variables) == 3
    assert all(variable.variable_type == "binary" for variable in spec.variables)
    assert spec.constraints[0].rhs == 50


def test_solves_end_to_end():
    result = solve_model_spec(parse_model(AMPL_MODEL))
    assert result["is_optimal"] is True
    assert result["objective_value"] == pytest.approx(9)
    assert result["variables"] == pytest.approx({"x": 1, "y": 3})


def test_reports_nonlinear_expression():
    with pytest.raises(AmplParseError, match="Nonlinear"):
        parse_model(
            "var x; var y; maximize value: x*y; subject to cap: x+y <= 2;",
            "ampl",
        )


@pytest.mark.parametrize(
    "source",
    [
        'import os\nos.system("echo unsafe")',
        'OR().maximize(__import__("os").system("echo unsafe")).solve()',
        'OR().maximize([1]).subject_to([1], "<=", 2).solve()\nprint(__import__("os").system("echo unsafe"))',
        'r = OR().maximize([1]).subject_to([1], "<=", 2).solve()\nprint(r.summary(open("x")))',
    ],
)
def test_orlearn_parser_never_executes_arbitrary_python(source):
    with pytest.raises(ORLearnParseError):
        parse_model(source, "orlearn")


def test_orlearn_display_prints_are_skipped_not_run():
    spec = parse_model('OR().maximize([1]).subject_to([1], "<=", 2).solve()\nprint("extra")', "orlearn")
    assert [v.name for v in spec.variables] == ["x1"]


def test_rejects_undeclared_ampl_variable():
    with pytest.raises(ValueError, match="not a declared variable"):
        parse_model(
            "var x; maximize value: x+y; subject to cap: x <= 2;",
            "ampl",
        )
