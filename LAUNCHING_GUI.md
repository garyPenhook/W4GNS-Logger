# Launching the W4GNS Ham Radio Logger GUI

## For Non-Technical Users (Click to Launch)

### Windows
1. Locate the project folder
2. Double-click `run.bat`
3. The application will launch automatically

### Linux (GNOME/KDE/Cinnamon/Budgie)

#### Option 1: Application Menu (Easiest)
1. Copy the desktop entry:
   ```bash
   cp W4GNS-Logger.desktop ~/.local/share/applications/
   ```
2. Open your Application Menu and search for "W4GNS"
3. Click to launch

#### Option 2: Double-Click Launcher
1. Make the launcher executable:
   ```bash
   chmod +x launcher.py
   ```
2. Right-click `launcher.py` → Properties → Permissions → Check "Allow executing"
3. Double-click `launcher.py` to launch

#### Option 3: File Manager
1. Right-click `run_gui.sh` → Properties → Permissions → "Allow executing"
2. Double-click `run_gui.sh` to launch

### macOS
1. Make the launcher executable:
   ```bash
   chmod +x run_gui.sh
   ```
2. Right-click `run_gui.sh` → Open With → Terminal
3. Or create an alias to drag to Applications

---

## For Terminal Users (Already Started From Terminal)

### Linux/macOS
```bash
./run.sh
```
This is the fastest and most reliable method.

### Windows (PowerShell/CMD)
```cmd
run.bat
```

---

## Alternative Launchers

### Python Launcher (Most Portable)
Works on any system with Python installed:

```bash
python launcher.py                    # Normal launch
python launcher.py --debug            # Enable Qt debug logging
python launcher.py --setup-only       # Setup environment without launching
```

### GUI Launcher Script (Linux-Specific)
Handles display server detection:

```bash
./run_gui.sh
```

---

## Platform-Specific Solutions

### Linux - No GUI Appears

#### Problem 1: No Display Server
**Symptom**: Application runs but no window appears

**Solution A: Check Display Server**
```bash
# Check if X11 or Wayland is running
echo $DISPLAY              # X11 - should show :0 or similar
echo $WAYLAND_DISPLAY     # Wayland - should be set
```

**Solution B: Remote SSH**
If connecting via SSH, use X11 forwarding:
```bash
ssh -X username@hostname
cd "W4GNS Logger"
./run.sh
```

**Solution C: Install VNC Server**
```bash
# Ubuntu/Debian
sudo apt-get install -y tigervnc-server

# Connect from VNC viewer, then run:
./run.sh
```

#### Problem 2: Missing Qt Dependencies
**Symptom**: "Could not load the Qt platform plugin"

**Solution**:
```bash
# Ubuntu/Debian
sudo apt-get install -y libxcb-cursor0

# Fedora/RHEL
sudo dnf install -y libxcb-cursor

# Then retry:
./run.sh
```

See [QT_PLATFORM_TROUBLESHOOTING.md](QT_PLATFORM_TROUBLESHOOTING.md) for more details.

### Windows - "Python Not Found"

**Solution**: Make sure you double-click `run.bat`, not the Python scripts.

### macOS - "Permission Denied"

**Solution**:
```bash
chmod +x run.sh run_gui.sh launcher.py
./run.sh
```

---

## Creating Desktop Shortcuts

### Windows Shortcut
1. Right-click desktop → New → Shortcut
2. Location: `C:\path\to\run.bat`
3. Name: "W4GNS Ham Radio Logger"
4. Click Finish
5. Right-click shortcut → Properties → Advanced → Check "Run as administrator" (optional)

### Linux Desktop Icon
```bash
# Create in ~/.local/share/applications/
cp W4GNS-Logger.desktop ~/.local/share/applications/
# Update the Exec path if needed
nano ~/.local/share/applications/W4GNS-Logger.desktop
```

### macOS Application Bundle
```bash
mkdir -p "W4GNS Logger.app/Contents/MacOS"
cat > "W4GNS Logger.app/Contents/MacOS/launcher" << 'EOF'
#!/bin/bash
cd "$(dirname "$0")/../../../"
./run.sh
EOF
chmod +x "W4GNS Logger.app/Contents/MacOS/launcher"
# Drag to Applications folder
```

---

## Troubleshooting

| Symptom | Cause | Solution |
|---------|-------|----------|
| "File not found" | Wrong working directory | Use full path or CD to project first |
| "Permission denied" | Script not executable | `chmod +x run.sh` |
| No GUI window | No display server | SSH with `-X` or install VNC |
| "Qt platform plugin" error | Missing libraries | Install libxcb-cursor0 (see above) |
| Window appears then closes | Python error | Run from terminal to see error message |
| Very slow startup | Dependencies installing | Wait - first run takes longer |

---

## Advanced Usage

### Environment Variables

Control behavior with these variables:

```bash
# Force specific Qt platform
export QT_QPA_PLATFORM=wayland
./run.sh

# Enable debugging
export QT_DEBUG_PLUGINS=1
./run.sh

# Scale for high-DPI displays
export QT_SCALE_FACTOR=2
./run.sh

# Custom database location
export W4GNS_DB_PATH=/path/to/mylogbook.db
./run.sh
```

### Running from Application Launcher (Systemd)

Create `~/.config/systemd/user/w4gns-logger.service`:

```ini
[Unit]
Description=W4GNS Ham Radio Logger
After=network.target

[Service]
Type=simple
ExecStart=/path/to/W4GNS Logger/run.sh
Restart=on-failure
Environment="QT_QPA_PLATFORM=wayland"

[Install]
WantedBy=default.target
```

Then:
```bash
systemctl --user enable w4gns-logger
systemctl --user start w4gns-logger
```

---

## Quick Reference

**Preferred Method**: Open terminal, navigate to project, type:
```bash
./run.sh
```

**Quickest GUI Launch**: Double-click `launcher.py`

**Fastest Setup**:
```bash
chmod +x launcher.py run.sh
cp W4GNS-Logger.desktop ~/.local/share/applications/  # Linux only
```

---

## Next Steps

1. Launch the application using your preferred method above
2. See [README.md](README.md) for usage instructions
3. Check the Logging tab to create your first contact entry
4. See [RUNNING_THE_APPLICATION.md](RUNNING_THE_APPLICATION.md) for advanced options

**Stuck?** Check [QT_PLATFORM_TROUBLESHOOTING.md](QT_PLATFORM_TROUBLESHOOTING.md) or review the "Troubleshooting" section above.
