#!/usr/bin/env bash
# ====================================================================
# SkyReserve — Airline Reservation & Flight Operations Database System
# Cross-platform startup script (Linux, macOS, Git Bash / WSL)
# ====================================================================

# Navigate to script directory
cd "$(dirname "$0")" || exit 1

echo "===================================================================="
echo "         SkyReserve - Airline Reservation & Flight Operations"
echo "===================================================================="
echo ""

# Check for Python (prefer local virtual environment if present)
if [ -f "./venv/bin/python" ]; then
    PY_CMD="./venv/bin/python"
elif command -v python3 &>/dev/null; then
    PY_CMD="python3"
elif command -v python &>/dev/null; then
    PY_CMD="python"
else
    echo "[!] Error: Python is not installed or not found in PATH."
    exit 1
fi

echo "[+] Using: $($PY_CMD --version)"

# Check and install requirements if Flask or mysql.connector is missing
if ! "$PY_CMD" -c "import flask; import mysql.connector" &>/dev/null; then
    echo "[+] Installing dependencies from requirements.txt..."
    "$PY_CMD" -m pip install -r requirements.txt
fi

URL="http://127.0.0.1:5001"
echo "[+] Launching web browser at $URL ..."

# Open browser based on OS environment
if command -v xdg-open &>/dev/null; then
    (sleep 1 && xdg-open "$URL") &
elif command -v open &>/dev/null; then
    (sleep 1 && open "$URL") &
elif command -v explorer.exe &>/dev/null; then
    (sleep 1 && explorer.exe "$URL") &
elif command -v start &>/dev/null; then
    (sleep 1 && start "$URL") &
fi

echo "[+] Starting Flask web server..."
echo "    Access the application at: $URL"
echo "    Press CTRL+C to stop."
echo "===================================================================="
echo ""

exec "$PY_CMD" app.py
