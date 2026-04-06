# OR Assistant Project - Complete Description for Claude

## Project Overview

I'm working on an AI-powered Operations Research Assistant - a Streamlit web application that helps solve optimization problems using natural language. Users describe their OR problems in plain English, and the system automatically classifies the problem type, generates mathematical models, solves them using appropriate solvers, and provides AI-interpreted explanations of the results.

## Core Architecture

The project follows a 4-step pipeline:
1. **Problem Classification** - AI analyzes natural language input to identify problem type (LP, IP, MIP, Transportation, etc.)
2. **Model Generation** - Converts problem description to mathematical model with variables, objectives, and constraints
3. **Solving** - Routes to appropriate solver (PuLP/CBC, CVXPY, OR-Tools) based on problem type
4. **Result Interpretation** - AI explains the solution in business-friendly terms

## Technology Stack

**AI/LLM Integration:**
- Anthropic Claude API (primary)
- OpenAI API (fallback)
- Used for problem understanding and result explanation

**OR Solvers:**
- PuLP with CBC (default)
- OR-Tools (Google's optimizer)
- CVXPY with multiple backends (OSQP, GLPK, SCIP)
- Optional: Gurobi, CPLEX (commercial)

**Frontend:**
- Streamlit for web interface
- Plotly for interactive visualizations
- Custom CSS for modern UI

**Backend:**
- Python 3.11+
- FastAPI for future API endpoints
- Environment-based configuration

## Directory Structure

```
or-assistant/
├── app.py                    # Main Streamlit application
├── src/
│   ├── agents/              # AI components
│   │   ├── problem_classifier.py    # Natural language → problem type
│   │   └── result_interpreter.py    # Solution → human explanation
│   ├── ingestion/           # File parsing & data extraction
│   │   ├── file_parser.py           # Multi-format file reader
│   │   ├── data_extractor.py        # Extract OR data from files
│   │   └── miplib_loader.py         # MIPLIB benchmark integration
│   ├── modeling/            # Model generation
│   │   └── model_generator.py       # Problem data → math model
│   ├── solvers/             # Solver interfaces
│   │   ├── solver_interface.py      # Unified solver wrapper
│   │   └── solver_router.py         # Route to best solver
│   ├── storage/             # Caching & persistence
│   │   └── miplib_cache.py          # Cache MIPLIB problems
│   ├── ui/                  # UI components
│   │   ├── solver_settings.py       # Solver configuration UI
│   │   └── solver_progress.py       # Progress tracking
│   ├── utils/               # Utilities
│   │   └── api_client.py            # AI API client
│   └── visualization/       # Chart generation
│       └── chart_generator.py       # Create optimization charts
├── tests/                   # Test suite
├── data/                    # Examples & templates
├── docs/                    # Documentation
└── config/                  # Configuration files
```

## Key Features Implemented

1. **Natural Language Input**
   - Text area for problem description
   - Support for business-level language
   - No need for mathematical notation

2. **Multi-Format File Upload**
   - Excel/CSV: Tabular data (costs, capacities)
   - Word/PDF: Problem descriptions
   - MPS: Standard OR format
   - Automatic data extraction

3. **Problem Types Supported**
   - Linear Programming (LP)
   - Integer Programming (IP/MIP)
   - Transportation Problems
   - Assignment Problems
   - Scheduling (Job-Shop, Flow-Shop)
   - Network Flow
   - Knapsack
   - Traveling Salesman (TSP)

4. **Intelligent Solver Routing**
   - Auto-detects best solver for problem type
   - Manual override available
   - Configurable time limits and parameters

5. **Result Visualization**
   - Network diagrams for transportation
   - Gantt charts for scheduling
   - Sensitivity analysis
   - Variable distributions
   - Efficient frontier plots

6. **AI-Powered Explanations**
   - Business-context interpretation
   - Key insights and recommendations
   - What-if scenario suggestions
   - Plain English summaries

## Current Implementation Status

**Working:**
- Basic Streamlit UI with 4 tabs (Solve, Results, Visualizations, Help)
- Solver interface supporting PuLP and CVXPY
- Chart generation with Plotly
- File parsing for multiple formats
- Environment configuration
- Example problems and templates

**In Progress:**
- AI problem classification with Claude/OpenAI
- Dynamic model generation
- Result interpretation
- MIPLIB integration
- Advanced solver routing

**Planned:**
- OR-Tools full integration
- Real-time progress tracking
- Solution caching
- API endpoints
- Multi-objective optimization
- Stochastic programming support

## Example Usage Flow

1. User enters: "I have 3 factories that can produce 100, 150, and 200 units. I need to supply 5 stores that need 80, 70, 90, 60, and 100 units. Shipping costs vary from $2-8 per unit. Minimize total cost."

2. System classifies: Transportation Problem

3. Generates model:
   ```
   Minimize: Σ(cost[i,j] * x[i,j])
   Subject to:
   - Σ(x[i,j]) ≤ supply[i] for all factories i
   - Σ(x[i,j]) = demand[j] for all stores j
   - x[i,j] ≥ 0
   ```

4. Solves and returns: "Optimal cost: $1,250. Ship 80 units from Factory 1 to Store 1..."

## Technical Implementation Details

**Problem Classifier (agents/problem_classifier.py):**
- Uses Claude/OpenAI to analyze natural language
- Returns structured dict with problem_type, objectives, constraints
- Handles ambiguous descriptions with clarifying assumptions

**Model Generator (modeling/model_generator.py):**
- Converts classifier output to PuLP LpProblem
- Supports various objective types (min/max)
- Handles different constraint types

**Solver Interface (solvers/solver_interface.py):**
- Unified interface for multiple solvers
- Automatic solver selection based on problem characteristics
- Error handling and timeout management

**Chart Generator (visualization/chart_generator.py):**
- Creates interactive Plotly charts
- Auto-selects appropriate visualization
- Customizable themes and layouts

## Configuration & Environment

Required environment variables (.env file):
```
AI_PROVIDER=anthropic
ANTHROPIC_API_KEY=your_key_here
# or
OPENAI_API_KEY=your_key_here
SOLVER_TIMEOUT=300
ENABLE_CACHING=true
```

## Development Guidelines

- Modular architecture with clear separation of concerns
- Type hints throughout for better IDE support
- Comprehensive error handling
- Pytest-based testing with >80% coverage target
- Black formatting, flake8 linting
- Detailed docstrings for all public methods

## Unique Aspects

1. **AI-First Approach**: Unlike traditional OR tools, this prioritizes natural language understanding
2. **Solver Agnostic**: Abstract interface allows easy addition of new solvers
3. **Educational Focus**: Explanations help users understand OR concepts
4. **Real-World Ready**: Handles messy, incomplete problem descriptions
5. **Extensible**: Plugin architecture for new problem types and visualizations

## Current Challenges

1. Balancing AI interpretation flexibility with mathematical precision
2. Handling ambiguous or incomplete problem descriptions
3. Solver selection for edge cases
4. Performance optimization for large problems
5. Caching strategy for expensive AI calls

## Testing Strategy

- Unit tests for each module
- Integration tests for full pipeline
- Mock AI responses for consistent testing
- Performance benchmarks
- Example problem test suite

## Future Vision

- Web API for programmatic access
- Multi-user support with problem library
- Custom algorithm upload
- Real-time collaboration
- Mobile interface
- Integration with business tools (Excel, ERP systems)

This is a full-stack OR solution that bridges the gap between business users and optimization technology, making advanced OR techniques accessible through natural language.