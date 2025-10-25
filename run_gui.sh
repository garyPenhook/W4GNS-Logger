#!/bin/bash
# GUI launcher script for W4GNS Ham Radio Logger
# This script attempts to launch the GUI in a graphical environment

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

# Ensure we're not in offscreen mode
unset QT_QPA_PLATFORM

# Try to detect and use the native display server
if [ -z "$DISPLAY" ] && [ -z "$WAYLAND_DISPLAY" ]; then
    echo "No display server detected. Attempting to start X11..."
    # Try to start X if available
    if command -v Xvfb &> /dev/null; then
        echo "Starting virtual X server..."
        Xvfb :99 -screen 0 1024x768x24 &
        export DISPLAY=:99
    else
        echo "ERROR: No display server found and Xvfb not available"
        echo "This is a headless system. Use one of these alternatives:"
        echo "  1. Run from a terminal with: ./run.sh"
        echo "  2. Use SSH with X11 forwarding: ssh -X user@host"
        echo "  3. Use a remote desktop solution (VNC, RDP)"
        exit 1
    fi
fi

# Try different Qt platforms in order of preference
for platform in wayland xcb; do
    echo "Trying $platform platform..."
    if QT_QPA_PLATFORM=$platform timeout 2 python -c "from PyQt6.QtWidgets import QApplication; QApplication([]).quit()" 2>/dev/null; then
        echo "Successfully using $platform platform"
        export QT_QPA_PLATFORM=$platform
        exec python src/main.py
        exit $?
    fi
done

echo "WARNING: Falling back to offscreen mode - GUI will not be visible"
export QT_QPA_PLATFORM=offscreen
python src/main.py
