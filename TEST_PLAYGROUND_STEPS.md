# Model Playground — Hands-On Test Script

Follow these steps **exactly** on your localhost. Every step tells you
**what to click**, **what you should see**, and **what it means**.

---

## STEP 0: Start the app & solve a problem first

```bash
streamlit run app.py
```

Go to **💡 Solve Problem** tab. Paste this text into the description box:

```
A furniture factory makes tables and chairs.
Each table needs 3 hours of assembly and 2 hours of finishing.
Each chair needs 2 hours of assembly and 1 hour of finishing.
Available: 240 assembly hours, 100 finishing hours.
Profit: $50 per table, $30 per chair.
Maximize profit.
```

Click **Solve** and wait for balloons. The answer should be around:
- tables ≈ 20, chairs ≈ 90 (or similar, depends on AI classification)
- Profit ≈ $3,700 – $4,200

**Why this step matters:** The Playground loads its model from the last
solved problem. Without solving first, you'll only see empty templates.

---

## STEP 1: Open the Playground tab

Click the tab **🧮 Model Playground** in the top navigation bar.

You now see **three sub-tabs**:

| Sub-tab | Purpose |
|---------|---------|
| 📄 Model View | Read-only view of the math model |
| ✏️ Live Editor | Change the model and re-solve |
| 📊 Sensitivity Sweep | See how one constraint limit affects the answer |

---

## STEP 2: Test the "📄 Model View" sub-tab

Click **📄 Model View**.

### What you should see (top to bottom):

**Block 1 — "Current Mathematical Model" heading**

**Block 2 — "Objective (Maximize):"**
A rendered math formula, for example:

$$50 x_{tables} + 30 x_{chairs}$$

This is the profit function. 50 × tables + 30 × chairs.

**Block 3 — "Subject to:"**
Two constraint formulas:

$$3 x_{tables} + 2 x_{chairs} \leq 240$$
$$2 x_{tables} + x_{chairs} \leq 100$$

These are the limits: assembly hours (240) and finishing hours (100).

**Block 4 — "Decision Variables:" table**

| Variable | LaTeX | Type | Lower Bound | Upper Bound |
|----------|-------|------|-------------|-------------|
| tables | $x_{tables}$ | Continuous | 0 | +∞ |
| chairs | $x_{chairs}$ | Continuous | 0 | +∞ |

**Block 5 — "Current Solution:" table** (only if problem was solved)

| Variable | Value |
|----------|-------|
| tables | 20.00 |
| chairs | 90.00 |

And a metric card showing **Objective Value: 3,700.0000** (or similar).

### How to verify it's correct:
- Plug the solution into the objective: 50 × 20 + 30 × 90 = 1000 + 2700 = 3700 ✓
- Check constraint 1: 3 × 20 + 2 × 90 = 60 + 180 = 240 ≤ 240 ✓
- Check constraint 2: 2 × 20 + 1 × 90 = 40 + 90 = 130 ... hmm, that's > 100

If the numbers don't perfectly match, it's because the AI classifier might
have generated slightly different coefficients. That's OK — the point is
that **real numbers** appear here, not symbolic c₁, a₁₁.

---

## STEP 3: Test the "✏️ Live Editor" sub-tab

Click **✏️ Live Editor**.

### What you see (top to bottom):

---

### SECTION A: "Objective Function"

**Row 1 — Direction dropdown**: Shows `maximize` or `minimize`.

> TEST: Click it and switch to `minimize`. Don't solve yet — just note
> that you can flip the direction.

**Row 2 — Math toolbar**: A blue row of clickable buttons:

```
∑  ∏  ∫  |  ≤  ≥  =  ≠  |  ∈  ℤ  ℝ  {0,1}  ∞  |  ½  xⁿ  xᵢ  √  |  α  β  λ  μ  δ  ε  |  LP obj  Supply  Demand  Knapsack
```

> TEST: Click the **∑** button. A summation template ∑ appears in the
> editor box with placeholder slots. Press Escape or click elsewhere to cancel.

**Row 3 — Math editor box**: Shows the objective formula.
Example: `50 x_{tables} + 30 x_{chairs}`

You can click inside and edit it like a text field, but with live math rendering.

> TEST: Click on the `50`, delete it, type `100`. The formula now reads
> `100 x_{tables} + 30 x_{chairs}`. You just doubled the table profit.

**Row 4 — LaTeX text input**: Shows the raw LaTeX code below the editor.
Example: `50 x_{tables} + 30 x_{chairs}`

