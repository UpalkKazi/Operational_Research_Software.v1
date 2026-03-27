# app.py — Line-by-Line Explanation with Realistic Examples

This document walks through every section of `app.py`, the main Streamlit web interface for the OR Assistant. Each section includes what the code does, why it matters, and a realistic example of what the user sees or experiences.

---

## Table of Contents

1. [Imports & Environment Setup (Lines 1–11)](#1-imports--environment-setup-lines-111)
2. [Module Imports with Fallback (Lines 13–20)](#2-module-imports-with-fallback-lines-1320)
3. [Page Configuration (Lines 22–28)](#3-page-configuration-lines-2228)
4. [Custom CSS Styling (Lines 30–43)](#4-custom-css-styling-lines-3043)
5. [Main Title (Lines 45–47)](#5-main-title-lines-4547)
6. [Sidebar — Settings & Examples (Lines 49–76)](#6-sidebar--settings--examples-lines-4976)
7. [Tabs Layout (Line 79)](#7-tabs-layout-line-79)
8. [Tab 1 — Solve Problem (Lines 81–142)](#8-tab-1--solve-problem-lines-81142)
9. [Tab 2 — Results (Lines 144–187)](#9-tab-2--results-lines-144187)
10. [Tab 3 — Visualizations (Lines 189–200)](#10-tab-3--visualizations-lines-189200)
11. [Tab 4 — Help (Lines 202–251)](#11-tab-4--help-lines-202251)
12. [Footer (Lines 253–255)](#12-footer-lines-253255)

---

## 1. Imports & Environment Setup (Lines 1–11)

```python
"""
OR Assistant - Main Streamlit Application
AI-Powered Operations Research Tool
"""

import streamlit as st
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()
```

### What it does

- **`import streamlit as st`** — Imports the Streamlit library, which is the web framework that turns this Python script into a full interactive web application. Every `st.___()` call renders a UI element in the browser.
- **`from dotenv import load_dotenv`** — Imports a helper that reads key-value pairs from a `.env` file and loads them into the process as environment variables.
- **`import os`** — Standard library for accessing environment variables (e.g., `os.getenv("ANTHROPIC_API_KEY")`).
- **`load_dotenv()`** — Actually reads the `.env` file at the project root. After this call, any code that does `os.getenv("ANTHROPIC_API_KEY")` will get the value you set in `.env`.

### Realistic Example

Your `.env` file contains:

```
AI_PROVIDER=anthropic
ANTHROPIC_API_KEY=sk-ant-api03-xxxxx...
```

After `load_dotenv()` runs, the app can do:

```python
provider = os.getenv("AI_PROVIDER")   # returns "anthropic"
api_key = os.getenv("ANTHROPIC_API_KEY")  # returns "sk-ant-api03-xxxxx..."
```

This keeps secrets out of the code itself.

---

## 2. Module Imports with Fallback (Lines 13–20)

```python
try:
    from src.agents.problem_classifier import ProblemClassifier
    from src.modeling.model_generator import ModelGenerator
    from src.solvers.solver_interface import SolverInterface
    from src.interpreters.result_interpreter import ResultInterpreter
except ImportError:
    st.warning("⚠️ Some modules are not yet implemented. See development guide.")
```

### What it does

Attempts to import four core project modules:

| Module | Role |
|---|---|
| `ProblemClassifier` | Takes a natural language problem and figures out what kind of OR problem it is (LP, IP, transportation, etc.) |
| `ModelGenerator` | Converts the classified problem into a mathematical model (decision variables, objective function, constraints) |
| `SolverInterface` | Sends the mathematical model to an optimization solver (PuLP, OR-Tools, CVXPY) and gets the solution |
| `ResultInterpreter` | Takes raw solver output and generates a human-readable explanation using AI |

The `try/except` block means: **if any of these modules haven't been implemented yet, the app still loads** — it just shows a yellow warning banner at the top instead of crashing.

### Realistic Example

When you first clone the repo and run the app, you'll likely see:

> ⚠️ Some modules are not yet implemented. See development guide.

This is because the files exist but the classes inside may not be fully coded yet. Once a student implements `ProblemClassifier` in `src/agents/problem_classifier.py`, that import starts working.

---

## 3. Page Configuration (Lines 22–28)

```python
st.set_page_config(
    page_title="OR Assistant",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded"
)
```

### What it does

Configures the browser tab and page layout. **This must be the first Streamlit command** (after imports).

| Parameter | Effect |
|---|---|
| `page_title="OR Assistant"` | The browser tab will say "OR Assistant" |
| `page_icon="🎯"` | The tab favicon shows a target emoji |
| `layout="wide"` | The app uses the full browser width instead of a narrow centered column |
| `initial_sidebar_state="expanded"` | The left sidebar is open by default when you first load the page |

### Realistic Example

When you open `http://localhost:8501`, the browser tab shows:

```
🎯 OR Assistant
```

And the page content stretches across the full screen width, with the sidebar already visible on the left.

---

## 4. Custom CSS Styling (Lines 30–43)

```python
st.markdown("""
<style>
    .main-header {
        font-size: 3rem;
        font-weight: bold;
        color: #1f77b4;
    }
    .sub-header {
        font-size: 1.2rem;
        color: #666;
    }
</style>
""", unsafe_allow_html=True)
```

### What it does

Injects raw HTML/CSS into the page. Streamlit normally sanitizes HTML for safety, but `unsafe_allow_html=True` allows it through.

This defines two CSS classes:
- **`.main-header`** — Large (3rem = ~48px), bold, blue text for the app title
- **`.sub-header`** — Medium (1.2rem = ~19px), gray text for the subtitle

### Realistic Example

Without this CSS, the title would look like any other text. With it, the title "🎯 OR Assistant" appears in large blue bold lettering, visually distinguishing it as the app header.

---

## 5. Main Title (Lines 45–47)

```python
st.markdown('<p class="main-header">🎯 OR Assistant</p>', unsafe_allow_html=True)
st.markdown('<p class="sub-header">AI-Powered Operations Research Solutions</p>', unsafe_allow_html=True)
```

### What it does

Renders the app title and subtitle using the CSS classes defined above.

### Realistic Example

At the top of the page the user sees:

> **🎯 OR Assistant** *(large, blue, bold)*
>
> AI-Powered Operations Research Solutions *(smaller, gray)*

---

## 6. Sidebar — Settings & Examples (Lines 49–76)

```python
with st.sidebar:
    st.header("⚙️ Settings")

    # Solver selection
    solver_type = st.selectbox(
        "Solver",
        ["PuLP", "OR-Tools", "CVXPY", "Auto-detect"],
        help="Select the optimization solver to use"
    )

    # Advanced options
    with st.expander("Advanced Options"):
        max_time = st.slider("Max Solution Time (seconds)", 10, 600, 300)
        show_formulation = st.checkbox("Show Mathematical Formulation", value=False)
        show_logs = st.checkbox("Show Solver Logs", value=False)

    st.divider()

    # Example problems
    st.header("📚 Example Problems")
    example_category = st.selectbox(
        "Category",
        ["Linear Programming", "Integer Programming", "Transportation", "Assignment", "Scheduling"]
    )

    if st.button("Load Example"):
        st.session_state.load_example = True
```

### What it does

Everything inside `with st.sidebar:` appears in the left sidebar panel.

**Solver Selection (`st.selectbox`)**
- Creates a dropdown with four choices. The selected value is stored in `solver_type`.
- The `help` parameter adds a small "?" icon with tooltip text.

**Advanced Options (`st.expander`)**
- Collapsible section. Clicking "Advanced Options" reveals:
  - **Slider** — User drags to set max solve time (default 300 seconds / 5 minutes)
  - **Checkbox** — Toggle whether to show the raw math formulation
  - **Checkbox** — Toggle whether to show solver debug logs

**Example Problems**
- A second dropdown to pick a category of sample problems.
- A "Load Example" button that sets a flag in `st.session_state` (Streamlit's per-session storage).

### Realistic Example

A student opens the app and sees the sidebar:

```
⚙️ Settings
┌──────────────────┐
│ Solver: [PuLP ▼] │  ← dropdown
└──────────────────┘
▶ Advanced Options    ← click to expand

─────────────────────
📚 Example Problems
┌──────────────────────────┐
│ Category: [Transportation ▼] │
└──────────────────────────┘
[ Load Example ]          ← button
```

If they select "OR-Tools" from the solver dropdown, then `solver_type` becomes `"OR-Tools"` and is used later when solving.

---

## 7. Tabs Layout (Line 79)

```python
tab1, tab2, tab3, tab4 = st.tabs(["💡 Solve Problem", "📊 Results", "📈 Visualization", "📖 Help"])
```

### What it does

Creates four horizontal tabs across the main content area. Each tab is a separate container. Only the active tab's content is visible at a time.

### Realistic Example

The user sees a tab bar:

```
[ 💡 Solve Problem ]  [ 📊 Results ]  [ 📈 Visualization ]  [ 📖 Help ]
```

Clicking any tab switches the view below it.

---

## 8. Tab 1 — Solve Problem (Lines 81–142)

This is the core interaction tab. Let's break it down:

### 8a. Problem Input (Lines 81–90)

```python
with tab1:
    st.header("Describe Your Problem")

    problem_description = st.text_area(
        "Enter problem description in natural language:",
        height=200,
        placeholder="Example: I need to minimize transportation costs between 3 warehouses and 5 stores...",
        help="Describe your optimization problem. Be specific about objectives, constraints, and data."
    )
```

Creates a large text box (200px tall) where the user types their problem in plain English. The `placeholder` text shows as gray hint text before the user starts typing.

**Realistic Example — What a user might type:**

```
I run a furniture company with two factories (Factory A and Factory B).
Factory A can produce up to 200 tables per week, Factory B up to 150.

I supply three retail stores:
- Store 1 needs 120 tables
- Store 2 needs 80 tables
- Store 3 needs 100 tables

Shipping costs per table:
- Factory A → Store 1: $5, Store 2: $8, Store 3: $6
- Factory B → Store 1: $7, Store 2: $4, Store 3: $9

Minimize total shipping cost while meeting all store demands.
```

### 8b. Action Buttons (Lines 92–98)

```python
col1, col2, col3 = st.columns([1, 1, 2])

with col1:
    solve_button = st.button("🚀 Solve Problem", type="primary", use_container_width=True)

with col2:
    clear_button = st.button("🗑️ Clear", use_container_width=True)
```

Creates a row of three columns (ratio 1:1:2). The first column gets a blue primary "Solve" button, the second gets a gray "Clear" button, and the third column is empty padding.

### 8c. Solve Pipeline (Lines 100–138)

```python
if solve_button and problem_description:
    with st.spinner("🤔 Understanding your problem..."):
        try:
            # Step 1: Classify problem
            st.info("**Step 1:** Classifying problem type...")
            st.success("✅ Problem classified as: Linear Programming")

            # Step 2: Generate model
            st.info("**Step 2:** Generating mathematical model...")
            st.success("✅ Model generated successfully")

            # Step 3: Solve
            st.info("**Step 3:** Solving with " + solver_type + "...")
            st.success("✅ Solution found!")

            # Step 4: Interpret
            st.info("**Step 4:** Interpreting results...")
            st.session_state.solution_ready = True
            st.balloons()

        except Exception as e:
            st.error(f"❌ Error: {str(e)}")
```

This is the **four-step pipeline** that runs when the user clicks "Solve":

| Step | What Happens (Once Implemented) | What User Sees Now (Placeholder) |
|---|---|---|
| **1. Classify** | AI reads the text and determines it's a Transportation problem | "✅ Problem classified as: Linear Programming" |
| **2. Model** | AI generates: minimize ΣΣ cᵢⱼxᵢⱼ subject to supply/demand constraints | "✅ Model generated successfully" |
| **3. Solve** | PuLP/OR-Tools finds optimal xᵢⱼ values | "✅ Solution found!" |
| **4. Interpret** | AI explains: "Ship 120 from Factory A to Store 1 at $5/unit..." | Balloons animation 🎈 |

The commented-out lines (e.g., `# classifier = ProblemClassifier()`) are where the real logic will go once each module is implemented.

**Realistic Example — What the user sees after clicking Solve:**

```
🤔 Understanding your problem...

ℹ️ Step 1: Classifying problem type...
✅ Problem classified as: Linear Programming

ℹ️ Step 2: Generating mathematical model...
✅ Model generated successfully

ℹ️ Step 3: Solving with PuLP...
✅ Solution found!

ℹ️ Step 4: Interpreting results...
🎈🎈🎈 (balloons animation)
```

### 8d. Edge Cases (Lines 137–142)

```python
elif solve_button:
    st.warning("⚠️ Please enter a problem description first.")

if clear_button:
    problem_description = ""
    st.rerun()
```

- If user clicks **Solve** with an empty text box → yellow warning
- If user clicks **Clear** → resets the text area and refreshes the page via `st.rerun()`

---

## 9. Tab 2 — Results (Lines 144–187)

```python
with tab2:
    st.header("Solution Results")

    if 'solution_ready' in st.session_state and st.session_state.solution_ready:
        col1, col2 = st.columns(2)

        with col1:
            st.metric("Objective Value", "$12,450", "Optimal")
            st.metric("Solution Status", "Optimal", delta_color="normal")
            st.metric("Solve Time", "2.3s")

        with col2:
            st.metric("Variables", "45")
            st.metric("Constraints", "78")
            st.metric("Iterations", "156")
```

### What it does

Shows solution metrics in a two-column dashboard layout. `st.metric()` renders a label, a large number, and an optional delta/status indicator.

Currently uses **hardcoded placeholder values**. Once implemented, these will come from the actual solver output.

### Realistic Example — What the user sees (after solving):

```
┌─────────────────────────┬─────────────────────────┐
│ Objective Value         │ Variables               │
│ $12,450    ▲ Optimal    │ 45                      │
│                         │                         │
│ Solution Status         │ Constraints             │
│ Optimal                 │ 78                      │
│                         │                         │
│ Solve Time              │ Iterations              │
│ 2.3s                    │ 156                     │
└─────────────────────────┴─────────────────────────┘
```

**For the furniture transportation example**, once implemented, this might show:

| Metric | Real Value |
|---|---|
| Objective Value | $1,740 (minimum total shipping cost) |
| Variables | 6 (one xᵢⱼ for each factory→store pair) |
| Constraints | 5 (2 supply + 3 demand) |
| Solve Time | 0.01s |

### AI Explanation Section (Lines 163–173)

```python
st.subheader("🤖 AI Explanation")
st.info("""
Based on the optimization results, here are the key recommendations:

1. **Optimal Transportation Plan**: Ship 60 units from Warehouse A to Store 1...
2. **Cost Savings**: This plan saves $3,200 compared to current operations
3. **Utilization**: All warehouse capacity is efficiently utilized
""")
```

Placeholder for AI-generated explanations. Once the `ResultInterpreter` module is implemented, it will call the Anthropic/OpenAI API to produce a natural language summary like:

> **Optimal Shipping Plan:**
> - Factory A → Store 1: 120 tables at $5 = $600
> - Factory A → Store 2: 80 tables at $8 = $640
> - Factory B → Store 3: 100 tables at $9 = $900
>
> **Total Cost: $1,740**
>
> Factory A ships all of Store 1 and Store 2's demand. Factory B handles Store 3. Factory A uses 200/200 capacity, Factory B uses 100/150.

### Download Button (Lines 179–185)

```python
st.download_button(
    "📥 Download Results (CSV)",
    "sample,data",
    "results.csv",
    "text/csv"
)
```

Creates a button that downloads a CSV file. Currently downloads placeholder data `"sample,data"`. Once implemented, it will produce a real file like:

```csv
from,to,units,cost_per_unit,total_cost
Factory A,Store 1,120,5,600
Factory A,Store 2,80,8,640
Factory B,Store 3,100,9,900
,,,,Total: 1740
```

---

## 10. Tab 3 — Visualizations (Lines 189–200)

```python
with tab3:
    st.header("Visualizations")

    if 'solution_ready' in st.session_state and st.session_state.solution_ready:
        viz_type = st.selectbox(
            "Visualization Type",
            ["Network Diagram", "Bar Chart", "Sensitivity Analysis", "Gantt Chart"]
        )
        st.info("📊 Visualizations will be displayed here based on problem type")
    else:
        st.info("👈 Solve a problem to see visualizations here")
```

### What it does

Shows a dropdown to pick a chart type. Currently just a placeholder message. Once implemented, this tab will render actual charts using `matplotlib`, `plotly`, or Streamlit's built-in charting.

### Realistic Example — What it will look like (once implemented):

**For a Transportation problem — Network Diagram:**

```
Factory A ──(120 @ $5)──► Store 1
    │
    └──(80 @ $8)──────► Store 2

Factory B ──(100 @ $9)──► Store 3
```

**For a Scheduling problem — Gantt Chart:**

```
Machine 1: |████ Job A ████|███ Job C ███|
Machine 2: |██ Job B ██|████████ Job D ████████|
           0    2    4    6    8    10   12  hours
```

**For Sensitivity Analysis — Bar Chart:**

A bar chart showing how much the objective changes if each constraint's right-hand side changes by one unit (shadow prices).

---

## 11. Tab 4 — Help (Lines 202–251)

```python
with tab4:
    st.header("How to Use OR Assistant")

    st.markdown("""
    ### 🎯 Getting Started
    1. **Describe Your Problem**: Use natural language...
    2. **Select Solver**: Choose your preferred solver...
    3. **Click Solve**: Let the AI understand, model, and solve...
    4. **Review Results**: Get actionable insights...

    ### 📝 Problem Types Supported
    - **Linear Programming (LP)**
    - **Integer Programming (IP)**
    - **Transportation**
    - **Assignment**
    - **Scheduling**

    ### 💡 Example Problems
    ...
    """)
```

### What it does

A static help/documentation page rendered in Markdown. Lists supported problem types, example inputs, and tips.

### Realistic Example — Problem Types Explained

| Type | Real-World Example |
|---|---|
| **Linear Programming** | "Maximize profit from 3 products given limited machine hours and raw materials" |
| **Integer Programming** | "How many delivery trucks (whole numbers) should I assign to each route?" |
| **Transportation** | "Minimize shipping costs from 3 factories to 5 retail stores" |
| **Assignment** | "Assign 10 employees to 10 tasks so total completion time is minimized" |
| **Scheduling** | "Schedule 20 jobs on 3 machines to minimize total makespan" |

---

## 12. Footer (Lines 253–255)

```python
st.divider()
st.caption("OR Assistant v0.1.0 | Built with AI & Streamlit | NDSU Project")
```

### What it does

- `st.divider()` — Draws a horizontal line
- `st.caption()` — Renders small gray text at the bottom

### Realistic Example

At the very bottom of every page:

```
────────────────────────────────────────────
OR Assistant v0.1.0 | Built with AI & Streamlit | NDSU Project
```

---

## How the Pieces Fit Together

Here is the overall flow when a user interacts with the app:

```
User opens http://localhost:8501
        │
        ▼
┌─────────────────────────────────┐
│  .env loaded (API keys ready)   │
│  Page configured (wide layout)  │
│  CSS injected (styled headers)  │
└────────────┬────────────────────┘
             │
             ▼
┌──────────┐  ┌──────────────────────────────────────┐
│ SIDEBAR  │  │ MAIN AREA (4 tabs)                    │
│          │  │                                        │
│ Solver ▼ │  │ Tab 1: Type problem → Click Solve      │
│ PuLP     │  │   ├─ Step 1: Classify (AI)             │
│          │  │   ├─ Step 2: Model (AI)                │
│ Advanced │  │   ├─ Step 3: Solve (PuLP/OR-Tools)     │
│ Options  │  │   └─ Step 4: Interpret (AI)            │
│          │  │                                        │
│ Examples │  │ Tab 2: View metrics + AI explanation    │
│ Category │  │ Tab 3: Charts & diagrams               │
│ [Load]   │  │ Tab 4: Help docs                       │
└──────────┘  └──────────────────────────────────────┘
```

### Session State

Streamlit reruns the **entire script** from top to bottom every time the user interacts with any widget. `st.session_state` is how data persists between reruns:

- `st.session_state.solution_ready` — Set to `True` after a successful solve. This is what makes Tab 2 and Tab 3 show results instead of "Solve a problem first."
- `st.session_state.load_example` — Set to `True` when the "Load Example" button is clicked.

### What Needs Implementation

The four commented-out module calls in the solve pipeline are the core student work:

```python
# classifier = ProblemClassifier()
# problem_data = classifier.classify(problem_description)

# generator = ModelGenerator()
# model = generator.generate(problem_data)

# solver = SolverInterface(solver_type=solver_type.lower())
# solution = solver.solve(model, max_time=max_time)

# interpreter = ResultInterpreter()
# explanation = interpreter.interpret(solution, problem_data)
```

Once these are implemented, the placeholders (`st.success("✅ Problem classified as: Linear Programming")`) get replaced with real dynamic output.
