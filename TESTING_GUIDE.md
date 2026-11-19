# OR Studio — what to press, what to type, what you see

Open PowerShell in the project folder and start the app:

```
.\venv\Scripts\python.exe -m streamlit run app.py --server.port 8501
```

Open http://localhost:8501

Reload the page (F5) whenever a step says **reload**. That clears the session.

---

## 1. Header

You see: blue **OR** square, **OR Studio**, switch **Chat | Model Playground**, **No model loaded**, **Settings**, **Help**.

Press: **Model Playground**
You see: address `/?view=playground`

Press: **Chat**
You see: address `/?view=chat`

---

## 2. Settings and Help

Press: **Settings**
You see:
- Default solver dropdown (Auto, CBC, OSQP, GLPK, SCIP)
- Time limit (seconds) = `60`
- Installed solvers table: CBC, OSQP, GLPK, SCIP all **Available**

Put: Time limit `30`
Close the panel. Press **Settings** again.
You see: still `30`

Put: Time limit `60`
Close the panel.

Press: **Help**
You see: Formats, keyboard shortcuts, OR-Learn `0.1.0` commit `38355732`

Press: **Esc**
You see: panel closed

---

## 3. Empty Chat

You see: **What would you like to optimize?**
You see buttons: **Try a template**, **Load Problem**, **OR-Learn example**
You see the box at the bottom and the blue **Solve Problem** button.

Press: **Solve Problem** (box empty)
You see: **Type a problem or load one first.**

Press: **Try a template**
You see: Model Playground, Easy Start

Press: **Chat**

---

## 4. Solve the furniture model (OR-Learn)

Press: **OR-Learn example**
You see: code starting `from orlearn import OR`
You see: **Detected: OR-Learn**

Press: **Solve Problem**
You see:
- **Optimal**
- Objective **2,200**
- Solver **CBC**
- chairs = **24**
- tables = **14**

Press each expander on that card:

**Variables (2)** → chairs 24, tables 14

**Constraints (2)** → Wood and Labor, slack 0, binding True

**Charts** → two bar charts at 100%

**Interpretation** → bullets, “Generated offline…”

**Diagnostics** → OR-Learn cross-check **solve() → 2,200**

**Exports** → press each download:
- Result (JSON) → `"objective": 2200`
- Variables (CSV) → chairs 24, tables 14
- Constraints (CSV) → Wood, Labor
- Model (AMPL-style) → `.mod` file
- Model (LP format) → starts with `Maximize`

---

## 5. Load Problem → Examples (use each one in Chat)

Press: **Load Problem**
You see tabs: **Examples**, **Upload**, **MIPLIB**

For each row: press the category, press the title, press **Use in Chat**.

| Press category | Press this title | You see |
|---|---|---|
| Linear Programming | Quick start (OR-Learn README) | Optimal **9**, x1=1, x2=3 |
| Linear Programming | Production planning with sets · AMPL-style | Optimal **2,200**, make[chairs]=24, make[tables]=14 |
| Linear Programming | Diet blend · AMPL-style | Optimal **6.84**, oats≈6.667, soy≈5.333 |
| Knapsack | 0-1 knapsack (OR-Learn README) | Optimal **220** |
| Knapsack | Pack a 5 kg bag · AMPL-style | Optimal **700**, Laptop and Camera |
| Transportation | Transportation (OR-Learn README) | Optimal **4,000** |
| Transportation | Warehouses to stores · AMPL-style | Optimal **2,280** |
| Assignment | Workers to tasks (OR-Learn README) | Optimal **13** |
| Assignment | Workers to tasks · AMPL-style | Optimal **13** |
| Scheduling | Shortest route (OR-Learn README, network) | Value **10**, path A → C → B → D → E, no Open in Playground |
| Integer Programming | Integer purchase plan · AMPL-style | Optimal **40**, large=5, small=0 |
| Scheduling | Jobs on machines (makespan) · AMPL-style | Optimal **5** |

Press: **Load Problem** → Knapsack → **Pack a 5 kg bag · AMPL-style** → **Open in Algebraic**
You see: Playground Algebraic, **Valid AMPL-style**

---

## 6. Paste AMPL in Chat

Reload. Stay on Chat.

Put in the box:

```
# Furniture production (AMPL-style)
var chairs >= 0;
var tables >= 0;
maximize profit: 45*chairs + 80*tables;
subject to wood:  5*chairs + 20*tables <= 400;
subject to labor: 10*chairs + 15*tables <= 450;
```

You see: **Detected: AMPL-style**

Press: **Solve Problem**
You see: Optimal **2,200**, chairs **24**, tables **14**

---

## 7. Wrong format, parse error, pick a format

Put the same AMPL text in the box.

Press Format dropdown → **OR-Learn**
Press: **Solve Problem**
You see: **Parse error** (not a result)

