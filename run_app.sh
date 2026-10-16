#!/usr/bin/env bash
#
# Launch the integrated app (Tala + Muhammad's chatbot) in your browser.
#
#   ./run_app.sh           # the full Tala app, with the Ask chatbot built in
#   ./run_app.sh chatbot   # just Muhammad's standalone chatbot
#
# Stop it with Ctrl+C.

set -e

# Always resolve paths from this script's own folder, so it works from anywhere.
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV="$ROOT/Muhammad/.venv"
PY="$VENV/bin/python"

# First run: create the virtual environment and install everything.
if [ ! -x "$PY" ]; then
    echo "Setting up the virtual environment (first run only)..."
    python3 -m venv "$VENV"
    "$VENV/bin/pip" install --upgrade pip >/dev/null
    "$VENV/bin/pip" install -r "$ROOT/Muhammad/requirements.txt"
    # Extra libraries Tala needs on top of the chatbot's requirements.
    "$VENV/bin/pip" install py3langid deep-translator
fi

STREAMLIT="$VENV/bin/streamlit"

if [ "$1" = "chatbot" ]; then
    echo "Starting Muhammad's standalone chatbot at http://localhost:8501"
    cd "$ROOT/Muhammad"
    exec "$STREAMLIT" run app/main.py
else
    echo "Starting the Tala app (with the Ask chatbot) at http://localhost:8501"
    echo "Log in with  Student / 123456   (or  Admin / 123456 )"
    cd "$ROOT/Tala"
    exec "$STREAMLIT" run oshc_welcome.py
fi
