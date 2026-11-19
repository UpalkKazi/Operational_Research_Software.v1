# AMPL-style subset

OR Studio reads a linear subset of AMPL in Chat (format **AMPL-style** or
**Auto**), in Model Playground → **Algebraic**, in uploaded `.txt`/`.docx`
files, and in the CLI. The parser is a tokenizer plus a recursive-descent parser
(`src/modeling/ampl_parser.py`). Nothing is evaluated as Python. Every error
gives the line and column of the problem, and a failed parse is never passed to
an AI provider.

## Supported

| Construct | Example |
|---|---|
| Set, listed | `set P := chairs tables;` or `set P := {chairs, tables};` |
| Set, range | `set T := 1..5;` |
| Scalar param | `param budget := 400;` |
| Indexed param, pairs | `param c{P} := chairs 45 tables 80;` |
| Indexed param, list | `param c{P} := [45, 80];` |
| 2-D param, nested list | `param a{R,P} := [[5, 20], [10, 15]];` |
| 2-D param, table | `param a{R,P}: chairs tables := wood 5 20 labor 10 15;` |
| Param default | `param d{P} default 0;` |
| Data section | `data; set P := a b; param c := a 1 b 2;` |
| Scalar variable | `var x;` `var x >= 0, <= 10;` |
| Indexed variable | `var x{P} >= 0, <= u[p], integer;` `var y{I,J} binary;` |
| Objective | `maximize profit: sum{p in P} c[p]*x[p];` |
| Constraint | `subject to cap: x + y <= 4;` or `s.t. cap: ...;` |
| Indexed constraint | `s.t. supply{i in I}: sum{j in J} x[i,j] <= s[i];` |
| Ranged constraint | `s.t. band: 1 <= x + y <= 4;` (becomes two rows) |
| Sums over several sets | `sum{i in I, j in J} c[i,j]*x[i,j]` |
| Arithmetic on constants | `+ - * /` and `^` when both sides are constants; division by a constant |
| Unicode operators | `≤ ≥ − × · ∑` |
| Ignored statements | `solve; end; display ...; option ...;` |

Bounds follow AMPL: a variable with no bound is **free** (−∞ to +∞), not
non-negative. `binary` means integer with bounds 0 and 1. The Live Editor shows
an unbounded side as ∞, which is different from 0.

## Rejected, with a location

| Construct | Message |
|---|---|
| Product or power of variables, `x*y`, `x^2` | Nonlinear term |
| Division by a variable, `1/x` | Nonlinear term: division by a variable |
| `prod`, `abs`, `max`, `min`, `if … then … else` | `'…' is not supported in a linear model` |
| Conditional indexing `{i in I: i > 1}` | Conditional indexing is not supported |
| Computed params `param a := 2*3;` | Expected `;` to end the parameter |
| Undeclared names | `'y' is not a declared variable, parameter, or index` |
| Strict inequalities `<`, `>` | Strict inequality is not allowed in linear programs |
| Other AMPL statements (`let`, `fix`, `problem`, …) | Unsupported statement |

## What you see after parsing

Algebraic → preview shows:

- the expanded model in mathematical notation, with constraint names,
- indexed variables as a table (for example `x[wood,chairs]`),
- each parameter as a matrix, and each set with its members,
- the line and column of the first error, with a caret under the problem.

**Solve Model** and **Open in Live Editor** act on the exact source revision
shown in the preview (a source hash guards this). If you edit the source after
validating, those buttons wait until the new text has been validated.

## OR-Learn input

OR-Learn chains (`OR().maximize([...]).subject_to(...).solve()`) are read by an
AST-based parser (`src/modeling/orlearn_parser.py`). It accepts only
`from orlearn import …` imports, literal assignments, and the documented chain
methods. It is then built through the real OR-Learn library, pinned at commit
`38355732feae2c6cc776d58b6f01491bbce78124`, via
`src/modeling/orlearn_adapter.py`. Diagnostics show the API calls that were
made. `print(...)` lines that only show values or result methods are skipped,
not run. Any other call, attribute access or import is rejected.
