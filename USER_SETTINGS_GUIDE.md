# User Settings & Configuration Guide

## Overview

W4GNS Ham Radio Logger uses a YAML configuration file to store all user settings. Settings are persistent across sessions and can be modified either through the GUI or by directly editing the configuration file.

---

## Configuration File Location

### Linux/macOS
```
~/.w4gns_logger/config.yaml
```
Expand `~` to your home directory. Example:
```
/home/username/.w4gns_logger/config.yaml
/Users/username/.w4gns_logger/config.yaml
```

### Windows
```
%USERPROFILE%\.w4gns_logger\config.yaml
```
Expand `%USERPROFILE%` to your user folder. Example:
```
C:\Users\username\.w4gns_logger\config.yaml
```

---

## Viewing Your Configuration

### From GUI (Recommended)
1. Click **Settings** tab
2. Click **Raw Config** sub-tab
3. View your complete configuration in YAML format

### From Command Line
```bash
cat ~/.w4gns_logger/config.yaml
```

### From File Manager
- Linux/macOS: Press Ctrl+H to show hidden files, navigate to `.w4gns_logger`
- Windows: Type `%USERPROFILE%\.w4gns_logger` in address bar

---

## Configuration Sections

### General Settings
```yaml
general:
  operator_callsign: "W4GNS"      # Your ham radio callsign
  home_grid: "FN20qd"            # Your Maidenhead grid square
  default_mode: "SSB"            # Default mode for new contacts
  default_power: 100             # Default TX power in watts
  auto_save_interval: 60         # Auto-save interval in seconds
```

**What These Do:**
- `operator_callsign` - Used in contact records and reports
- `home_grid` - Your grid square for distance calculations
- `default_mode` - Pre-selected mode when logging new contacts
- `default_power` - Pre-filled TX power field
- `auto_save_interval` - How often app auto-saves data

---

### Database Settings
```yaml
database:
  location: "/home/username/.w4gns_logger/contacts.db"
  backup_enabled: true           # Enable automatic backups
  backup_interval: 24            # Backup every N hours
```

**What These Do:**
- `location` - Where your contact database is stored
- `backup_enabled` - Auto-create backups
- `backup_interval` - Hours between backups (24 = daily)

**Important:** Don't move the database file unless you know what you're doing!

---

### User Interface Settings
```yaml
ui:
  theme: "light"                 # "light" or "dark"
  font_size: 10                  # Font size in points (8-20)
  window_geometry: null          # Window position/size (auto-managed)
```

