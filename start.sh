#!/bin/bash
# Start script for the Flask Agent

echo "Starting Flask Agent Server..."
echo "================================"
echo ""

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Virtual environment not found. Creating one..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Install requirements if needed
echo "Checking dependencies..."
pip install -q -r requirements.txt

echo ""
echo "Starting server..."
echo "================================"
python agent.py
