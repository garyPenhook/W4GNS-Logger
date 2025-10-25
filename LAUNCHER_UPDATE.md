# Launcher Update - UV Integration

## What Was Fixed

The `launcher.py` script has been updated to properly use **UV** as the package manager, not pip.

### Changes Made

#### 1. Virtual Environment Creation
**Before**: Tried to use `uv venv` with fallback to standard `venv`
**After**: Uses `uv venv --python 3.14` directly (matching `run.sh`)

#### 2. Dependency Installation
**Before**: Failed because it looked for `pip` executable (doesn't exist until deps are installed)
**After**:
- Checks if dependencies already installed via `import PyQt6` test
- Uses `uv pip install --python <path-to-venv-python>`
- Skips installation if already complete

#### 3. Platform Detection
**Before**: Basic platform checks
**After**: Enhanced platform detection that tries wayland → xcb → offscreen (matching `run.sh`)

#### 4. Error Handling
**Before**: Generic error messages
**After**: Specific error messages directing users to UV documentation

---

## How It Works Now

### When You Double-Click `launcher.py`:

1. **Checks Virtual Environment**
   - If venv exists → proceed
   - If venv missing → create with `uv venv --python 3.14`

2. **Checks Dependencies**
   - If PyQt6 imports successfully → skip installation
   - If missing → install all with `uv pip install`

3. **Detects Display Platform** (Linux only)
   - Tests wayland platform
   - Falls back to xcb
   - Falls back to offscreen (headless)
   - Remembers choice for this run

4. **Starts Application**
   - Runs `src/main.py` with proper environment
   - Application initializes and displays

---

## Usage

### Standard Launch (Auto-Detect Everything)
```bash
python launcher.py
```

### Setup Only (Don't Launch App)
```bash
python launcher.py --setup-only
```

### With Debug Output
```bash
python launcher.py --debug
```

### Double-Click From File Manager
Just double-click `launcher.py` - works the same as terminal

---

## Command Line Options

| Option | Effect |
|--------|--------|
| (none) | Setup and launch application |
| `--setup-only` | Only setup, don't launch |
| `--debug` | Enable Qt debug logging |
| `--console` | Show console (for terminal use) |

---

## Why UV Instead of pip?

UV is the package manager specified in this project:

1. **100x faster** than pip for dependency resolution
2. **Reproducible** with `uv.lock` file
3. **Manages Python versions** - can download Python if needed
4. **Official integration** with this project

The launcher now properly uses UV throughout the setup process.

---

## What Still Works

All three ways to launch the application still work:

1. **From Terminal** (Recommended)
   ```bash
   ./run.sh              # Linux/macOS
   run.bat               # Windows
   ```

2. **From File Manager** (New - Most User-Friendly)
   ```bash
   Double-click: launcher.py
   ```

3. **From Application Menu** (Linux)
   ```bash
   cp W4GNS-Logger.desktop ~/.local/share/applications/
   ```

---

## Technical Details

### Virtual Environment Check
```python
# Fast check - just see if PyQt6 can import
subprocess.run([venv_python, "-c", "import PyQt6; print('OK')"])
```

### Dependency Installation
```bash
uv pip install --python /path/to/venv/bin/python -r requirements.txt
```

### Platform Detection (Linux)
```bash
# For each platform, test if it loads
QT_QPA_PLATFORM=wayland python -c "from PyQt6.QtWidgets import QApplication; QApplication([]).quit()"
```

---

## Troubleshooting

### Problem: `uv` command not found
**Cause**: UV not installed or not in PATH

**Solution**:
```bash
# Install UV
curl -LsSf https://astral.sh/uv/install.sh | sh

# Or use your package manager
sudo apt-get install uv        # Debian/Ubuntu
brew install uv                # macOS
choco install uv               # Windows
```

### Problem: Platform detection failing
**Cause**: Display server issue

**Solution**: Application will default to `offscreen` mode. For GUI:
1. Use SSH with X11: `ssh -X user@host`
2. Install VNC server
3. Install missing libs: `sudo apt-get install libxcb-cursor0`

### Problem: Slow first launch
**Cause**: First time setup with UV

**Solution**: Normal! Subsequent launches are instant.

---

## Files Modified

- **launcher.py** - Updated to use UV throughout
  - ✓ Proper venv creation with UV
  - ✓ Dependency check before install
  - ✓ UV-based installation
  - ✓ Enhanced platform detection
  - ✓ Better error messages

---

## Verification

Test that launcher works:

```bash
# Setup only (no app launch)
python launcher.py --setup-only

# Should output:
#   ✓ Using platform: [wayland|xcb|offscreen]
#   ✓ Dependencies already installed
#   Setup complete!
```

Test that app launches:

```bash
# Full launch (will run app)
timeout 5 python launcher.py || true

# Should output:
#   W4GNS Ham Radio Logger
#   Project root: ...
#   [Successfully initialized and started]
```

---

## Next Steps

1. **Try the launcher**:
   ```bash
   python launcher.py --setup-only
   ```

2. **Launch the app**:
   ```bash
   python launcher.py
   ```

3. **Or use run.sh** (if already tested):
   ```bash
   ./run.sh
   ```

4. **Create a desktop shortcut** for frequent use:
   ```bash
   cp W4GNS-Logger.desktop ~/.local/share/applications/
   ```

---

**The launcher is now production-ready and using UV correctly!**

73 de W4GNS 🎙️
