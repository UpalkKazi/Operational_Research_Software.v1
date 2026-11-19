"""
OR Assistant — One-Time Test Setup
===================================
Run this ONCE from your project root to create all test scripts:

    python setup_tests.py

This creates the tests/ folder and writes test_phase2.py through
test_phase5.py inside it. After that, you can run:

    python tests/test_phase2.py
    python tests/test_phase3.py
    python tests/test_phase4.py
    python tests/test_phase5.py
"""

import os

# Make sure tests/ folder exists
os.makedirs("tests", exist_ok=True)

# ─────────────────────────────────────────────────────────────────
# test_phase2.py
# ─────────────────────────────────────────────────────────────────
PHASE2 = '''"""
OR Assistant - Phase 2 Interactive Tester
Run from your project root:
    python tests/test_phase2.py

Paste your problem in plain English when prompted.
The classifier will show you what it detected.
"""

import sys
import os
sys.path.insert(0, '.')

# Load .env file so ANTHROPIC_API_KEY is available
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # dotenv not installed, rely on system env vars

try:
    from src.agents.problem_classifier import ProblemClassifier
except ImportError as e:
    print(f"\\n  ERROR: Could not import ProblemClassifier.")
    print(f"  Make sure you are running from the or-assistant folder.")
    print(f"  Details: {e}")
    sys.exit(1)

print("\\n" + "="*60)
print("  OR ASSISTANT — Phase 2: Problem Classifier Test")
print("="*60)
print("\\n  Paste your problem in plain English below.")
print("  Press Enter twice when done.\\n")

lines = []
while True:
    try:
        line = input()
        if line == "" and lines and lines[-1] == "":
            break
        lines.append(line)
    except EOFError:
        break

problem = "\\n".join(lines).strip()

if not problem:
    print("\\n  No input received. Exiting.")
    sys.exit(1)

print("\\n" + "-"*60)
print("  Running classifier...")
print("-"*60)

try:
    classifier = ProblemClassifier()
    result = classifier.classify(problem)

    print(f"\\n  Problem Type   : {result.get(\'problem_type\', \'N/A\')}")
    print(f"  Objective      : {result.get(\'objective\', \'N/A\')}")
    print(f"  Confidence     : {result.get(\'confidence\', 0):.0%}")

    variables = result.get(\'decision_variables\', [])
    print(f"\\n  Decision Variables ({len(variables)} found):")
    for v in variables:
        print(f"    - {v.get(\'name\', \'?\')} ({v.get(\'type\', \'?\')}): {v.get(\'description\', \'\')}")

    constraints = result.get(\'constraints\', [])
    print(f"\\n  Constraints ({len(constraints)} found):")
    for c in constraints:
        print(f"    - {c.get(\'name\', \'?\')} : {c.get(\'expression\', \'\')}")

    assumptions = result.get(\'assumptions\', [])
    if assumptions:
        print(f"\\n  Assumptions ({len(assumptions)} made by AI):")
        for a in assumptions:
            impact = a.get(\'impact\', \'?\').upper()
            conf   = a.get(\'confidence\', 0)
            print(f"    [{impact}] {a.get(\'assumption\', \'\')} (confidence: {conf:.0%})")

    warnings = result.get(\'warnings\', [])
    if warnings:
        print(f"\\n  Warnings:")
        for w in warnings:
            print(f"    ! {w}")

    print("\\n" + "-"*60)
    conf = result.get(\'confidence\', 0)
    if conf >= 0.8:
        print("  RESULT: HIGH CONFIDENCE — classifier is sure about this problem.")
    elif conf >= 0.6:
        print("  RESULT: MEDIUM CONFIDENCE — review assumptions above before solving.")
    else:
        print("  RESULT: LOW CONFIDENCE — problem is vague. Add more details.")
    print("-"*60 + "\\n")

except Exception as e:
    print(f"\\n  FAILED: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
'''

