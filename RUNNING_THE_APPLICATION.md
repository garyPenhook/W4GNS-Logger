# Running W4GNS Ham Radio Logger

This guide covers all the different ways to run the application depending on your environment and preferences.

## Quick Reference

| Method | Platform | Terminal Required | GUI | Command |
|--------|----------|-------------------|-----|---------|
| **Terminal** | Linux/macOS | ✓ | ✓ | `./run.sh` |
| **Terminal** | Windows | ✓ | ✓ | `run.bat` |
| **Desktop Launcher** | Linux | ✗ | ✓ | Click icon |
| **GUI Launcher** | Linux | ✗ | ✓ | `./run_gui.sh` |
| **SSH with X11** | Remote | ✗ | ✓ | `ssh -X user@host` |
| **Programmatic** | Any | - | ✗ | `python src/main.py` |

---

## Method 1: From Terminal (Recommended for Development)

### Linux/macOS

```bash
cd "W4GNS Logger"
./run.sh
```

The application will:
1. Create a virtual environment if needed
2. Install dependencies
3. Detect the best available display platform (Wayland → XCB → Offscreen)
4. Launch the GUI

### Windows

```cmd
cd "W4GNS Logger"
run.bat
```

**Note**: On Windows, GUI will appear directly. Press `Ctrl+C` in the terminal to close the app.

---

## Method 2: Desktop Launcher (No Terminal)

### Linux GNOME/KDE/Cinnamon

**Option A: Simple Copy**

```bash
cp W4GNS-Logger.desktop ~/.local/share/applications/
```

Then search for "W4GNS" in your applications menu and click to launch.

**Option B: System-Wide Installation**

```bash
sudo cp W4GNS-Logger.desktop /usr/share/applications/
```

Available to all users in applications menu.

**Option C: Manual Setup**

1. Copy the desktop file to your applications folder
2. Edit the `Exec=` line to match your installation path
3. Make sure `run_gui.sh` is executable: `chmod +x run_gui.sh`

### Windows

Create a Windows shortcut:

1. Right-click on desktop → New → Shortcut
2. Location: `C:\Path\To\W4GNS Logger\run.bat`
3. Name: "W4GNS Ham Radio Logger"
4. Right-click shortcut → Properties → Change Icon (optional)
5. Double-click to launch

Or use PowerShell:

```powershell
$shell = New-Object -ComObject WScript.Shell
$shortcut = $shell.CreateShortcut("$env:USERPROFILE\Desktop\W4GNS Logger.lnk")
$shortcut.TargetPath = "C:\Path\To\W4GNS Logger\run.bat"
$shortcut.WorkingDirectory = "C:\Path\To\W4GNS Logger"
$shortcut.Save()
```

### macOS

Create an application wrapper:

```bash
mkdir -p "W4GNS Logger.app/Contents/MacOS"
cat > "W4GNS Logger.app/Contents/MacOS/launcher" << 'EOF'
#!/bin/bash
cd "$(dirname "$0")/../../../"
./run_gui.sh
EOF
chmod +x "W4GNS Logger.app/Contents/MacOS/launcher"
```

Then drag to Applications folder.

---

## Method 3: GUI Launcher Script (Linux)

If you want a launcher that handles display detection automatically:

```bash
chmod +x run_gui.sh
./run_gui.sh
```

This script:
- Checks for active display server
- Falls back to Xvfb (virtual display) if available
- Uses platform detection to find best Qt backend
- Shows clear errors if environment is truly headless

---

## Method 4: SSH with X11 Forwarding (Remote Linux)

If you're connecting via SSH and want to display the GUI on your local machine:

```bash
# From your local machine:
ssh -X user@remote-host
cd "W4GNS Logger"
./run.sh
```

Requirements:
- X11 forwarding enabled on SSH server
- X11 server running on your local machine (XQuartz on macOS, or WSL on Windows)

### SSH Configuration

Edit `~/.ssh/config` on your local machine:

```
Host ham-logger
    HostName remote.example.com
    User username
    ForwardX11 yes
    ForwardX11Trusted yes
```