**What These Do:**
- `theme` - Application color scheme
- `font_size` - GUI text size
- `window_geometry` - Stores window position (don't edit manually)

---

### DX Cluster Settings
```yaml
dx_cluster:
  enabled: true                  # Enable DX cluster feature
  auto_connect: false            # Auto-connect on startup
  heartbeat_interval: 60         # Connection heartbeat in seconds
```

**What These Do:**
- `enabled` - Turn DX cluster on/off
- `auto_connect` - Auto-connect when app starts
- `heartbeat_interval` - How often to check connection (seconds)

---

### QRZ.com Settings
```yaml
qrz:
  enabled: false                 # Enable QRZ integration
  auto_upload: false             # Auto-upload contacts to QRZ
```

**What These Do:**
- `enabled` - Enable QRZ.com features
- `auto_upload` - Automatically sync contacts with QRZ logbook

**Note:** Requires QRZ.com account and API key (to be configured)

---

### Awards Tracking Settings
```yaml
awards:
  enabled: true                  # Enable award tracking
  auto_calculate: true           # Auto-calculate award progress
```

**What These Do:**
- `enabled` - Enable DXCC, WAS, WPX tracking
- `auto_calculate` - Auto-calculate progress on each contact save

---

## How to Edit Settings

### Method 1: GUI (Easiest)
1. Launch application
2. Click **Settings** tab
3. Edit fields in respective sections (General, Database, UI, Features)
4. Click **Save Settings**

**Advantages:**
- User-friendly
- Validates input
- No syntax errors possible
- Organized by category

### Method 2: Edit Raw YAML in GUI
1. Click **Settings** tab
2. Click **Raw Config** sub-tab
3. Edit YAML directly
4. Click **Save Settings**

**Advantages:**
- Full control
- See entire config
- No tab switching

### Method 3: Edit File Directly
1. Open file manager
2. Navigate to `~/.w4gns_logger/config.yaml`
3. Right-click → Open With → Text Editor
4. Edit YAML
5. Save file

**Advantages:**
- Can edit without launching app
- Use your preferred editor
- Version control friendly

**Disadvantages:**
- Easy to make syntax errors
- App must be closed (or reload config)

---

## Default Configuration

When first launched, app creates this default config:

```yaml
general:
  operator_callsign: MYCALL
  home_grid: FN20qd
  default_mode: SSB
  default_power: 100
  auto_save_interval: 60

database:
  location: ~/.w4gns_logger/contacts.db
  backup_enabled: true
  backup_interval: 24

ui:
  theme: light
  font_size: 10
  window_geometry: null

dx_cluster:
  enabled: true
  auto_connect: false
  heartbeat_interval: 60

qrz:
  enabled: false
  auto_upload: false

awards:
  enabled: true
  auto_calculate: true
```

---

## Common Configuration Changes

### Change Your Callsign
**GUI:** Settings → General → Operator Callsign

**YAML:**
```yaml
general:
  operator_callsign: "W4GNS"  # Change MYCALL to your call
```

### Move Database Location
⚠️ **Warning:** Advanced procedure

**GUI:**
1. Settings → Database → Database Location
2. Click Browse
3. Select new location
4. ⚠️ Manually move the old database file to new location
5. Click Save

**Command Line:**
```bash
# Move database
mv ~/.w4gns_logger/contacts.db /path/to/new/location/contacts.db

# Edit config
nano ~/.w4gns_logger/config.yaml
# Update: database.location: /path/to/new/location/contacts.db
```

### Disable DX Cluster Feature
**GUI:** Settings → Features → Uncheck "Enable DX Cluster"

**YAML:**
```yaml
dx_cluster:
  enabled: false  # Change from true
```

### Enable Dark Theme
**GUI:** Settings → UI → Theme → Select "dark"

**YAML:**
```yaml
ui:
  theme: "dark"  # Change from "light"
```

### Reset to Defaults
**GUI:** Settings → Click "Reset to Defaults" button

**Command Line:**
```bash
rm ~/.w4gns_logger/config.yaml
# App will recreate with defaults on next launch
```

---

## YAML Format Guide

If editing YAML directly, follow these rules:

### Valid YAML Syntax
```yaml
# Key-value pairs
key: value

# Strings (with or without quotes)
name: "John"
name: John

# Numbers
count: 42
temperature: 98.6

# Booleans
enabled: true
enabled: false

# Nested sections
section:
  subsection: value
  another: 123
```

### Invalid YAML Syntax (Don't Do This)
```yaml
# Missing colon
name John              # ✗ WRONG

# Wrong indentation
settings:
  enabled: true       # ✗ WRONG (use spaces, not tabs)

# Unclosed quotes
name: "John          # ✗ WRONG (missing closing quote)

# Tabs instead of spaces
key:	value          # ✗ WRONG (tab before value)
```

---

## Making Changes Without GUI

### Step 1: Open Configuration File
```bash
# Linux/macOS
nano ~/.w4gns_logger/config.yaml

# Windows (PowerShell)
notepad $env:USERPROFILE\.w4gns_logger\config.yaml
```

### Step 2: Edit Values
```yaml
general:
  operator_callsign: "W4GNS"        # Change this
  home_grid: "EN87"                 # And this
```

### Step 3: Save and Close
- **Nano:** Ctrl+O, Enter, Ctrl+X
- **Notepad:** Ctrl+S, then close
- **VS Code:** Ctrl+S

### Step 4: Reload Configuration
- **Close and restart app** (quickest)
- Or use Settings → Reset/Save (in GUI)

---

## Backing Up Your Settings

### Backup Configuration
```bash
# Linux/macOS
cp ~/.w4gns_logger/config.yaml ~/backups/config-backup.yaml

# Windows
copy %USERPROFILE%\.w4gns_logger\config.yaml C:\backups\config-backup.yaml
```

### Restore Configuration
```bash
# Linux/macOS
cp ~/backups/config-backup.yaml ~/.w4gns_logger/config.yaml

# Windows
copy C:\backups\config-backup.yaml %USERPROFILE%\.w4gns_logger\config.yaml
```

---

## Troubleshooting

### Problem: Settings won't save
**Solution:**
1. Close app
2. Check file permissions: `ls -la ~/.w4gns_logger/`
3. Should be readable/writable by you
4. Restart app

### Problem: Invalid YAML error
**Solution:**
1. Check syntax:
   - All colons followed by space
   - Consistent indentation (spaces only)
   - Matching quotes
2. Or reset: `rm ~/.w4gns_logger/config.yaml`

### Problem: Settings revert on restart
**Solution:**
1. File not saving: Check directory permissions
2. App not reading: Try restarting app twice
3. Or reset and reconfigure: `rm ~/.w4gns_logger/config.yaml`

### Problem: Can't find config file
**Solution:**
1. Show hidden files:
   - Linux/macOS: Press Ctrl+H in file manager
   - Windows: Check "View Hidden Files" in View menu
2. Or use terminal:
   ```bash
   find ~ -name "config.yaml" 2>/dev/null
   ```

---

## Advanced: Version Control

If you use Git, you can track your settings:

```bash
# Initialize git in config directory
cd ~/.w4gns_logger
git init

# Add config file
git add config.yaml
git commit -m "Initial settings configuration"

# After making changes
git add config.yaml
git commit -m "Updated callsign and grid square"

# See history
git log --oneline
git diff HEAD~1  # Compare with previous version
```

---

## Settings Persistence

### What Gets Saved
- ✅ General settings (callsign, grid, default mode, power)
- ✅ Database location
- ✅ UI preferences (theme, font size)
- ✅ Feature toggles (cluster, QRZ, awards)
- ✅ Window geometry (position/size)

### What Doesn't Get Saved
- ❌ Contact data (stored in database, not config)
- ❌ Award progress (stored in database)
- ❌ Temporary state (only during current session)

### Automatic Operations
- **On Save:** Writes settings to config.yaml
- **On Start:** Reads config.yaml
- **On Reset:** Overwrites with defaults
- **On Crash:** Uses last saved settings

---

## Next Steps

1. **Configure Your Details**
   - Set your callsign
   - Set your grid square
   - Choose your default mode

2. **Test Different Settings**
   - Try different themes
   - Adjust font size
   - Enable/disable features

3. **Back Up Configuration**
   - Save a copy of config.yaml
   - Keep in cloud storage
   - Or use version control

4. **Customize Further**
   - Edit raw YAML for advanced options
   - Try different database locations
   - Configure QRZ.com integration

---

## Support

**Question about a setting?**
- Hover over field labels in Settings tab
- Read this guide
- Check settings description

**Settings not working?**
- Restart the application
- Check file permissions
- Verify YAML syntax
- Reset to defaults and reconfigure

**Want to customize further?**
- Edit `config.yaml` directly
- Add custom sections (not deleted on updates)
- Create environment-specific configs

---

**Your settings are portable!** Copy `~/.w4gns_logger/config.yaml` to any other installation and your settings will carry over.

**73 de W4GNS** 🎙️
