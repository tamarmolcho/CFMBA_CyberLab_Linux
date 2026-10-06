#!/bin/bash
# ==============================================================================
# CFMBA CyberLab Operations Center - Turnkey Kali Linux Launcher
# Developed by: Tamar Molcho
# Academic Supervisor: Mr. Jack Altal
# Institution: Ono Academic College
# ==============================================================================

set -e

# Resolve directory of this script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "========================================================================"
echo "⚡ CFMBA CyberLab Operations Center - Starting on Kali Linux"
echo "========================================================================"

# 1. Verify Python 3
if ! command -v python3 &> /dev/null; then
    echo "[!] Error: python3 is not installed on this system."
    echo "[*] Please run: sudo apt update && sudo apt install -y python3 python3-venv python3-pip"
    exit 1
fi

PY_VER=$(python3 --version)
echo "[+] Detected: $PY_VER"

# 2. Virtual Environment Setup (Handles Debian/Kali PEP 668 safely)
VENV_DIR="$SCRIPT_DIR/.venv"
USE_SYSTEM_PYTHON=0

if [ ! -d "$VENV_DIR" ]; then
    echo "[*] Creating dedicated virtual environment at .venv..."
    if python3 -m venv "$VENV_DIR" 2>/dev/null; then
        echo "[+] Virtual environment created successfully."
    else
        echo "[!] Notice: python3-venv package not found. Attempting to use system python..."
        USE_SYSTEM_PYTHON=1
    fi
fi

if [ $USE_SYSTEM_PYTHON -eq 0 ] && [ -f "$VENV_DIR/bin/activate" ]; then
    source "$VENV_DIR/bin/activate"
    PYTHON_EXEC="$VENV_DIR/bin/python3"
    PIP_EXEC="$VENV_DIR/bin/pip"
else
    PYTHON_EXEC="python3"
    PIP_EXEC="pip3"
fi

# 3. Check and install dependencies
echo "[*] Checking Python dependencies (Flask, psutil, Pillow)..."
if ! $PYTHON_EXEC -c "import flask, psutil" 2>/dev/null; then
    echo "[*] Installing required packages from requirements.txt..."
    if [ $USE_SYSTEM_PYTHON -eq 1 ]; then
        $PIP_EXEC install -r requirements.txt --break-system-packages 2>/dev/null || $PIP_EXEC install -r requirements.txt
    else
        $PIP_EXEC install --upgrade pip --quiet 2>/dev/null || true
        $PIP_EXEC install -r requirements.txt --quiet
    fi
else
    echo "[+] Core dependencies already satisfied."
fi

# 4. Make all original bash scripts executable
echo "[*] Applying execution permissions to cyber scripts..."
chmod +x scripts/*.sh 2>/dev/null || true
chmod +x run.sh 2>/dev/null || true

# 5. Determine Kali Host IP address
KALI_IP=$(hostname -I 2>/dev/null | awk '{print $1}' || echo "127.0.0.1")
PORT="${PORT:-5001}"

echo "========================================================================"
echo "🛡️  CFMBA CyberLab Operations Center is ready!"
echo "========================================================================"
echo "📍 Local Web Access:     http://127.0.0.1:$PORT"
if [ "$KALI_IP" != "127.0.0.1" ] && [ -n "$KALI_IP" ]; then
    echo "🌐 Remote / VM Network:  http://$KALI_IP:$PORT"
fi
echo "🤖 CyberCopilot AI:      ONLINE & OPERATIONAL"
echo "📊 VirtualBox Fleet:     Virtualization Engine & Lab Systems Synchronized"
echo "⚡ Mode:                 Cyber Range Simulation & Real VBox Auto-Sync"
echo "========================================================================"
echo "Press Ctrl+C to stop the server."
echo ""

# 6. Launch Application
APP_FILE="app.py"
if [ ! -f "$APP_FILE" ]; then
    echo "[!] Error: $APP_FILE not found in $(pwd)!"
    exit 1
fi

export PORT="$PORT"
export PYTHONUNBUFFERED=1
echo "[*] Launching CFMBA CyberLab ($APP_FILE) on port $PORT..."
exec $PYTHON_EXEC "$APP_FILE"