# ─────────────────────────────────────────────────────────────────
# test_phase3.py
# ─────────────────────────────────────────────────────────────────
PHASE3 = '''"""
OR Assistant - Phase 3 Interactive Tester
Run from your project root:
    python tests/test_phase3.py

Paste your problem in plain English when prompted.
Shows the mathematical model that gets built.
"""

import sys
import os
sys.path.insert(0, '.')

# Load .env file so ANTHROPIC_API_KEY is available
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

try:
    from src.agents.problem_classifier import ProblemClassifier
    from src.modeling.model_generator import ModelGenerator
    import pulp
except ImportError as e:
    print(f"\\n  ERROR: Could not import required modules.")
    print(f"  Details: {e}")
    sys.exit(1)

print("\\n" + "="*60)
print("  OR ASSISTANT — Phase 3: Model Generator Test")
print("="*60)
print("\\n  Paste your problem in plain English below.")
print("  Press Enter twice when done.\\n")

lines = []
while True:
    try:
        line = input()
        if line == "" and lines and lines[-1] == "":
            break
        lines.append(line)
    except EOFError:
        break

problem = "\\n".join(lines).strip()
if not problem:
    print("\\n  No input received. Exiting.")
    sys.exit(1)

print("\\n" + "-"*60)
print("  Step 1: Classifying problem...")
print("-"*60)
try:
    classifier = ProblemClassifier()
    problem_data = classifier.classify(problem)
    print(f"  Type       : {problem_data.get(\'problem_type\', \'N/A\')}")
    print(f"  Objective  : {problem_data.get(\'objective\', \'N/A\')}")
    print(f"  Confidence : {problem_data.get(\'confidence\', 0):.0%}")
except Exception as e:
    print(f"\\n  FAILED at classifier: {e}")
    sys.exit(1)

print("\\n" + "-"*60)
print("  Step 2: Building mathematical model...")
print("-"*60)
try:
    generator = ModelGenerator()
    model = generator.generate(problem_data)

    if not isinstance(model, pulp.LpProblem):
        print("\\n  FAILED: generate() did not return an LpProblem.")
        sys.exit(1)

    sense = "Maximize" if model.sense == pulp.LpMaximize else "Minimize"
    variables    = model.variables()
    binary_vars  = [v for v in variables if v.cat == \'Binary\']
    integer_vars = [v for v in variables if v.cat == \'Integer\']
    cont_vars    = [v for v in variables if v.cat == \'Continuous\']

    print(f"\\n  Model Name     : {model.name}")
    print(f"  Direction      : {sense}")
    print(f"  Variables      : {len(variables)} total")
    if cont_vars:
        print(f"    Continuous   : {len(cont_vars)}")
    if integer_vars:
        print(f"    Integer      : {len(integer_vars)}")
    if binary_vars:
        print(f"    Binary (0/1) : {len(binary_vars)}")

    names = [v.name for v in variables[:10]]
    print(f"\\n  Variable names : {names}")
    if len(variables) > 10:
        print(f"    ... and {len(variables)-10} more")

    constraints = model.constraints
    print(f"\\n  Constraints    : {len(constraints)}")
    for name, c in list(constraints.items())[:5]:
        print(f"    - {name}: {c}")
    if len(constraints) > 5:
        print(f"    ... and {len(constraints)-5} more")

    print("\\n" + "-"*60)
    print(f"  RESULT: Model built successfully.")
    print(f"  {len(variables)} variables, {len(constraints)} constraints.")
    print("-"*60 + "\\n")

except Exception as e:
    print(f"\\n  FAILED at model generator: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
'''

