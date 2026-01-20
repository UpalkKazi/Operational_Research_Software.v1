# OR Assistant - AI-Powered Operations Research Tool

An intelligent assistant that helps solve Operations Research problems using natural language. Built with Claude AI and open-source OR solvers.

## 🎯 Project Overview

OR Assistant bridges the gap between business problems and mathematical optimization by:
- Understanding problem descriptions in natural language
- Automatically formulating mathematical models
- Solving problems using industry-standard solvers
- Providing clear, actionable insights

## 🚀 Features

- **Natural Language Interface**: Describe problems in plain English
- **Multi-Problem Support**: LP, IP, Transportation, Assignment, Scheduling
- **Multiple Solvers**: PuLP, OR-Tools, CVXPY integration
- **Smart Interpretation**: AI-powered results explanation
- **Visualization**: Charts, tables, and network diagrams
- **Simulation Engine**: What-if scenario analysis

## 📋 Prerequisites

- Python 3.10 or higher
- Anthropic API key (get from https://console.anthropic.com)
- Optional: Gurobi academic license for advanced solving

## 🛠️ Installation

### 1. Clone the repository
```bash
git clone https://github.com/yourusername/or-assistant.git
cd or-assistant
```

### 2. Create virtual environment
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Set up environment variables
```bash
cp .env.example .env
# Edit .env and add your ANTHROPIC_API_KEY
```

## 🏃 Quick Start

### Run the Streamlit App
```bash
streamlit run app.py
```

### Use the CLI
```bash
python cli.py --problem "Minimize transportation costs..."
```

### Python API
```python
from src.agents.problem_classifier import ProblemClassifier
from src.modeling.model_generator import ModelGenerator
from src.solvers.solver_interface import SolverInterface

# Classify problem
classifier = ProblemClassifier()
problem_data = classifier.classify("I need to minimize costs...")

# Generate model
generator = ModelGenerator()
model = generator.generate(problem_data)

# Solve
solver = SolverInterface()
solution = solver.solve(model)
```

## 📁 Project Structure

```
or-assistant/
├── src/
│   ├── agents/              # AI agents for problem understanding
│   ├── modeling/            # Mathematical model generators
│   ├── solvers/             # Solver interfaces
│   ├── interpreters/        # Results interpretation
│   ├── simulation/          # Simulation engines
│   └── utils/               # Helper functions
├── tests/                   # Unit and integration tests
├── data/
│   ├── examples/            # Example problems
│   └── templates/           # Problem templates
├── docs/                    # Documentation
├── config/                  # Configuration files
├── app.py                   # Streamlit web interface
├── cli.py                   # Command-line interface
└── requirements.txt         # Python dependencies
```

## 📖 Documentation

- [User Guide](docs/USER_GUIDE.md)
- [Development Guide](docs/DEVELOPMENT.md)
- [API Reference](docs/API_REFERENCE.md)
- [Examples](docs/EXAMPLES.md)

## 🧪 Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src tests/

# Run specific test
pytest tests/test_classifier.py
```

## 🗓️ Development Timeline

- **Weeks 1-2**: Foundation & Setup ✅
- **Weeks 3-4**: AI Agent & Problem Detection
- **Weeks 5-7**: Problem Modeling Engine
- **Weeks 8-9**: Solver Integration
- **Weeks 10-11**: Results Interpretation
- **Week 12**: Integration & Polish

## 🤝 Contributing

Contributions are welcome! Please read [CONTRIBUTING.md](CONTRIBUTING.md) for details.

## 📝 License

This project is licensed under the MIT License - see [LICENSE](LICENSE) file.

## 🙏 Acknowledgments

- Anthropic Claude AI
- Google OR-Tools
- COIN-OR PuLP
- CVXPY Team

## 📧 Contact

For questions or support, please open an issue or contact [your-email@example.com]

## 🎓 Academic Use

This project was developed as part of NDSU's initiative to bridge AI and local industry needs.