Press Format → **AMPL-style**
Press: **Solve Problem**
You see: Optimal **2,200**

Press Format → **Auto**

Reload.

Put: `maximize 3x + 2y subject to x + y <= 4`
Press: **Solve Problem**
You see: **Which format is this?**
Press: **Treat as AMPL-style**
You see: **Parse error** (this text is not valid AMPL)

Reload.

Put:

```
var x >= 0;
maximize z: 3*x*x;
subject to c: x <= 4;
```

Press: **Solve Problem**
You see: **Parse error**, Line **2**, “Nonlinear term”, caret `^`, “Nothing was sent to an AI provider.”
The box still has your text.

Change `3*x*x` to `3*x`
Press: **Solve Problem**
You see: Optimal **12**, x=**4**

---

## 8. Solver menu (same AMPL furniture model each time)

Put the AMPL furniture model. Change **Solver**, then press **Solve Problem**.

| Press Solver | You see Solver | You see Objective |
|---|---|---|
| CBC | CBC | 2,200 |
| OSQP | OSQP | 2,200 |
| GLPK | GLPK | 2,200 |
| SCIP | SCIP | 2,200 |
| Auto | CBC | 2,200 |

Press Solver → **OSQP**
Press: **Load Problem** → Integer Programming → **Integer purchase plan · AMPL-style** → **Use in Chat**
You see: **Not run**, “OSQP solves continuous problems only…”
Press: **Solve with Auto instead**
You see: Optimal **40**

Press Solver → **Auto**

---

## 9. Text stays in the box

Put: `maximize z: 3*x + 2*y;`
Do not solve.

Press Format → **AMPL-style**
You see: text still there

Press Solver → **SCIP**
You see: text still there

Press: **Load Problem**, then **Esc**
You see: text still there

Press: **Model Playground**, then **Chat**
You see: same text, Format AMPL-style, Solver SCIP

Clear the box. Press Format **Auto**, Solver **Auto**.

---

## 10. Upload (Load Problem → Upload)

Press: **Load Problem** → **Upload**
Press: **Browse files** (or drop the file)

Use files in `test_files/`. After each file, close the dialog if needed, then open Upload again.

**01_ampl_model.txt**
You see: Found an AMPL-style model. 2 variables · 2 constraints
Press: **Solve in Chat**
You see: Optimal **2,200**

**02_orlearn_model.txt**
You see: Found an OR-Learn model. 2 variables · 2 constraints

**03_ampl_model.docx**
You see: AMPL-style model. 2 variables · 2 constraints

**04_furniture.mps**
You see: MPS model imported.
Press: **Open in Live Editor**
Press: **Solve Model**
You see: Optimal **2,200**

**05_furniture.mps.gz**
You see: MPS model imported.

**06_plan.csv**
You see: document, table preview, Extracted text
Press: **Put text in the composer** (optional) then clear the box

**07_plan.xlsx**
You see: sheet **Products**, 2 rows

**08_brief.pdf**
You see: 1 page(s) of text extracted.

**09_description.txt**
You see: Extracted text (not an error)

**10_legacy_word.doc**
You see: Extracted text

**11_legacy_excel.xls**
You see: Extracted text

First load **04_furniture.mps** → **Open in Live Editor** (model stays loaded).
Then Upload **12_corrupt.mps.gz**
You see: error, not a valid gzip archive, **Your active model is unchanged.**
Close dialog. Top bar still shows the furniture model.

**13_not_mps.gz**
You see: Only .mps.gz archives are supported.

**14_empty.txt**
You see: The file is empty.

**15_bad_ampl.txt**
You see: looks like AMPL-style but did not parse: Nonlinear term

---

## 11. MIPLIB (needs internet)

Press: **Load Problem** → **MIPLIB** → **By name**

Put Instance name: `flugpl`
Press: **Load**
You see: Loading… then **Model loaded**, **flugpl**, 18 variables

Press: **Solve**
You see: Optimal **1,201,500**

Press: **Solve** again
You see: **From cache**, Time **cached**

Press: **Re-solve (ignore cache)**
You see: Optimal **1,201,500** without From cache

Press: **Load Problem** → MIPLIB → **Browse**
Put Search: `neos`
You see: match list and a Load button

Press: **Cached**
You see: downloaded **flugpl**

Tick: **I understand cached data will be deleted**
Press: **Clear solution cache**
You see: Solution cache cleared.

Press: **Delete downloaded files**
You see: Deleted N file(s).

Press: **By name**
Put: `doesnotexist123`
Press: **Load**
You see: **Load failed**, Retry button, active model unchanged

---

## 12. Time limit and Cancel

Press: **Settings**
Put Time limit: `5`
Close Settings.

Press: **Load Problem** → MIPLIB → By name
Put: `markshare_4_0`
Press: **Load**
You see: 34 variables
Press: **Solve**
Wait ~5–7 seconds.
You see: **Feasible (time limit)** (not Optimal). Objective is a number (often 8; it can differ).

