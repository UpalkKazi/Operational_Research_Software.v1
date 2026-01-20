# Quick Start Guide

Get OR Assistant running in 5 minutes!

## Step 1: Clone Repository

```bash
git clone https://github.com/yourusername/or-assistant.git
cd or-assistant
```

## Step 2: Set Up Python Environment

```bash
# Create virtual environment
python -m venv venv

# Activate it
# On macOS/Linux:
source venv/bin/activate

# On Windows:
venv\Scripts\activate
```

## Step 3: Install Dependencies

```bash
pip install -r requirements.txt
```

## Step 4: Configure API Key

1. Get your Anthropic API key from: https://console.anthropic.com
2. Create `.env` file:

```bash
cp .env.example .env
```

3. Edit `.env` and add your key:

```
ANTHROPIC_API_KEY=your_key_here
```

## Step 5: Run the App

```bash
streamlit run app.py
```

The app will open in your browser at `http://localhost:8501`

## Try an Example

Paste this into the app:

```
I need to minimize transportation costs between 3 warehouses and 4 stores.

Warehouse supplies: [100, 150, 200] units
Store demands: [80, 120, 90, 110] units

Shipping costs per unit:
From Warehouse 1: [$5, $8, $6, $7]
From Warehouse 2: [$6, $7, $9, $5]
From Warehouse 3: [$8, $6, $7, $9]

Find the optimal shipping plan.
```

Click "Solve Problem" and see the results!

## Using the CLI

```bash
# Solve a problem
python cli.py solve --problem "Your problem here"

# See examples
python cli.py examples

# Check configuration
python cli.py config

# List available solvers
python cli.py solvers
```

## Next Steps

1. Read the [User Guide](docs/USER_GUIDE.md)
2. Try more examples from `data/examples/`
3. Read the [Development Guide](docs/DEVELOPMENT.md) if contributing

## Troubleshooting

### "ModuleNotFoundError"
Make sure virtual environment is activated and dependencies installed:
```bash
source venv/bin/activate  # or venv\Scripts\activate
pip install -r requirements.txt
```

### "ANTHROPIC_API_KEY not found"
1. Check `.env` file exists
2. Verify the API key is correct
3. Make sure `.env` is in the project root directory

### "Solver not available"
Default PuLP solver (CBC) should work. For others:
```bash
# Check available solvers
python cli.py solvers
```

### App won't start
```bash
# Update Streamlit
pip install --upgrade streamlit

# Clear cache
streamlit cache clear
```

## Help & Support

- 📖 [Documentation](docs/)
- 💬 [Open an Issue](https://github.com/yourusername/or-assistant/issues)
- 📧 Contact: harun.pirim@ndsu.edu

Happy optimizing! 🎯