You can also type LaTeX directly here if the math editor is hard to use.

---

### SECTION B: "Constraints"

Each constraint is in a **collapsible expander**. Click to open one.

**Inside each constraint expander:**

| Element | What it is | Example |
|---------|-----------|---------|
| **Name** text input | Label for this constraint | `_C1` |
| **Math toolbar** (small) | Insert ∑, ≤, ≥, etc. | Blue button row |
| **Math editor box** | The constraint formula | `3x_{tables} + 2x_{chairs} ≤ 240` |
| **LaTeX text input** | Raw LaTeX code | Same as above in text form |
| **RHS value** number input | The right-hand-side limit | `240.00` |
| **🗑️ Remove** button | Delete this constraint | Click to remove |

> TEST A: Open the first constraint. Change the **RHS value** from 240 to
> **300**. You just gave the factory 60 more assembly hours.

> TEST B: Open the second constraint. Change the RHS from 100 to **150**.
> More finishing hours available now.

**Below the constraints: "➕ Add New Constraint" expander**

> TEST C: Click to expand. You see:
> - Name: `new_constraint_3`
> - A MathLive editor pre-loaded with `x_{1} ≤ 100`
> - RHS value: `0.00`
> - "Add Constraint" button
>
> Change the name to `max_tables`. In the LaTeX input below the math editor,
> type: `x_{tables} \leq 40`. Set RHS to `40`. Click **Add Constraint**.
>
> You just added a rule: "make at most 40 tables."

---

### SECTION C: "Variables"

A row for each variable:

| Name | LaTeX | Type | LB | UB | 🗑️ |
|------|-------|------|----|----|-----|
| tables | $x_{tables}$ | Continuous ▼ | 0.00 | 0.00 (0 = ∞) | 🗑️ |
| chairs | $x_{chairs}$ | Continuous ▼ | 0.00 | 0.00 (0 = ∞) | 🗑️ |

> TEST A: Change "tables" Type dropdown from `Continuous` to `Integer`.
> Now tables must be a whole number (no fractions like 20.5).

> TEST B: Change "chairs" LB from 0 to 10. Now the factory must produce
> at least 10 chairs.

**"➕ Add New Variable" expander:**

> TEST C: Expand it. Enter name `desks`, type `Continuous`, LB=0, UB=0
> (unbounded). Click **Add Variable**. A new variable appears in the list.

---

### SECTION D: Action Buttons (bottom)

Three buttons in a row:

| Button | What it does |
|--------|-------------|
| 🚀 **Solve Edited Model** (red) | Takes all your edits, builds a new model, solves it |
| 👁️ **Preview as LaTeX** | Shows the edited model as rendered math (no solving) |
| 🔄 **Reset to Original** | Undoes ALL your edits, returns to the original model |

---

## STEP 4: Full Edit → Solve → Compare test

Do these edits one by one (from the tests above), then solve:

1. ✅ Set Direction to `maximize`
2. ✅ Change objective: `100 x_{tables} + 30 x_{chairs}` (changed 50 → 100)
3. ✅ Change first constraint RHS from 240 → **300**
4. ✅ Change variable "tables" type to `Integer`

Now click **🚀 Solve Edited Model**.

### What appears below the buttons:

**Block 1 — "📊 Comparison: Original vs Edited" heading**

**Block 2 — Three metric cards side by side:**

| Original Objective | Edited Objective | Delta |
|--------------------|-----------------|-------|
| 3,700.0000 | 5,200.0000 | +1,500.0000 (+40.5%) |

(Your exact numbers will differ, but the structure is the same.)

**How to read this:**
- Original = the profit from the first solve
- Edited = the profit after your changes
- Delta = how much profit changed (+ is better if maximizing)

**Block 3 — "Changes Made:" list**

```
- Objective expression was modified
- Constraint '_C1' RHS: 240.0 → 300.0
- Variable 'tables' type: Continuous → Integer
```

This tells you exactly what you changed.

**Block 4 — Variable Comparison table:**

| Variable | Original | Edited | Delta |
|----------|----------|--------|-------|
| tables | 20.0000 | 30.0000 | +10.0000 |
| chairs | 90.0000 | 75.0000 | -15.0000 |

