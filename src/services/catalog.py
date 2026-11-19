"""Built-in examples (all original categories) and Easy Start templates.

OR-Learn snippets are copied verbatim from the OR-Learn README
(https://github.com/harunpirim/orlearn, MIT license, commit 38355732).
Natural-language examples are the original OR Studio sidebar examples.
"""

from __future__ import annotations

from typing import Dict, List

ORLEARN_ATTRIBUTION = "OR-Learn README · github.com/harunpirim/orlearn @ 3835573 (MIT)"

ORLEARN_LP = '''from orlearn import OR

# Production planning: maximize profit
result = (OR()
    .maximize([45, 80], names=['chairs', 'tables'])
    .subject_to([5, 20], "<=", 400, "Wood")    # Wood constraint
    .subject_to([10, 15], "<=", 450, "Labor")  # Labor constraint
    .solve())

print(f"Make {result.solution['chairs']:.0f} chairs")
print(f"Make {result.solution['tables']:.0f} tables")
print(f"Profit: ${result.value:.0f}")

# Visualize the feasible region (2D problems only)
result.visualize()
'''

ORLEARN_QUICKSTART = '''from orlearn import OR

# Define → Constrain → Solve
result = (OR()
    .maximize([3, 2])
    .subject_to([1, 1], "<=", 4)
    .subject_to([2, 1], "<=", 5)
    .solve())

print(result)
'''

ORLEARN_KNAPSACK = '''from orlearn import OR

# 0-1 Knapsack: select items to maximize value
result = (OR()
    .maximize([60, 100, 120])       # Item values
    .subject_to([10, 20, 30], "<=", 50)  # Weight limit
    .as_binary()
    .solve())

print(result)
'''

ORLEARN_TRANSPORT = '''from orlearn import OR

# Minimize shipping costs
result = (OR()
    .transport(supply=[300, 400], demand=[250, 350, 100])
    .costs([
        [8, 6, 10],
        [9, 4, 5]
    ])
    .solve())

print(result)
# Shows optimal shipping plan with costs

# Visualize as network flow
result.visualize()
'''

ORLEARN_ASSIGN = '''from orlearn import assign

# Assign workers to tasks (minimize time)
costs = [
    [9, 2, 7, 8],
    [6, 4, 3, 7],
    [5, 8, 1, 8],
    [7, 6, 9, 4]
]

result = assign(costs, names=['Alice', 'Bob', 'Carol', 'David'])
print(result)

# Visualize as bipartite network
result.visualize()
'''

ORLEARN_SHORTEST_PATH = '''from orlearn import OR

# Find shortest route
result = (OR()
    .network([
        ('A', 'B', 4), ('A', 'C', 2),
        ('B', 'C', 1), ('B', 'D', 5),
        ('C', 'D', 8), ('D', 'E', 2)
    ])
    .shortest_path('A', 'E'))

print(f"Path: {' → '.join(result.solution['path'])}")
print(f"Distance: {result.value}")
'''

AMPL_PRODUCTION = """# Production planning: chairs and tables
var chairs >= 0;
var tables >= 0;

maximize profit: 45*chairs + 80*tables;

subject to wood:  5*chairs + 20*tables <= 400;
subject to labor: 10*chairs + 15*tables <= 450;
"""

AMPL_PRODUCTION_INDEXED = """# Same model with sets, parameters and a summation
set PRODUCTS := chairs tables;
set RESOURCES := wood labor;

param profit{PRODUCTS} := chairs 45  tables 80;
param capacity{RESOURCES} := wood 400  labor 450;
param use{RESOURCES, PRODUCTS}:  chairs  tables :=
  wood                            5      20
  labor                          10      15;

var make{PRODUCTS} >= 0;

maximize total_profit: sum{p in PRODUCTS} profit[p] * make[p];

subject to limit{r in RESOURCES}:
  sum{p in PRODUCTS} use[r, p] * make[p] <= capacity[r];
"""

AMPL_INTEGER = """# Integer purchase plan: small and large units
var small >= 0, integer;
var large >= 0, integer;

maximize value: 5*small + 8*large;

subject to units:  small + large <= 6;
subject to budget: 5*small + 9*large <= 45;
"""

AMPL_TRANSPORT = """# Ship from 3 warehouses to 4 stores at minimum cost
set W := w1 w2 w3;
set S := s1 s2 s3 s4;

param supply{W} := [100, 150, 200];
param demand{S} := [80, 120, 90, 110];
param cost{W, S} := [[5, 8, 6, 7],
                     [6, 7, 9, 5],
                     [8, 6, 7, 9]];

var ship{W, S} >= 0;

minimize total_cost: sum{w in W, s in S} cost[w, s] * ship[w, s];

subject to capacity{w in W}: sum{s in S} ship[w, s] <= supply[w];
subject to need{s in S}:     sum{w in W} ship[w, s] >= demand[s];
"""

