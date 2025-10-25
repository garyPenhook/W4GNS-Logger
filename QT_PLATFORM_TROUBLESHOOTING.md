# Qt Platform Plugin Troubleshooting

## Issue: Qt Platform Plugin Not Found

When running the application, you may see an error like:

```
qt.qpa.plugin: Could not load the Qt platform plugin "xcb" in "" even though it was found.
This application failed to start because no Qt platform plugin could be initialized.
```

## Root Cause

The PyQt6 xcb platform plugin requires system libraries that may not be installed on your system:
- `libxcb-cursor0` (primary issue)
- Other related X11/xcb libraries

## Solution

The `run.sh` script automatically handles this by trying multiple platform backends in order:

1. **Wayland** - Modern display server protocol (if available)
2. **XCB** - Traditional X11 (requires libxcb-cursor0)
3. **Offscreen** - Headless mode for servers without a display

### If You're Running Headless (Server/SSH)

The script will automatically use offscreen mode. The GUI will run but not display on screen.

### If You Have a Desktop Environment

**Option 1: Install Missing System Dependencies (Recommended)**

On Ubuntu/Debian:
```bash
sudo apt-get update
sudo apt-get install -y libxcb-cursor0
```

On Fedora/RHEL:
```bash
sudo dnf install -y libxcb-cursor
```

On Arch:
```bash
sudo pacman -S libxcb xcb-util
```

On macOS (with Homebrew):
```bash
brew install qt libxcb
```

After installing, run the application normally:
```bash
./run.sh
```

**Option 2: Set Qt Platform Explicitly**

If you know which platform you want to use:

```bash
# Use Wayland (modern, faster)
QT_QPA_PLATFORM=wayland ./run.sh

# Use XCB (traditional X11)
QT_QPA_PLATFORM=xcb ./run.sh

# Use offscreen (headless, no display)
QT_QPA_PLATFORM=offscreen python src/main.py
```

**Option 3: Suppress Display and Use Web Interface**

For future versions with web UI support:
```bash
QT_QPA_PLATFORM=offscreen python src/main.py --headless --port 8080
```

## Platform Capabilities

| Platform | Display | X11/Wayland | GUI Features | Use Case |
|----------|---------|-----------|--------------|----------|
| **XCB** | ✓ | X11 | Full | Traditional Linux desktops |
| **Wayland** | ✓ | Wayland | Full | Modern Linux desktops (Ubuntu 22.04+) |
| **Offscreen** | ✗ | None | Limited | Servers, CI/CD, headless systems |

## Environment Variables

Control Qt behavior with these environment variables:

```bash
# Specify platform
export QT_QPA_PLATFORM=wayland

# Set plugin path (rarely needed)
export QT_QPA_PLATFORM_PLUGIN_PATH=/path/to/plugins

# Enable debug output
export QT_DEBUG_PLUGINS=1

# Scale factor for high-DPI displays
export QT_SCALE_FACTOR=2
```

## Advanced Troubleshooting

### Check Available Platforms

```bash
source venv/bin/activate
python -c "from PyQt6 import QtGui; print(QtGui.QGuiApplication.platformName())"
```

### List Installed Qt Plugins

```bash
python -c "from PyQt6.QtCore import QLibraryInfo; print(QLibraryInfo.LibraryPath.PluginsPath)"
```

### Enable Debug Output

```bash
export QT_DEBUG_PLUGINS=1
./run.sh 2>&1 | grep -i plugin
```

### Check X11/Wayland Status

```bash
# Check which display server is running
echo $DISPLAY              # X11
echo $WAYLAND_DISPLAY     # Wayland
```

## Getting Help

If you're still having issues:

1. **Check your display server**: Are you on X11, Wayland, or headless?
2. **Install system dependencies**: Follow the installation steps above
3. **Try different platforms**: The run.sh script tries multiple backends automatically
4. **Check logs**: Enable debug output as shown above
5. **Verify PyQt6**: `python -c "from PyQt6 import QtWidgets; print('OK')"`

## For Developers

To test platform availability programmatically:

```python
import os
from PyQt6.QtWidgets import QApplication

for platform in ['wayland', 'xcb', 'offscreen']:
    try:
        os.environ['QT_QPA_PLATFORM'] = platform
        app = QApplication([])
        print(f"{platform}: OK")
        app.quit()
    except Exception as e:
        print(f"{platform}: {e}")
```

---

**Note**: The application is designed to work on Windows, macOS, and Linux. Qt platform plugin issues are specific to Linux systems and usually resolved by installing the appropriate system libraries.