# ─────────────────────────────────────────────────────────────────
# test_phase4.py
# ─────────────────────────────────────────────────────────────────
PHASE4 = '''"""
OR Assistant - Phase 4 Interactive Tester
Run from your project root:
    python tests/test_phase4.py

Paste your problem in plain English when prompted.
Runs classify + build + solve and prints the answer.
"""

import sys
import os
import time
sys.path.insert(0, '.')

# Load .env file so ANTHROPIC_API_KEY is available
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

try:
    from src.agents.problem_classifier import ProblemClassifier
    from src.modeling.model_generator import ModelGenerator
    from src.solvers.solver_interface import SolverInterface
    import pulp
except ImportError as e:
    print(f"\\n  ERROR: Could not import required modules.")
    print(f"  Details: {e}")
    sys.exit(1)

print("\\n" + "="*60)
print("  OR ASSISTANT — Phase 4: Solver Test")
print("="*60)
print("\\n  Paste your problem in plain English below.")
print("  Press Enter twice when done.\\n")

lines = []
while True:
    try:
        line = input()
        if line == "" and lines and lines[-1] == "":
            break
        lines.append(line)
    except EOFError:
        break

problem = "\\n".join(lines).strip()
if not problem:
    print("\\n  No input received. Exiting.")
    sys.exit(1)

start_total = time.time()

print("\\n" + "-"*60)
print("  Step 1: Classifying...")
print("-"*60)
try:
    classifier = ProblemClassifier()
    problem_data = classifier.classify(problem)
    print(f"  Type       : {problem_data.get(\'problem_type\', \'N/A\')}")
    print(f"  Objective  : {problem_data.get(\'objective\', \'N/A\')}")
    print(f"  Confidence : {problem_data.get(\'confidence\', 0):.0%}")
except Exception as e:
    print(f"\\n  FAILED: {e}")
    sys.exit(1)

print("\\n" + "-"*60)
print("  Step 2: Building model...")
print("-"*60)
try:
    generator = ModelGenerator()
    model = generator.generate(problem_data)
    print(f"  Variables   : {len(model.variables())}")
    print(f"  Constraints : {len(model.constraints)}")
except Exception as e:
    print(f"\\n  FAILED: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\\n" + "-"*60)
print("  Step 3: Solving...")
print("-"*60)
try:
    solver   = SolverInterface(\'pulp\')
    solution = solver.solve(model)

    status = solution.get(\'status\', \'Unknown\')
    obj    = solution.get(\'objective_value\')
    t      = solution.get(\'solve_time\', 0)

    print(f"\\n  Status          : {status}")
    if obj is not None:
        print(f"  Objective Value : {obj:.4f}")
    print(f"  Solve Time      : {t:.3f}s")

    vars_dict = solution.get(\'variables\', {})
    nonzero   = {k: v for k, v in vars_dict.items() if v is not None and abs(v) > 0.0001}
    zero      = {k: v for k, v in vars_dict.items() if v is not None and abs(v) <= 0.0001}

    print(f"\\n  Active Variables (non-zero):")
    if nonzero:
        for name, val in list(nonzero.items())[:15]:
            print(f"    {name} = {val:.4f}")
        if len(nonzero) > 15:
            print(f"    ... and {len(nonzero)-15} more")
    else:
        print("    None — all variables are zero.")

    if zero:
        zkeys = list(zero.keys())[:5]
        print(f"\\n  Zero Variables  : {zkeys}" + (" ..." if len(zero) > 5 else ""))

    total = time.time() - start_total
    print("\\n" + "-"*60)
    if solution.get(\'is_optimal\'):
        print(f"  RESULT: OPTIMAL SOLUTION FOUND")
        print(f"  Objective Value = {obj:.4f}")
        print(f"  Total time      : {total:.1f}s")
    else:
        print(f"  RESULT: {status} — no optimal solution.")
        print(f"  Check your constraints — they may contradict each other.")
    print("-"*60 + "\\n")

except Exception as e:
    print(f"\\n  FAILED at solver: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
'''

