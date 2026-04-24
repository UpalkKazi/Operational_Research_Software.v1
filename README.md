# OR Assistant - AI-Powered Operations Research Solutions

An intelligent Streamlit application that helps users solve Operations Research problems using natural language descriptions. The system automatically classifies problems, generates mathematical models, solves them using appropriate solvers, and provides interpretations of results.

## 🚀 Features

- **Natural Language Input**: Describe your OR problem in plain English
- **Automatic Problem Classification**: AI identifies problem types (LP, IP, MIP, Transportation, etc.)
- **Model Generation**: Converts problem descriptions to mathematical models
- **Multiple Solvers**: Supports PuLP/CBC, CVXPY with various backends (OSQP, GLPK, SCIP)
- **File Upload Support**: Import problems from Excel, CSV, Word, PDF, or MPS files
- **MIPLIB Integration**: Direct access to benchmark problems from MIPLIB
- **Interactive Visualizations**: Charts and graphs to understand solutions
- **Result Interpretation**: AI explains what the solution means in business terms
- **🆕 Model Playground**: Interactive LaTeX equation editor to modify and experiment with OR models
  - Live mathematical notation editing with MathLive
  - Real-time constraint and variable adjustments
  - Side-by-side comparison of original vs modified solutions
  - Sensitivity analysis with visual sweep charts

## 📋 Prerequisites

- Python 3.11 or higher
- API keys for either:
  - Anthropic Claude API (recommended)
  - OpenAI API

## 🛠️ Installation

### Quick Start

1. **Clone the repository:**
```bash
git clone https://github.com/UpalkKazi/Operational_Research_Software.v1.git
cd Operational_Research_Software.v1
```

2. **Create a virtual environment:**
```bash
python -m venv venv
```

3. **Activate the virtual environment:**

**Windows:**
```bash
venv\Scripts\activate
```

**macOS/Linux:**
```bash
source venv/bin/activate
```

4. **Install dependencies:**
```bash
pip install -r requirements.txt
```

5. **Set up environment variables:**
   - Copy `.env.example` to `.env`:
     ```bash
     cp .env.example .env
     ```
   - Edit `.env` and add your API key:
     ```
     ANTHROPIC_API_KEY=your_anthropic_key_here
     # OR
     OPENAI_API_KEY=your_openai_key_here
     ```

6. **(Optional) Install additional solvers:**
```bash
# For SCIP support (requires conda):
conda install -c conda-forge pyscipopt

# For Gurobi (requires license):
pip install gurobipy
```

## 🏃‍♂️ Running the Application

```bash
streamlit run app.py
```

The application will open in your default browser at `http://localhost:8501`

## 📖 Usage

### Basic Workflow

1. **Describe Your Problem**: Enter a natural language description of your optimization problem
2. **Select Solver**: Choose a solver or let the app auto-detect the best one
3. **Solve**: Click "Solve Problem" to run the optimization pipeline
4. **View Results**: See the solution, interpretation, and visualizations

### Model Playground (New!)

After solving a problem, use the **🧮 Model Playground** tab to:
- **Edit Models**: Modify objectives and constraints using visual math notation
- **Test Scenarios**: Change parameters and see immediate impact on solutions
- **Sensitivity Analysis**: Sweep constraint bounds to understand solution behavior
- **Compare Results**: View original vs modified solutions side-by-side

### Example Problems

Click "Load Example" to see sample problems for:
- Linear Programming (furniture production)
- Integer Programming (delivery optimization)
- Transportation (minimize shipping costs)
- Assignment (worker-task allocation)
- Scheduling (job-machine scheduling)
- Knapsack (investment portfolio optimization)

### File Upload

Support for various file formats:
- **Spreadsheets**: .xlsx, .xls, .csv
- **Documents**: .docx, .doc, .txt, .pdf
- **MPS Files**: .mps, .mps.gz (standard OR format)

## 🏗️ Architecture

```
or-assistant/
├── app.py                    # Main Streamlit application
├── src/
│   ├── agents/              # AI components
│   │   ├── problem_classifier.py
│   │   └── result_interpreter.py
│   ├── ingestion/           # File parsing
│   │   ├── file_parser.py
│   │   ├── data_extractor.py
│   │   └── miplib_loader.py
│   ├── modeling/            # Model generation
│   │   └── model_generator.py
│   ├── solvers/             # Solver interfaces
│   │   ├── solver_interface.py
│   │   └── solver_router.py
│   ├── storage/             # Caching
│   │   └── miplib_cache.py
│   ├── ui/                  # UI components
│   │   ├── solver_settings.py
│   │   ├── solver_progress.py
│   │   ├── mathlive_component.py    # MathLive editor
│   │   └── mathlive_build/          # Component assets
│   ├── utils/               # Utilities
│   │   ├── api_client.py
│   │   └── model_editor.py          # Model editing logic
│   └── visualization/       # Chart generation
│       └── chart_generator.py
├── requirements.txt
├── .env.example
└── README.md
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- Built with [Streamlit](https://streamlit.io/)
- Uses [PuLP](https://coin-or.github.io/pulp/) and [CVXPY](https://www.cvxpy.org/) for optimization
- Powered by [Anthropic Claude](https://www.anthropic.com/) or [OpenAI](https://openai.com/) for AI capabilities
- MIPLIB problems from [MIPLIB 2017](https://miplib.zib.de/)

## 📧 Contact

For questions or support, please open an issue on GitHub.