AMPL_ASSIGNMENT = """# Assign 4 workers to 4 tasks at minimum cost
set WORKERS := Alice Bob Carol David;
set TASKS := t1 t2 t3 t4;

param cost{WORKERS, TASKS}:  t1 t2 t3 t4 :=
  Alice                       9  2  7  8
  Bob                         6  4  3  7
  Carol                       5  8  1  8
  David                       7  6  9  4;

var assign{WORKERS, TASKS} binary;

minimize total_cost: sum{w in WORKERS, t in TASKS} cost[w, t] * assign[w, t];

subject to one_task{w in WORKERS}:   sum{t in TASKS} assign[w, t] = 1;
subject to one_worker{t in TASKS}:   sum{w in WORKERS} assign[w, t] = 1;
"""

AMPL_KNAPSACK = """# Pack the most valuable items into a 5 kg bag
set ITEMS := Laptop Camera Books Clothes;

param value{ITEMS}  := Laptop 500  Camera 200  Books 100  Clothes 150;
param weight{ITEMS} := Laptop 3    Camera 1    Books 2    Clothes 2;
param capacity := 5;

var take{ITEMS} binary;

maximize packed_value: sum{i in ITEMS} value[i] * take[i];

subject to bag: sum{i in ITEMS} weight[i] * take[i] <= capacity;
"""

AMPL_SCHEDULING = """# Schedule 4 jobs on 2 machines to minimize the makespan
set JOBS := j1 j2 j3 j4;
set MACHINES := m1 m2;

param time{JOBS, MACHINES}:  m1 m2 :=
  j1                          3  4
  j2                          5  2
  j3                          2  6
  j4                          4  3;

var run_on{JOBS, MACHINES} binary;
var makespan >= 0;

minimize finish: makespan;

subject to each_job{j in JOBS}: sum{m in MACHINES} run_on[j, m] = 1;
subject to load{m in MACHINES}:
  sum{j in JOBS} time[j, m] * run_on[j, m] <= makespan;
"""

AMPL_DIET = """# Blend oats and soy at minimum cost
var oats >= 0;
var soy >= 0;

minimize cost: 0.45*oats + 0.72*soy;

subject to protein: 8*oats + 20*soy >= 160;
subject to weight:  oats + soy = 12;
"""

NL = {
    "lp": (
        "A furniture company makes tables (profit $50) and chairs "
        "(profit $30). Each table needs 3 hours labor and 1 unit "
        "material. Each chair needs 2 hours labor and 1 unit material. "
        "Total labor available: 240 hours. Total material available: "
        "100 units. How many of each should be produced to maximize profit?"
    ),
    "ip": (
        "A delivery company has 5 packages to assign to 3 trucks. "
        "Each truck can carry at most 100 kg. Package weights: "
        "[30, 45, 20, 55, 40]. Package values: [10, 15, 8, 20, 12]. "
        "Maximize total value delivered while respecting truck capacity."
    ),
    "transportation": (
        "Minimize shipping costs from 3 warehouses to 4 stores. "
        "Warehouse capacities: [100, 150, 200]. "
        "Store demands: [80, 120, 90, 110]. "
        "Cost per unit shipped (rows=warehouses, cols=stores): "
        "[[5,8,6,7],[6,7,9,5],[8,6,7,9]]"
    ),
    "assignment": (
        "Assign 4 workers to 4 tasks to minimize total cost. "
        "Cost matrix (rows=workers, cols=tasks): "
        "[[9,2,7,8],[6,4,3,7],[5,8,1,8],[7,6,9,4]]"
    ),
    "scheduling": (
        "Schedule 4 jobs on 2 machines. Job processing times on "
        "machine 1: [3,5,2,4]. On machine 2: [4,2,6,3]. "
        "Minimize total completion time."
    ),
    "knapsack": (
        "I have a 5 kg bag. A laptop is worth 500 and weighs 3 kg, a camera "
        "is worth 200 and weighs 1 kg, books are worth 100 and weigh 2 kg, and "
        "clothes are worth 150 and weigh 2 kg. Which items should I pack to "
        "maximize value?"
    ),
}

CATEGORIES = ["Linear Programming", "Integer Programming", "Transportation", "Assignment", "Scheduling", "Knapsack"]

