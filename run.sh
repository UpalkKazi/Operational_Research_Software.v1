#!/bin/bash
# Helper script to run OR Assistant

# Activate virtual environment
source venv/bin/activate

# Run the command passed as arguments
python cli.py "$@"
