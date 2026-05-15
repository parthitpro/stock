#!/bin/bash

echo "========================================"
echo " NSE AI Stock Analyst - Starting System"
echo "========================================"
echo ""

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "ERROR: Python 3 is not installed or not in PATH"
    echo "Please install Python 3.10+ first"
    exit 1
fi

echo "Python version: $(python3 --version)"

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
    if [ $? -ne 0 ]; then
        echo "ERROR: Failed to create virtual environment"
        exit 1
    fi
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt --quiet
if [ $? -ne 0 ]; then
    echo "WARNING: Some dependencies may have failed to install"
fi

# Check if .env exists
if [ ! -f ".env" ]; then
    echo ""
    echo "WARNING: .env file not found!"
    echo "Please create a .env file with your OPENROUTER_API_KEY"
    echo "Example:"
    echo "OPENROUTER_API_KEY=sk-or-v1-your-key-here"
    echo ""
    read -p "Press Enter to continue anyway or Ctrl+C to cancel..."
fi

# Start the server
echo ""
echo "========================================"
echo " Starting FastAPI Server + Frontend"
echo " Access dashboard at: http://localhost:8000"
echo " API docs at: http://localhost:8000/docs"
echo "========================================"
echo ""

python main.py