EXAMPLES: List[Dict[str, str]] = [
    {"id": "orl-lp", "category": "Linear Programming", "title": "Production planning (OR-Learn README)", "format": "orlearn", "text": ORLEARN_LP, "source": ORLEARN_ATTRIBUTION, "expected": "Objective 2200 · chairs 24, tables 14"},
    {"id": "orl-quick", "category": "Linear Programming", "title": "Quick start (OR-Learn README)", "format": "orlearn", "text": ORLEARN_QUICKSTART, "source": ORLEARN_ATTRIBUTION, "expected": "Objective 9 (the README comment says 11; the true optimum is 9)"},
    {"id": "ampl-lp", "category": "Linear Programming", "title": "Production planning · AMPL-style", "format": "ampl", "text": AMPL_PRODUCTION, "source": "OR Studio", "expected": "Objective 2200"},
    {"id": "ampl-lp-indexed", "category": "Linear Programming", "title": "Production planning with sets · AMPL-style", "format": "ampl", "text": AMPL_PRODUCTION_INDEXED, "source": "OR Studio", "expected": "Objective 2200"},
    {"id": "ampl-diet", "category": "Linear Programming", "title": "Diet blend · AMPL-style", "format": "ampl", "text": AMPL_DIET, "source": "OR Studio", "expected": ""},
    {"id": "nl-lp", "category": "Linear Programming", "title": "Furniture production (description)", "format": "natural", "text": NL["lp"], "source": "OR Studio", "expected": "Needs an AI provider"},
    {"id": "ampl-ip", "category": "Integer Programming", "title": "Integer purchase plan · AMPL-style", "format": "ampl", "text": AMPL_INTEGER, "source": "OR Studio", "expected": "Objective 40"},
    {"id": "nl-ip", "category": "Integer Programming", "title": "Package delivery (description)", "format": "natural", "text": NL["ip"], "source": "OR Studio", "expected": "Needs an AI provider"},
    {"id": "orl-tp", "category": "Transportation", "title": "Transportation (OR-Learn README)", "format": "orlearn", "text": ORLEARN_TRANSPORT, "source": ORLEARN_ATTRIBUTION, "expected": "Minimum cost 4000"},
    {"id": "ampl-tp", "category": "Transportation", "title": "Warehouses to stores · AMPL-style", "format": "ampl", "text": AMPL_TRANSPORT, "source": "OR Studio", "expected": ""},
    {"id": "nl-tp", "category": "Transportation", "title": "Warehouses to stores (description)", "format": "natural", "text": NL["transportation"], "source": "OR Studio", "expected": "Needs an AI provider"},
    {"id": "orl-assign", "category": "Assignment", "title": "Workers to tasks (OR-Learn README)", "format": "orlearn", "text": ORLEARN_ASSIGN, "source": ORLEARN_ATTRIBUTION, "expected": "Total cost 13"},
    {"id": "ampl-assign", "category": "Assignment", "title": "Workers to tasks · AMPL-style", "format": "ampl", "text": AMPL_ASSIGNMENT, "source": "OR Studio", "expected": "Total cost 13"},
    {"id": "nl-assign", "category": "Assignment", "title": "Workers to tasks (description)", "format": "natural", "text": NL["assignment"], "source": "OR Studio", "expected": "Needs an AI provider"},
    {"id": "ampl-sched", "category": "Scheduling", "title": "Jobs on machines (makespan) · AMPL-style", "format": "ampl", "text": AMPL_SCHEDULING, "source": "OR Studio", "expected": "Makespan 5"},
    {"id": "orl-path", "category": "Scheduling", "title": "Shortest route (OR-Learn README, network)", "format": "orlearn", "text": ORLEARN_SHORTEST_PATH, "source": ORLEARN_ATTRIBUTION, "expected": "Distance 10 via A → C → B → D → E"},
    {"id": "nl-sched", "category": "Scheduling", "title": "Jobs on two machines (description)", "format": "natural", "text": NL["scheduling"], "source": "OR Studio", "expected": "Needs an AI provider"},
    {"id": "orl-knap", "category": "Knapsack", "title": "0-1 knapsack (OR-Learn README)", "format": "orlearn", "text": ORLEARN_KNAPSACK, "source": ORLEARN_ATTRIBUTION, "expected": "Objective 220"},
    {"id": "ampl-knap", "category": "Knapsack", "title": "Pack a 5 kg bag · AMPL-style", "format": "ampl", "text": AMPL_KNAPSACK, "source": "OR Studio", "expected": "Value 700"},
    {"id": "nl-knap", "category": "Knapsack", "title": "Pack a 5 kg bag (description)", "format": "natural", "text": NL["knapsack"], "source": "OR Studio", "expected": "Needs an AI provider"},
]

TEMPLATES: List[Dict[str, str]] = [
    {"key": "lp", "title": "Linear program", "subtitle": "Production planning", "icon": ":material/show_chart:", "text": AMPL_PRODUCTION},
    {"key": "ip", "title": "Integer program", "subtitle": "Whole-unit purchase plan", "icon": ":material/pin:", "text": AMPL_INTEGER},
    {"key": "transportation", "title": "Transportation", "subtitle": "Warehouses → stores", "icon": ":material/local_shipping:", "text": AMPL_TRANSPORT},
    {"key": "assignment", "title": "Assignment", "subtitle": "Workers ↔ tasks", "icon": ":material/assignment_ind:", "text": AMPL_ASSIGNMENT},
    {"key": "knapsack", "title": "Knapsack", "subtitle": "Pack the best items", "icon": ":material/backpack:", "text": AMPL_KNAPSACK},
    {"key": "scheduling", "title": "Scheduling", "subtitle": "Jobs on machines", "icon": ":material/calendar_month:", "text": AMPL_SCHEDULING},
]

ALGEBRAIC_EXAMPLES: List[Dict[str, str]] = [e for e in EXAMPLES if e["format"] in ("orlearn", "ampl")]


def example(example_id: str) -> Dict[str, str]:
    return next(e for e in EXAMPLES if e["id"] == example_id)


def template(key: str) -> Dict[str, str]:
    return next(t for t in TEMPLATES if t["key"] == key)