Then connect with: `ssh ham-logger`

---

## Method 5: Using Screen or Tmux (Persistent Sessions)

For running on a server that you'll connect to multiple times:

### With Screen

```bash
screen -S w4gns
cd "W4GNS Logger"
./run.sh

# To detach: Ctrl+A then D
# To reattach: screen -r w4gns
```

### With Tmux

```bash
tmux new-session -d -s w4gns
tmux send-keys -t w4gns "cd 'W4GNS Logger' && ./run.sh" Enter

# To attach: tmux attach -t w4gns
```

---

## Method 6: Python Virtual Environment (Manual)

For advanced users who want to run it directly:

```bash
cd "W4GNS Logger"

# Create and activate venv
uv venv --python 3.14 venv
source venv/bin/activate  # Linux/macOS
# OR
venv\Scripts\activate.bat  # Windows

# Install dependencies
uv pip install --python ./venv/bin/python -r requirements.txt

# Set display platform (Linux only)
export QT_QPA_PLATFORM=xcb  # or wayland, offscreen

# Run
python src/main.py
```

---

## Method 7: Docker Container (Advanced)

For reproducible environments, create a Dockerfile:

```dockerfile
FROM ubuntu:22.04

RUN apt-get update && apt-get install -y \
    python3.14 \
    libxcb-cursor0 \
    libqt6gui6 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY . .

RUN pip install -r requirements.txt

CMD ["python", "src/main.py"]
```

Build and run:

```bash
docker build -t w4gns-logger .
docker run -it --net=host w4gns-logger
```

---

## Troubleshooting

### Issue: GUI window doesn't appear

**Check your display server:**
```bash
echo $DISPLAY    # X11
echo $WAYLAND_DISPLAY  # Wayland
```

**If empty:** You're on a headless system or SSH without X11 forwarding.

**Solution:** Use SSH with X11 forwarding or install a VNC server.

### Issue: "Could not load the Qt platform plugin"

See [QT_PLATFORM_TROUBLESHOOTING.md](QT_PLATFORM_TROUBLESHOOTING.md) for detailed solutions.

### Issue: Permission denied when running

Make scripts executable:

```bash
chmod +x run.sh run_gui.sh
```

### Issue: Port conflicts or permission errors

Try running as user (not root):

```bash
# Don't use sudo - it causes permission issues
./run.sh
```

---

## Advanced Options

### Enable Verbose Logging

```bash
export QT_DEBUG_PLUGINS=1
export QT_DEBUG_EVENTS=1
./run.sh 2>&1 | tee app.log
```

### Set Qt Scale Factor (High-DPI Displays)

```bash
export QT_SCALE_FACTOR=2
./run.sh
```

### Force Specific Platform

```bash
export QT_QPA_PLATFORM=wayland
./run.sh
```

### Custom Database Location

```bash
export W4GNS_DB_PATH=/path/to/custom.db
python src/main.py
```

### Run in Headless Mode (No GUI)

```bash
export QT_QPA_PLATFORM=offscreen
python src/main.py --headless
```

---

## Platform-Specific Notes

### Linux

- **Best performance**: Use Wayland on modern systems
- **Maximum compatibility**: Use XCB on older systems
- **Headless servers**: Use offscreen mode
- **Remote display**: Use SSH with X11 forwarding

### macOS

- PyQt6 works natively on macOS
- `run_gui.sh` isn't needed; use `run.sh` directly
- Set `export QT_SCALE_FACTOR=1.5` for Retina displays

### Windows

- `run.bat` handles everything automatically
- Create shortcuts for easy access
- No additional display configuration needed

---

## Next Steps

1. Choose your preferred launch method from above
2. If GUI doesn't appear, check [QT_PLATFORM_TROUBLESHOOTING.md](QT_PLATFORM_TROUBLESHOOTING.md)
3. Create a desktop shortcut/launcher for repeated use
4. Check [README.md](README.md) for usage instructions

---

**Need Help?** Check the troubleshooting guides or review environment setup in README.md.
