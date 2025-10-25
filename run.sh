#!/bin/bash
# Quick-start script for W4GNS Ham Radio Logger
# Uses UV with Python 3.14

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Check if venv exists
if [ ! -d "venv" ]; then
    echo "Virtual environment not found. Creating with Python 3.14..."
    uv venv --python 3.14 venv
    echo "Installing dependencies with uv..."
    uv pip install --python ./venv/bin/python -r requirements.txt
fi

# Activate virtual environment
source venv/bin/activate

# Try to run with different platform plugins if needed
echo "Attempting to start application..."

# First, try to set DISPLAY if not set but X is running
if [ -z "$DISPLAY" ] && [ -z "$WAYLAND_DISPLAY" ]; then
    # Check if X is running
    if ps aux | grep -q "[X]org.*:0"; then
        export DISPLAY=:0
        echo "✓ Detected X server on :0, setting DISPLAY"
    fi
fi

# Test which platform is available
for platform in xcb wayland offscreen; do
    echo "Testing $platform platform..."
    if QT_QPA_PLATFORM=$platform python -c "from PyQt6.QtWidgets import QApplication; QApplication([]).quit()" 2>/dev/null; then
        echo "✓ Using $platform platform"
        export QT_QPA_PLATFORM=$platform
        python src/main.py
        exit $?
    fi
done

echo "No suitable Qt platform found!"
exit 1
