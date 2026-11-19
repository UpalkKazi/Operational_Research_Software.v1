"""Curated Model Playground examples.

OR-Learn examples are adapted from https://github.com/harunpirim/orlearn
(MIT license, commit 38355732feae2c6cc776d58b6f01491bbce78124).
"""

from __future__ import annotations

from typing import Dict

EXAMPLES: Dict[str, Dict[str, str]] = {
    "Production planning · OR-Learn": {
        "syntax": "orlearn",
        "description": "Maximize profit for chairs and tables under wood and labor limits.",
        "source": "Adapted from OR-Learn README (MIT).",
        "text": """from orlearn import OR

model = (OR()
    .maximize([45, 80], names=["chairs", "tables"])
    .subject_to([5, 20], "<=", 400, "wood")
    .subject_to([10, 15], "<=", 450, "labor")
    .solve())""",
    },
    "Binary knapsack · OR-Learn": {
        "syntax": "orlearn",
        "description": "Select items to maximize value without exceeding capacity.",
        "source": "Adapted from OR-Learn README (MIT).",
        "text": """from orlearn import OR

model = (OR()
    .maximize([60, 100, 120], names=["item_1", "item_2", "item_3"])
    .subject_to([10, 20, 30], "<=", 50, "weight_limit")
    .as_binary()
    .solve())""",
    },
    "Production planning · AMPL": {
        "syntax": "ampl",
        "description": "The same production model in the supported AMPL-style syntax.",
        "source": "OR Studio example.",
        "text": """# Decision variables
var chairs >= 0, integer;
var tables >= 0, integer;

maximize profit: 45*chairs + 80*tables;

subject to wood: 5*chairs + 20*tables <= 400;
subject to labor: 10*chairs + 15*tables <= 450;

solve;""",
    },
    "Diet blend · AMPL": {
        "syntax": "ampl",
        "description": "Minimize blend cost while satisfying nutrition requirements.",
        "source": "OR Studio example.",
        "text": """var oats >= 0;
var soy >= 0;

minimize cost: 0.45*oats + 0.72*soy;

subject to protein: 8*oats + 20*soy >= 160;
subject to weight: oats + soy = 12;

solve;""",
    },
}


def get_example(name: str) -> Dict[str, str]:
    return EXAMPLES[name].copy()
