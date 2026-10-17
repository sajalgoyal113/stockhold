#!/bin/bash
cd "$(dirname "$0")"

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    source venv/bin/activate
fi

echo "========================================================"
echo "⚡ Starting StockHold — Simplifying stock analysis for investors"
echo "========================================================"
echo "Access the app in your browser at: http://localhost:8501"
echo "========================================================"

streamlit run app.py --server.port 8501 --server.headless false
