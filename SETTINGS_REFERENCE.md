# Quick Settings Reference Card

## Configuration File Location

| OS | Path |
|----|----|
| Linux | `~/.w4gns_logger/config.yaml` |
| macOS | `~/.w4gns_logger/config.yaml` |
| Windows | `%USERPROFILE%\.w4gns_logger\config.yaml` |

## Three Ways to Change Settings

### 1️⃣ GUI (Easiest)
```
Launch App → Settings Tab → Edit Fields → Save Settings
```

### 2️⃣ GUI Raw Editor
```
Launch App → Settings Tab → Raw Config → Edit YAML → Save Settings
```

### 3️⃣ Direct File Edit
```
~/.w4gns_logger/config.yaml → Text Editor → Edit → Save
```

---

## Essential Settings

### Your Identity
```yaml
general:
  operator_callsign: "W4GNS"     # Your ham callsign
  home_grid: "FN20qd"           # Your grid square (Maidenhead)
```

### Default Contact Settings
```yaml
general:
  default_mode: "SSB"           # Default mode (CW, SSB, FM, RTTY, etc)
  default_power: 100            # Default TX power in watts
```

### Database Location
```yaml
database:
  location: "/home/user/.w4gns_logger/contacts.db"
```

### Theme & Display
```yaml
ui:
  theme: "light"                # or "dark"
  font_size: 10                 # 8-20 points
```

---

## All Settings

```yaml
general:
  operator_callsign: "MYCALL"       # Your callsign
  home_grid: "FN20qd"              # Your grid square
  default_mode: "SSB"              # Default mode for logging
  default_power: 100               # Default TX power (watts)
  auto_save_interval: 60           # Save interval (seconds)

database:
  location: "~/.w4gns_logger/contacts.db"    # DB file path
  backup_enabled: true             # Enable auto-backup
  backup_interval: 24              # Backup interval (hours)

ui:
  theme: "light"                   # Theme (light/dark)
  font_size: 10                    # Font size (8-20 pt)
  window_geometry: null            # Auto-managed

dx_cluster:
  enabled: true                    # Enable DX cluster
  auto_connect: false              # Auto-connect on startup
  heartbeat_interval: 60           # Check interval (seconds)

qrz:
  enabled: false                   # Enable QRZ integration
  auto_upload: false               # Auto-upload contacts

awards:
  enabled: true                    # Enable award tracking
  auto_calculate: true             # Auto-calc progress
```

---

## Quick Commands

### View Current Config
```bash
cat ~/.w4gns_logger/config.yaml
```

### Reset to Defaults
```bash
rm ~/.w4gns_logger/config.yaml
# App recreates on next launch
```

### Backup Config
```bash
cp ~/.w4gns_logger/config.yaml ~/.w4gns_logger/config-backup.yaml
```

### Edit with Terminal
```bash
nano ~/.w4gns_logger/config.yaml        # Linux
nano ~/.w4gns_logger/config.yaml        # macOS
notepad %USERPROFILE%\.w4gns_logger\config.yaml  # Windows
```

---

## Settings That Save Automatically

| Setting | Saved When |
|---------|-----------|
| Operator callsign | You click "Save Settings" |
| Grid square | You click "Save Settings" |
| Default mode | You click "Save Settings" |
| TX power | You click "Save Settings" |
| Theme | You click "Save Settings" |
| Font size | You click "Save Settings" |
| Window size/position | App closing |
| Feature toggles | You click "Save Settings" |

---

## Settings That DON'T Save

- ❌ Contact data (saved in database)
- ❌ Award progress (saved in database)
- ❌ Temporary filters or searches
- ❌ Window scroll position

---

## Common YAML Rules

```yaml
# Key: Value pairs
key: value

# Strings with special characters need quotes
name: "W4GNS Logger"

# Numbers without quotes
count: 42
power: 100.5

# True/False
enabled: true
enabled: false

# Nested sections (use spaces, not tabs)
section:
  subsection: value
  another: 123
```

### YAML Errors to Avoid
```yaml
# ❌ Missing space after colon
key:value

# ❌ Tabs instead of spaces
section:
	nested: value

# ❌ Unclosed quotes
name: "unclosed

# ❌ Wrong indentation
key: value
nested: wrong

# ❌ Missing colon
name John
```