Press: **Settings**
Put Time limit: `120`
Press Solver → **SCIP**
Close Settings.

Press: **Solve** on markshare
While it runs, press: **Cancel solve**
You see: Cancellation requested. Run stops.

Press Solver → **CBC**
Press: **Solve**
You see: no Cancel button. Text says it stops at the time limit.

Press: **Settings**
Put Time limit: `60`
Press Solver → **Auto**

---

## 13. Easy Start (six templates)

Press: **Model Playground** → **Easy Start**

For each card: press **Select**, then press **Solve Template**.

| Press Select on | You see Objective | You see decisions |
|---|---|---|
| Linear program | **2,200** | chairs 24, tables 14 |
| Integer program | **40** | large 5 |
| Transportation | **2,280** | ship[w1,s1] 80, ship[w1,s3] 20, ship[w2,s4] 110, ship[w3,s2] 120, ship[w3,s3] 70 |
| Assignment | **13** | Alice→t2, Bob→t1, Carol→t3, David→t4 |
| Knapsack | **700** | Laptop, Camera |
| Scheduling | **5** | makespan 5 |

Press **Select** on Linear program again.
You see: its **2,200** result still there.

Press Linear program **Select**
Press: **Edit in Live Editor**
You see: Live Editor, Constraints · 2, wood RHS **400**

In Wood **Right-hand side**, put `300`, press Tab
You see: **Unsolved edits**

Press: **Easy Start**
Press Knapsack **Select**
Press: **Edit in Live Editor**
You see: **Replace the model in the editor?**

Press: **Keep Editing**
You see: Live Editor, wood still **300**

Press Easy Start → Knapsack **Select** → **Edit in Live Editor**
Press: **Load Template**
You see: Knapsack in the editor

Press **Models** in the header
You see: the Linear program with the 300 edit still listed

---

## 14. Algebraic

Press: **Model Playground** → **Algebraic**

Press: **Load Example** → **Production planning with sets · AMPL-style**
You see: **Valid AMPL-style**, 2 variables · 2 constraints
Press: **Solve Model**
You see: Optimal **2,200**

At the end of the source, add a new line:

```
subject to bad: make[chairs] * make[tables] <= 3;
```

Click outside the box.
You see: **Not valid**, Nonlinear term
**Solve Model** is greyed out.

Delete that extra line.
You see: Valid again.

Press: **Load Example** → **Production planning (OR-Learn README)**
You see: **Valid OR-Learn**
Press: **Solve Model**
You see: **2,200**

Press: **Open in Live Editor**
You see: Wood RHS **400**

Press: **Algebraic**
Put this in the source (replace everything):

```
A bakery makes bread and cake and wants more profit.
```

You see: this reads like a description, not a model

Replace the source with:

```
import json
print(json.dumps({"hello": 1}))
```

You see: **Only 'import orlearn' is allowed (found 'json').**

---

## 15. Live Editor — full pass

Reload.
Press: **Chat** → **OR-Learn example** → **Solve Problem**
You see: 2,200
Press: **Open in Playground**

You see:
- Objective: Maximize, `45 chairs + 80 tables`
- Wood: `5 chairs + 20 tables` ≤ **400**
- Labor: `10 chairs + 15 tables` ≤ **450**
- Variables: chairs, tables, lower **0**, upper **+∞**
- Button: **Solve Model**
- Result: **2,200**

### Change wood

Wood Right-hand side: put `300`, press Tab
You see: **Unsolved edits**, button **Solve Edited Model**

Press: **Solve Edited Model**
You see: Optimal **2,100**, chairs **36**, tables **6**
You see Compare: Baseline **2,200**, Edited **2,100**, Difference **−100**, Wood 400 → 300

### Sweep

Open **Sensitivity sweep**
Constraint: **Wood**
Put Right-hand-side values: `300, 350, 400`
Press: **Run sweep**
You see:

- 300 → Optimal **2,100**
- 350 → Optimal **2,150**
- 400 → Optimal **2,200**

Wood box still shows **300**.

Put values: `abc`
Press: **Run sweep**
You see: Sweep values must be numbers separated by commas.

### History and reset

Open **Run history**
You see: Baseline 2,200 and Edit 1 2,100

Press: **Reset to Baseline**
You see: Wood **400**, chip **Baseline**

In Run history press **Open this version** on Edit 1
You see: Wood **300**

Press: **Chat**
On the first 2,200 card press **Open in Playground**
You see: Wood **400**

### Minimize

Press: **Reset to Baseline**
Press objective: **minimize**
Press: **Solve Edited Model**
You see: Optimal **0**, chairs 0, tables 0

Press: **maximize**

### Math keypad

Press the objective `45 chairs + 80 tables`
You see: math field + **∑±**

