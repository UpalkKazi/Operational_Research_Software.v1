# OR Studio

OR Studio is an operations research workspace with two views:

- **Chat** takes a problem in natural language, OR-Learn, or AMPL-style syntax
  and returns a result card inline (status, objective, solver, time, key
  decisions, plus variables, constraints, charts, interpretation, diagnostics
  and exports).
- **Model Playground** has three tabs. **Easy Start** offers LP, IP,
  transportation, assignment, knapsack and scheduling templates. **Algebraic**
  shows source and expanded math side by side. **Live Editor** gives MathLive
  equations with a symbols keypad, a variables table, a baseline comparison,
  and RHS sensitivity sweeps.

**Load Problem**, reachable from both views, brings in the bundled examples,
uploads (`.xlsx .xls .csv .docx .doc .txt .pdf .mps .mps.gz`), and MIPLIB
instances, with download progress and cache controls.

Structured models solve offline. Natural language uses the configured AI
provider and needs `OPENAI_API_KEY` or `ANTHROPIC_API_KEY` with credits. Without
a key, Chat says so, keeps your text, and points to the offline options.

The previous interface is kept as `legacy_app.py`
(`python -m streamlit run legacy_app.py`).

## Solvers

| Key | Backend | Model types |
|---|---|---|
| `auto` | Picks CBC, or SCIP for large or MIPLIB integer models, and explains why | LP, MIP |
| `pulp_cbc` | COIN-OR CBC via PuLP | LP, MIP |
| `cvxpy_osqp` | OSQP via CVXPY | LP only; integer models are refused with a reason |
| `cvxpy_glpk` | GLPK via CVXPY/CVXOPT | LP, MIP |
| `cvxpy_scip` | SCIP via PySCIPOpt | LP, MIP; the only backend that supports Cancel |

A manual choice is never silently replaced. Each run records the requested
solver, the backend that actually ran, the settings, status and timing.

## Run locally (development)

```powershell
py -3.12 -m venv venv          # 3.12 is the production target; 3.14 also works
.\venv\Scripts\Activate.ps1
python -m pip install -r requirements-dev.txt
python -m streamlit run app.py
```

Open <http://localhost:8501>. `?view=playground` opens Model Playground directly.

## Production startup

Use a clean environment with no `.env` and no AI keys. With
[uv](https://docs.astral.sh/uv/):

```powershell
uv venv --python 3.12 .venv
uv pip install --python .venv\Scripts\python.exe -r requirements-runtime.txt
.venv\Scripts\python.exe -m streamlit run app.py --server.address=0.0.0.0 --server.port=8501 --server.headless=true
```

Health check: `GET /_stcore/health` returns `ok`. MIPLIB downloads and
cached solutions are stored under `ORSTUDIO_DATA_DIR` (default `./data`).

Docker (same command, non-root user, health check built in):

```bash
docker build -t or-studio .
docker run --rm -p 8501:8501 -v or-studio-data:/app/data or-studio
```

To enable natural language, pass `-e OPENAI_API_KEY=...` (or
`ANTHROPIC_API_KEY`) and optionally `AI_PROVIDER`. Never commit `.env`.

## Tests

```powershell
python -m pytest tests --ignore=tests/browser -m "not network"  # unit + AppTest, offline
python -m pytest tests --ignore=tests/browser                    # also downloads MIPLIB flugpl
python -m playwright install chromium
python -m streamlit run app.py                           # in another terminal
python -m pytest tests/browser                           # end-to-end, writes artifacts/screens
```

`ORSTUDIO_URL` points the browser tests at another server (for example a
production build on port 8502).

The numeric fixture used throughout is: maximize 45c + 80t subject to
5c + 20t ≤ 400 and 10c + 15t ≤ 450. The baseline optimum is c = 24, t = 14 with
objective 2200. Setting RHS1 to 300 gives 36 / 6 and objective 2100
(difference −100), while the baseline stays at 2200. Sweeping RHS1 over
300 / 350 / 400 gives 2100 / 2150 / 2200 and leaves the draft unchanged.

## Syntax

OR-Learn ([upstream README](https://github.com/harunpirim/orlearn), read through the
real library pinned at `38355732feae2c6cc776d58b6f01491bbce78124`):

```python
from orlearn import OR

result = (OR()
    .maximize([45, 80], names=["chairs", "tables"])
    .subject_to([5, 20], "<=", 400, "Wood")
    .subject_to([10, 15], "<=", 450, "Labor")
    .solve())
```

AMPL-style, with sets, indexed params and variables, and `sum{...}`. The full
reference is in [docs/AMPL_SUBSET.md](docs/AMPL_SUBSET.md).

```text
set P := chairs tables;
param profit{P} := chairs 45 tables 80;
var x{P} >= 0;
maximize z: sum{p in P} profit[p]*x[p];
subject to wood: 5*x['chairs'] + 20*x['tables'] <= 400;
subject to labor: 10*x['chairs'] + 15*x['tables'] <= 450;
```

Pasted Python is never executed. Unsupported constructs are rejected with a
line and column, and a failed structured parse is never sent to the AI.
Planned AI-assisted conversion of descriptions to AMPL is described in
[docs/AI_CONVERSION.md](docs/AI_CONVERSION.md).

## CLI

```powershell
python cli.py solve --file model.mod --solver auto --output result.json
python cli.py solve --file tests/fixtures/uploads/fixture.mps --solver cvxpy_scip
python cli.py validate model.mod
python cli.py examples
python cli.py solvers
```

## Attribution

OR-Learn examples are adapted from
[harunpirim/orlearn](https://github.com/harunpirim/orlearn) (MIT). MathLive is
vendored under `src/ui/mathlive_build/vendor` (MIT).