# ─────────────────────────────────────────────────────────────────
# test_phase5.py
# ─────────────────────────────────────────────────────────────────
PHASE5 = '''"""
OR Assistant - Phase 5 Interactive Tester (Full Pipeline)
Run from your project root:
    python tests/test_phase5.py

Paste your problem in plain English when prompted.
Runs the FULL pipeline: classify → model → solve → AI explanation.
"""

import sys
import os
import time
sys.path.insert(0, '.')

# Load .env file so ANTHROPIC_API_KEY is available
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

try:
    from src.agents.problem_classifier import ProblemClassifier
    from src.modeling.model_generator import ModelGenerator
    from src.solvers.solver_interface import SolverInterface
    from src.interpreters.result_interpreter import ResultInterpreter
except ImportError as e:
    print(f"\\n  ERROR: Could not import required modules.")
    print(f"  Details: {e}")
    sys.exit(1)

print("\\n" + "="*60)
print("  OR ASSISTANT — Phase 5: Full Pipeline Test")
print("  Classify → Model → Solve → AI Explanation")
print("="*60)
print("\\n  Paste your problem in plain English below.")
print("  Press Enter twice when done.\\n")

lines = []
while True:
    try:
        line = input()
        if line == "" and lines and lines[-1] == "":
            break
        lines.append(line)
    except EOFError:
        break

problem = "\\n".join(lines).strip()
if not problem:
    print("\\n  No input received. Exiting.")
    sys.exit(1)

start_total = time.time()

print("\\n" + "-"*60)
print("  Step 1: Classifying...")
try:
    classifier = ProblemClassifier()
    problem_data = classifier.classify(problem)
    ptype = problem_data.get(\'problem_type\', \'?\')
    obj   = problem_data.get(\'objective\', \'?\')
    conf  = problem_data.get(\'confidence\', 0)
    print(f"  Type: {ptype}  |  Objective: {obj}  |  Confidence: {conf:.0%}")
    assumptions = problem_data.get(\'assumptions\', [])
    if assumptions:
        print(f"  AI made {len(assumptions)} assumption(s) — visible in the app UI.")
except Exception as e:
    print(f"  FAILED: {e}")
    sys.exit(1)

print("\\n  Step 2: Building model...")
try:
    generator = ModelGenerator()
    model = generator.generate(problem_data)
    print(f"  {len(model.variables())} variables, {len(model.constraints)} constraints")
except Exception as e:
    print(f"  FAILED: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\\n  Step 3: Solving...")
try:
    solver   = SolverInterface(\'pulp\')
    solution = solver.solve(model)
    status   = solution.get(\'status\', \'Unknown\')
    obj_val  = solution.get(\'objective_value\')
    t        = solution.get(\'solve_time\', 0)
    print(f"  Status: {status}  |  Objective: {obj_val:.4f if obj_val else \'N/A\'}  |  Time: {t:.3f}s")
except Exception as e:
    print(f"  FAILED: {e}")
    sys.exit(1)

print("\\n  Step 4: Generating AI explanation...")
try:
    interpreter    = ResultInterpreter()
    interpretation = interpreter.interpret(solution, problem_data)
except Exception as e:
    print(f"  FAILED: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

total = time.time() - start_total

print("\\n" + "="*60)
print("  RESULTS")
print("="*60)
print(f"\\n  Objective Value : {solution.get(\'objective_value\', \'N/A\')}")
print(f"  Status          : {solution.get(\'status\', \'N/A\')}")
print(f"  Total Time      : {total:.1f}s")

vars_dict = solution.get(\'variables\', {})
nonzero   = {k: v for k, v in vars_dict.items() if v is not None and abs(v) > 0.0001}
if nonzero:
    print(f"\\n  Active Variables:")
    for name, val in list(nonzero.items())[:10]:
        print(f"    {name} = {val:.4f}")

summary = interpretation.get(\'summary\', \'\')
if summary:
    print(f"\\n  AI Summary:")
    words = summary.split()
    line_buf, out = [], []
    for w in words:
        line_buf.append(w)
        if len(\' \'.join(line_buf)) > 55:
            out.append(\'  \' + \' \'.join(line_buf[:-1]))
            line_buf = [w]
    if line_buf:
        out.append(\'  \' + \' \'.join(line_buf))
    for ln in out:
        print(ln)

findings = interpretation.get(\'key_findings\', [])
if findings:
    print(f"\\n  Key Findings:")
    for f in findings:
        print(f"    * {f}")

recs = interpretation.get(\'recommendations\', [])
if recs:
    print(f"\\n  Recommendations:")
    for i, r in enumerate(recs, 1):
        print(f"    {i}. {r}")

warnings = interpretation.get(\'warnings\', [])
if warnings:
    print(f"\\n  Warnings:")
    for w in warnings:
        print(f"    ! {w}")

print("\\n" + "="*60)
if total < 30:
    print(f"  ALL STEPS PASSED — Pipeline done in {total:.1f}s")
    print(f"  Ready to wire the UI in Phase 6.")
else:
    print(f"  WARNING: Took {total:.1f}s (over 30s target).")
print("="*60 + "\\n")
'''

# ─────────────────────────────────────────────────────────────────
# Write all files
# ─────────────────────────────────────────────────────────────────
files = {
    "tests/test_phase2.py": PHASE2,
    "tests/test_phase3.py": PHASE3,
    "tests/test_phase4.py": PHASE4,
    "tests/test_phase5.py": PHASE5,
}

for path, code in files.items():
    with open(path, "w", encoding="utf-8") as f:
        f.write(code)
    print(f"  Created: {path}")

print("\n  Setup complete. You can now run:")
print("    python tests/test_phase2.py")
print("    python tests/test_phase3.py")
print("    python tests/test_phase4.py")
print("    python tests/test_phase5.py")