Press: **∑±**
You see: Common, Variables (chairs, tables), More
≤ ≥ = ∑ √ are struck through on the objective.

Press: **Esc** (keypad closes)

Click the field, press Ctrl+A
Put: `50chairs+80tables`
Click outside.
Press: **Solve Edited Model**
You see: Optimal **2,320**, chairs 24, tables 14

Press: **Close editor**

### Bad math

Click the objective, Ctrl+A
Put: `chairs*tables`
You see: **Not applied** (product of variables)

Press: **Solve Edited Model**
You see: Not solved. No new result.

Ctrl+A, put: `45chairs+80tables`

Put: `sofas`
You see: **Not applied**, unknown variable

### Constraint relation

Press: **Reset to Baseline**
Wood Relation dropdown → **≥**
Press: **Solve Edited Model**
You see: Optimal **2,400**, chairs **0**, tables **30**

Wood Relation → **=**, RHS `400`
Press: **Solve Edited Model**
You see: **2,200**

Press: **Reset to Baseline**

### Add / rename / remove constraint

Press: **Add Constraint**
Put Name: `Storage`
Put expression: `chairs` then keypad **≤** then `20`
Press: **Add**
You see: Constraints · 3, Storage

Press: **Solve Edited Model**
You see: Optimal **2,100**, chairs **20**, tables **15**

Press: **Add Constraint**
Put: `chairs*tables<=5`
Press: **Add**
You see: **Not added**
Press: **Discard**

Press **⋮** on Storage
Put Rename: `Warehouse`, press Enter
You see: name Warehouse

Press **⋮** → **Remove constraint**
You see: Constraints · 2

### Variables

Press: **Reset to Baseline**

In the variables table, tables **Upper bound**: put `10`, Enter
Press: **Solve Edited Model**
You see: Optimal **2,150**, chairs **30**, tables **10**

Tables Upper bound: put `inf`, Enter
You see: **+∞**

Both Domain → **integer**
Press: **Solve Edited Model**
You see: **2,200**, header says **MIP**

Name `chairs` → `stools`, Enter
You see: stools in objective and constraints
Rename back to `chairs`

Click **+** at the bottom of the table
Put Name: `benches`
You see: new variable, Used in 0

Tick the **chairs** row, press Delete
You see: Remove **chairs**? coefficient 45, Wood (5), Labor (10)

Press: **Keep it**
You see: chairs still there

Delete chairs again. Press: **Remove variable**
Press: **Solve Edited Model**
You see: Optimal **1,600**, tables **20**

Try to delete **tables** (last in objective)
You see: Remove variable **disabled**

Press: **Reset to Baseline**
You see: chairs is back

Press: **Preview Math**
You see: full model as equations
Press: **Hide Math**
You see: box gone

---

## 16. Plain English (no working AI key)

Reload. Chat.

Put:

```
A bakery makes bread and cake. Bread earns 3 and cake earns 5. We have 40 hours of oven time.
```

You see: **Detected: Natural Language**
Press: **Solve Problem**
You see: **AI credentials required** (or HTTP **429** if a key is set but has no credits)
The text stays in the box.

Press: **Switch format to AMPL-style**
You see: Format is AMPL-style, text still there

---

## 17. Phone width

Press F12 → device toolbar → width **390**

Chat: no sideways scroll. Top bar still works.

Live Editor: each constraint is a card. Keypad keys wrap.

Width **768**: Algebraic stacks source above preview.

Width **1440**: Chat centered.

Press Tab around the page.
You see: blue outline on the focused control.

Press Esc on Load Problem / Help / keypad → they close.

Reset zoom: Ctrl+0. Close device toolbar.

---

## 18. Command line

In the project folder:

```
.\venv\Scripts\python.exe cli.py solvers
```
You see: five solvers, all Yes

```
.\venv\Scripts\python.exe cli.py examples
```
You see: example list

```
.\venv\Scripts\python.exe cli.py solve -f test_files\01_ampl_model.txt
```
You see: Optimal · objective **2,200** · chairs 24, tables 14

```
.\venv\Scripts\python.exe cli.py solve -f test_files\04_furniture.mps -s cvxpy_scip
```
You see: Optimal **2,200** via SCIP

```
.\venv\Scripts\python.exe cli.py validate test_files\02_orlearn_model.txt
```
You see: Valid ORLEARN model, 2 variables · 2 constraints

```
.\venv\Scripts\python.exe cli.py solve -f test_files\15_bad_ampl.txt
```
You see: Error: line 2 … Nonlinear term

---

## 19. Old app

```
.\venv\Scripts\python.exe -m streamlit run legacy_app.py --server.port 8503
```

Open http://localhost:8503
You see: old tabs — Solve Problem, Results, Visualization, Model Playground, MIPLIB Cache, Help — plus the sidebar.