---

## Troubleshooting

### Settings won't save
- [ ] Is the app still running? (Close it first)
- [ ] Check file permissions: `ls -la ~/.w4gns_logger/`
- [ ] Restart the application

### Settings revert on restart
- [ ] File might not be saving to disk
- [ ] Check available disk space
- [ ] Verify YAML syntax if manually edited

### Can't find config file
- [ ] Show hidden files (Ctrl+H in file manager)
- [ ] Or search: `find ~ -name "config.yaml"`
- [ ] Ensure app has been launched once

### YAML syntax error
- [ ] Don't use tabs (use spaces only)
- [ ] Add space after colons: `key: value`
- [ ] Keep consistent indentation
- [ ] Enclose special characters in quotes

### Wrong settings applied
- [ ] Restart the application
- [ ] Close all instances of the app
- [ ] Check file permissions
- [ ] Try resetting: `rm ~/.w4gns_logger/config.yaml`

---

## Settings GUI Features

### General Tab
- ✅ Operator callsign
- ✅ Home grid square
- ✅ Default mode
- ✅ Default TX power
- ✅ Auto-save interval

### Database Tab
- ✅ Database location (with browse button)
- ✅ Backup enabled toggle
- ✅ Backup interval

### UI Tab
- ✅ Theme selection (light/dark)
- ✅ Font size slider
- ✅ Window geometry (auto-managed)

### Features Tab
- ✅ DX Cluster enable
- ✅ Cluster auto-connect
- ✅ QRZ.com integration
- ✅ Award tracking
- ✅ All toggles and intervals

### Raw Config Tab
- ✅ Full YAML editor
- ✅ Direct file editing
- ✅ Syntax checking

---

## File Locations Summary

| Item | Location |
|------|----------|
| Config File | `~/.w4gns_logger/config.yaml` |
| Database | `~/.w4gns_logger/contacts.db` (configurable) |
| App Directory | `~/Projects/W4GNS Logger/` |
| Backups | `~/.w4gns_logger/backups/` (auto-created) |
| Logs | Console output (no log file by default) |

---

## Settings for Different Scenarios

### Contest Mode
```yaml
general:
  auto_save_interval: 30        # Save more frequently
  default_mode: "CW"            # Set to your mode
```

### Mobile Operation
```yaml
general:
  default_power: 5              # Lower power
  default_mode: "SSB"
```

### Home Station
```yaml
general:
  default_power: 100            # Full power
  auto_save_interval: 60
```

### Testing/Development
```yaml
database:
  backup_enabled: false         # Disable backups
  location: "/tmp/test.db"      # Temp database
```

---

## Factory Reset

**Remove everything and start fresh:**

```bash
# Backup first (IMPORTANT!)
cp ~/.w4gns_logger/config.yaml ~/config-backup.yaml

# Reset configuration only
rm ~/.w4gns_logger/config.yaml
# App recreates with defaults on next launch

# Reset everything (config + database + backups)
rm -rf ~/.w4gns_logger/
# App recreates everything on next launch
```

---

## Advanced: Environment Variables

### Override Config at Runtime
```bash
# Linux/macOS
export W4GNS_DB_PATH=/custom/path/contacts.db
python launcher.py

# Windows
set W4GNS_DB_PATH=C:\custom\path\contacts.db
python launcher.py
```

### Custom Config Directory
```bash
# Linux/macOS
export W4GNS_CONFIG_DIR=/custom/config/path
python launcher.py

# Windows
set W4GNS_CONFIG_DIR=C:\custom\config\path
python launcher.py
```

---

## Need Help?

- **How to edit settings?** → GUI (Settings tab)
- **Where's config file?** → `~/.w4gns_logger/config.yaml`
- **How to backup?** → `cp ~/.w4gns_logger/config.yaml ~/backup.yaml`
- **How to reset?** → `rm ~/.w4gns_logger/config.yaml` (recreated on launch)
- **More details?** → Read `USER_SETTINGS_GUIDE.md`

---

**73 de W4GNS** 🎙️
