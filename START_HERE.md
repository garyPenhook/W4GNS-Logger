# W4GNS Ham Radio Logger - START HERE

Welcome! This guide will help you get up and running quickly.

## First Time? Read This First

1. **Start the application** - 2 minutes
2. **Log your first contact** - 5 minutes
3. **Explore other tabs** - Optional

---

## Quick Start (2 Minutes)

### Step 1: Open a Terminal

### Step 2: Navigate to the project
```bash
cd "W4GNS Logger"
```

### Step 3: Run the application

**Linux/macOS:**
```bash
./run.sh
```

**Windows:**
```cmd
run.bat
```

**Any Platform (if above doesn't work):**
```bash
python launcher.py
```

### Step 4: Wait for launch
- First run takes 30 seconds (installing dependencies)
- Subsequent runs are instant
- A GUI window should appear

---

## If GUI Doesn't Appear

**Most Common Reason**: Missing display server on Linux

**Quick Fix**:
1. Make sure you have a graphical desktop environment running
2. If on SSH: use `ssh -X` to enable X11 forwarding
3. See [LAUNCHING_GUI.md](LAUNCHING_GUI.md) for detailed help

---

## Logging Your First Contact (5 Minutes)

1. **Click the "Logging" tab** (should be active by default)

2. **Fill in the form**:
   - **Callsign**: Type the remote station callsign (e.g., `N5XYZ`)
   - **Date & Time**: Click to select (defaults to now)
   - **Band**: Click dropdown and select band (e.g., `20M`)
   - **Mode**: Click dropdown and select mode (e.g., `SSB`)
   - **Frequency**: Auto-fills when you select band (or type manually)

3. **Optional - Add more details**:
   - **Country**: Select from dropdown
   - **State**: Auto-enabled if USA selected
   - **Grid Square**: Enter grid (e.g., `EM87ui`)
   - **RST Sent/Received**: Signal reports
   - **TX Power**: Your transmit power
   - **Operator Name**: Remote operator's name

4. **Click "Save Contact"**
   - Success message appears
   - Form clears for next entry
   - Contact saved to database!

---

## Key Features

### Smart Dropdowns
- Band selection (15 HF/VHF bands)
- Mode selection (36 modes: CW, SSB, FM, RTTY, digital)
- Country selection (115+ countries)
- State selection (auto-enables for USA)

### Auto-Fill
- Select band → frequency auto-fills with center frequency
- Can override manually if needed

### Validation
- Won't save incomplete contacts
- Checks RST format
- Validates required fields

### Database
- All contacts stored locally in SQLite
- No internet required
- Backup to file anytime

---

## Available Tabs

| Tab | Status | Purpose |
|-----|--------|---------|
| **Logging** | ✅ Ready | Log new contacts |
| **Contacts** | 🔄 Coming | Search saved contacts |
| **Awards** | 🔄 Coming | Track DXCC, WAS, etc |
| **DX Cluster** | 🔄 Coming | Real-time spot monitoring |
| **Settings** | 🔄 Coming | App configuration |

---

## Menu Options

| Menu | Available | Function |
|------|-----------|----------|
| **File** | 🔄 Coming | Import/Export ADIF |
| **Edit** | 🔄 Coming | Settings |
| **View** | 🔄 Coming | Dark mode toggle |
| **Tools** | 🔄 Coming | Award verification |
| **Help** | ✅ Ready | About dialog |

---

## Where Is My Data?

Your contacts are stored here:
- **Linux/macOS**: `~/.w4gns_logger/contacts.db`
- **Windows**: `%USERPROFILE%\.w4gns_logger\contacts.db`

### Backup Your Data
```bash
cp ~/.w4gns_logger/contacts.db ~/backups/contacts-backup.db
```

---

## Documentation Index

### For Different Needs

**Just want to launch?**
→ [QUICK_START.md](QUICK_START.md) - 5 minute overview

**Having trouble launching?**
→ [LAUNCHING_GUI.md](LAUNCHING_GUI.md) - All ways to run the app

**Getting Qt errors?**
→ [QT_PLATFORM_TROUBLESHOOTING.md](QT_PLATFORM_TROUBLESHOOTING.md) - Display server issues

**Need advanced options?**
→ [RUNNING_THE_APPLICATION.md](RUNNING_THE_APPLICATION.md) - All 7 launch methods

**Want full feature details?**
→ [README.md](README.md) - Complete project documentation

---

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Tab` | Move to next field |
| `Shift+Tab` | Move to previous field |
| `Enter` | Submit form (from any field) |
| `Ctrl+A` | Select all in text field |
| `Ctrl+Q` | Close application |

---

## Troubleshooting Quick Reference

### Problem: "File not found" or "Permission denied"
**Solution**:
```bash
cd "W4GNS Logger"
chmod +x run.sh launcher.py run_gui.sh
./run.sh
```

### Problem: GUI starts but window doesn't appear
**Solution**: See [LAUNCHING_GUI.md](LAUNCHING_GUI.md) section "Linux - No GUI Appears"

### Problem: "Qt platform plugin" error
**Solution**: See [QT_PLATFORM_TROUBLESHOOTING.md](QT_PLATFORM_TROUBLESHOOTING.md) "Root Cause" section

### Problem: Form won't save
**Solution**:
1. Check that all required fields have values (Callsign, Band, Mode)
2. Check frequency is greater than 0
3. Try clearing and re-entering
4. See console output for specific error

### Problem: Slow first startup
**Solution**: Normal! Dependencies installing. Subsequent launches are instant.

---

## Pro Tips

1. **Use Tab key** - Faster than mouse for rapid logging
   - Callsign → Band → Mode → Frequency → Save

2. **Callsigns** - Automatically converted to uppercase
   - Type `n5xyz` → Saves as `N5XYZ`

3. **Auto-frequency** - Let band selection fill frequency
   - Select 20M → Frequency becomes 14.0 MHz
   - Override manually if using different frequency

4. **Batch operations** - Coming soon
   - Import ADIF to load old contacts
   - Export to create backups

5. **Regular backups** - Don't lose your logbook!
   ```bash
   cp ~/.w4gns_logger/contacts.db ~/backups/contacts-$(date +%Y%m%d).db
   ```

---

## Getting Help

### Is your question answered in...

**Quick Start?**
→ [QUICK_START.md](QUICK_START.md)

**Launching?**
→ [LAUNCHING_GUI.md](LAUNCHING_GUI.md)

**Display/Platform errors?**
→ [QT_PLATFORM_TROUBLESHOOTING.md](QT_PLATFORM_TROUBLESHOOTING.md)

**Advanced usage?**
→ [RUNNING_THE_APPLICATION.md](RUNNING_THE_APPLICATION.md)

**Project details?**
→ [README.md](README.md)

**Still stuck?**
→ Enable debug mode:
```bash
export QT_DEBUG_PLUGINS=1
./run.sh 2>&1 | tee debug.log
```

---

## What's Next?

### For Users
1. ✅ Launch the application
2. ✅ Log your first few contacts
3. 🔜 Watch for Contacts tab (search/filter)
4. 🔜 Start tracking awards (DXCC, WAS)
5. 🔜 Export your logbook to ADIF

### For Developers
1. Review [src/ui/logging_form.py](src/ui/logging_form.py) - Form implementation
2. Check [src/ui/dropdown_data.py](src/ui/dropdown_data.py) - Data provider
3. Read [README.md](README.md) - Full architecture
4. Add new features to other tabs

---

## System Information

| Component | Details |
|-----------|---------|
| **App Name** | W4GNS Ham Radio Logger |
| **Version** | 1.0.0 |
| **Python** | 3.14+ (auto-managed by UV) |
| **UI Framework** | PyQt6 |
| **Database** | SQLite3 |
| **Platforms** | Windows, macOS, Linux |
| **License** | Respects ham radio regulations |

---

## Quick Reference Card

### Launch Command
```bash
./run.sh              # Linux/macOS
run.bat               # Windows
python launcher.py    # Any platform
```

### Log a Contact
```
1. Click Logging tab
2. Fill form
3. Click Save Contact
```

### Where's My Data?
```
~/.w4gns_logger/contacts.db
```

### Backup
```bash
cp ~/.w4gns_logger/contacts.db ~/backups/contacts-backup.db
```

### Help with Launching
```
See: LAUNCHING_GUI.md
```

### Help with Errors
```
See: QT_PLATFORM_TROUBLESHOOTING.md
```

---

## Next Step

Choose one:

1. **New to the app?**
   → Go to [QUICK_START.md](QUICK_START.md)

2. **Can't launch?**
   → Go to [LAUNCHING_GUI.md](LAUNCHING_GUI.md)

3. **Ready to start?**
   ```bash
   ./run.sh
   ```

---

**Enjoy logging! 73 de W4GNS** 🎙️

---

*Need help?* Check the documentation files above. For issues not covered, review the README.md file.
