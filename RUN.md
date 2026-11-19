# How to Run OR Assistant

## Quick Start

### 1. Set Up Virtual Environment (Recommended)

```bash
# Create virtual environment
python -m venv venv

# Activate it
# On macOS/Linux:
source venv/bin/activate

# On Windows:
venv\Scripts\activate
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

If you encounter SSL certificate errors, try:
```bash
pip install --trusted-host pypi.org --trusted-host pypi.python.org --trusted-host files.pythonhosted.org -r requirements.txt
```

### 3. Configure Environment

Make sure you have a `.env` file with your API key:

```bash
# Copy example if you haven't already
cp .env.example .env

# Edit .env and add your API key:
# - OPENAI_API_KEY=your_key_here (for OpenAI)
# - ANTHROPIC_API_KEY=your_key_here (for Anthropic)
```

### 4. Run the Application

**Option A: Streamlit Web Interface**
```bash
streamlit run app.py
```
Then open your browser to the URL shown (usually http://localhost:8501)

**Option B: Command Line Interface**
```bash
python cli.py config          # Check configuration
python cli.py examples         # See example problems
python cli.py solvers          # List available solvers
python cli.py solve --problem "Your problem description here"
```

## Troubleshooting

### SSL Certificate Errors
If you get SSL errors when installing packages:
```bash
pip install --trusted-host pypi.org --trusted-host pypi.python.org --trusted-host files.pythonhosted.org <package_name>
```

### Missing Dependencies
Make sure all packages from `requirements.txt` are installed:
```bash
pip install streamlit python-dotenv anthropic openai pulp click rich
```

### API Key Issues
- Verify your `.env` file exists in the project root
- Check that your API key is correct
- Make sure there are no extra spaces or quotes around the key
- For OpenAI, the key should start with `sk-`
- For Anthropic, the key format varies

### Import Errors
If you get import errors, make sure you're in the project root directory:
```bash
cd /Users/harunpirim/Documents/GitHub/or-assistant
```

## Current Configuration

Your `.env` file is configured with:
- Model: `gpt-5.2-codex` (OpenAI)
- Make sure your `OPENAI_API_KEY` is set correctly