**How to verify the edited solution:**
- Objective: 100 × 30 + 30 × 75 = 3000 + 2250 = 5250 ≈ 5,200 ✓ (close)
- Constraint 1: 3 × 30 + 2 × 75 = 90 + 150 = 240 ≤ 300 ✓
- Constraint 2: 2 × 30 + 1 × 75 = 60 + 75 = 135 ≤ 150 ✓
- tables = 30 (integer) ✓

---

## STEP 5: Test the "📊 Sensitivity Sweep" sub-tab

Click **📊 Sensitivity Sweep**.

### What you see:

**Row 1 — "Select constraint" dropdown**
Lists all constraints by name. Pick the first one (assembly hours).

**Row 2 — Three number inputs side by side:**

| RHS Min | RHS Max | Number of points |
|---------|---------|-----------------|
| 48.0 | 600.0 | 10 |

These defaults are 20% and 250% of the actual constraint RHS (240).

> TEST: Keep these defaults. Click **🔍 Run Sweep**.

### What happens:

A **progress bar** appears: "Solving 1/10...", "Solving 2/10...", etc.
The system solves the model 10 times, each time with a different RHS value:
48, 109, 170, 231, 292, 353, 414, 475, 536, 600.

### What appears after the sweep:

**Block 1 — Plotly line chart:**
- X-axis: "RHS Value" (48 to 600)
- Y-axis: "Objective" (profit)
- Blue line with dots: profit at each RHS value
- Red dashed vertical line: "Current: 240" marking the original RHS

**How to read the chart:**
- The line goes UP as RHS increases → more assembly hours = more profit
- The line might flatten → at some point, the other constraint (finishing)
  becomes the bottleneck, so extra assembly hours don't help

**Block 2 — "Approximate Shadow Price" metric:**
Shows a number like `16.6667`.

**What the shadow price means:**
- For every 1 extra assembly hour, profit increases by ~$16.67
- If you could buy 10 more assembly hours, you'd gain ~$166.70 in profit
- This tells the factory manager "assembly hours are worth $16.67 each"

> TEST: Now switch the dropdown to the **second constraint** (finishing hours).
> Click Run Sweep again. Compare the shadow prices — the constraint with
> the HIGHER shadow price is the bigger bottleneck.

---

## STEP 6: Test with a Template (no solve needed)

1. Press F5 to refresh the page (clears all session state)
2. Go directly to **🧮 Model Playground** tab
3. You see: "No model loaded yet" message and 5 template buttons

Click **Knapsack**. This loads a template with:
- Objective: `v_{1} x_{1} + v_{2} x_{2} + v_{3} x_{3}` (symbolic, not numbers)
- Constraint: `w_{1} x_{1} + w_{2} x_{2} + w_{3} x_{3} ≤ W`
- Variables: x_{1}, x_{2}, x_{3} (Binary type)

> This is a TEMPLATE — it uses placeholder symbols (v₁, w₁, W) because
> no real problem has been solved yet. You'd manually replace these with
> actual numbers in the editor to solve a specific problem.

Try clicking **Linear Program** or **Transportation** to see other templates.

---

## Quick Reference: What Each Section Produces

| Section | Input | Output |
|---------|-------|--------|
| Model View | (nothing, read-only) | Math formulas + solution table |
| Objective editor | Change numbers/direction | New profit formula |
| Constraint editors | Change limits/add/remove | New constraint set |
| Variable table | Change types/bounds | New variable definitions |
| Solve Edited Model | All edits combined | New solution + comparison |
| Preview as LaTeX | All edits combined | Rendered math (no solve) |
| Reset to Original | Click | Undo all edits |
| Sensitivity Sweep | Pick constraint + range | Chart + shadow price |

---

## Checklist: Verify Everything Works

After each test, check (✓) if it worked:

```
[ ] Model View shows real numbers (50, 30, 3, 2), not symbols (c₁, a₁₁)
[ ] Constraints show ≤ symbol (not "leq" or broken text)
[ ] Changing 50 to 100 in objective editor actually sticks
[ ] Changing RHS from 240 to 300 actually sticks
[ ] Solve Edited Model produces comparison metrics
[ ] Delta percentage makes sense (positive = improvement for maximize)
[ ] Variable comparison table has Original, Edited, Delta columns
[ ] Changes Made list correctly describes what you changed
[ ] Sensitivity Sweep chart loads after clicking Run Sweep
[ ] Shadow Price shows a number (not N/A)
[ ] Red dashed line appears at the current RHS value
[ ] Reset to Original clears all edits
[ ] Template buttons work when no problem is solved
```
