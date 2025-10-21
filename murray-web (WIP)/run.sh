#!/bin/bash
# Run Murray Web UI

# Activate virtual environment
cd "$(dirname "$0")/.."
source env/bin/activate

# Run Flask app
cd murray-web
python app.py
