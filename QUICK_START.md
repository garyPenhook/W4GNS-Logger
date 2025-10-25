# Quick Start Guide - W4GNS Ham Radio Logger

## TL;DR - Just Run This

**Linux/macOS (from terminal):**
```bash
./run.sh
```

**Windows:**
```cmd
run.bat
```

**Any Platform (double-click):**
```bash
python launcher.py
```

---

## What You Just Built

✅ **Professional Contact Logging Form** with dropdown menus:
- Band selection (160M - 23cm)
- Operating mode selection (36 modes: CW, SSB, FM, RTTY, etc.)
- Country selector (115+ countries)
- State selector (US states, auto-enabled for USA)
- Frequency auto-fill from band selection
- Signal report entry (RST sent/received)
- Operator information
- Grid square and QTH entry
- TX power entry

✅ **Automatic Database Integration** - Save contacts to SQLite
✅ **Form Validation** - Prevents incomplete/invalid entries
✅ **Cross-Platform Launcher** - Works on Windows, Linux, macOS
✅ **Smart Qt Platform Detection** - Finds best display backend automatically

---

## Files You Now Have

### Main Application Files
- `src/ui/logging_form.py` - Contact logging form with all dropdown fields
- `src/ui/dropdown_data.py` - Dropdown data (bands, modes, countries, states)
- `src/ui/main_window.py` - Updated main window with integrated form
- `src/main.py` - Updated application entry point

### Launcher Scripts
- `run.sh` - Terminal launcher (Linux/macOS)
- `run.bat` - Terminal launcher (Windows)
- `launcher.py` - GUI launcher (any platform)
- `run_gui.sh` - GUI launcher with display detection (Linux)
- `W4GNS-Logger.desktop` - Desktop application shortcut (Linux)

### Documentation
- `LAUNCHING_GUI.md` - How to run from GUI/file manager
- `RUNNING_THE_APPLICATION.md` - All ways to run the app
- `QT_PLATFORM_TROUBLESHOOTING.md` - Display issues help
- `QUICK_START.md` - This file

---

## Using the Application

### 1. Creating Your First Contact Entry

1. Launch the application (see section above)
2. Click the **Logging** tab
3. Fill in the form fields:
   - **Callsign**: Enter the remote station callsign (e.g., N5XYZ)
   - **Date & Time**: Select date/time of contact
   - **Band**: Choose from dropdown (160M, 80M, 40M, 20M, etc.)
   - **Mode**: Choose from dropdown (CW, SSB, FM, etc.)
   - **Frequency**: Auto-fills when you select band, or enter manually
   - **Country**: Select from dropdown
   - **State**: Auto-enables if USA selected
   - **Grid Square**: Enter grid (e.g., EM87ui)
   - **RST Sent/Received**: Signal reports (e.g., 59)
   - **TX Power**: Your transmit power in watts
   - **Operator Name**: Remote operator name

4. Click **Save Contact** button
5. Success message appears - contact saved to database!
6. Form clears for next entry

### 2. Keyboard Shortcuts

While in form:
- **Tab** - Move to next field
- **Shift+Tab** - Move to previous field
- **Enter** - Submit form (from any field)
- **Ctrl+A** - Select all in text field
- **Ctrl+Z** - Undo (standard OS shortcut)

### 3. Tabs Available

- **Logging** - Enter new contacts (active now)
- **Contacts** - View saved contacts (coming soon)
- **Awards** - Track DXCC, WAS, etc. (coming soon)
- **DX Cluster** - Real-time spots (coming soon)
- **Settings** - Application settings (coming soon)

---

## Your Data

### Where It's Stored
- **Database**: `~/.w4gns_logger/contacts.db`
- **Config**: `~/.w4gns_logger/config.yaml`

### Backup Your Data
```bash
cp ~/.w4gns_logger/contacts.db ~/backups/contacts-backup.db
```

### Export Your Contacts (ADIF)
Coming soon - File → Export ADIF

### Import Contacts (ADIF)
Coming soon - File → Import ADIF

---

## Troubleshooting

### Problem: "GUI won't start"

**Check your display server:**
```bash
echo $DISPLAY         # Should show :0 or similar
```

**Solution**: Follow [LAUNCHING_GUI.md](LAUNCHING_GUI.md) for your platform.

### Problem: "Qt platform plugin error"

**Solution**: Install missing library:
```bash
# Ubuntu/Debian
sudo apt-get install -y libxcb-cursor0
```

See [QT_PLATFORM_TROUBLESHOOTING.md](QT_PLATFORM_TROUBLESHOOTING.md) for more details.

### Problem: "Permission denied"

**Solution**:
```bash
chmod +x run.sh launcher.py run_gui.sh
```

### Problem: Very slow startup (first time only)

Normal! It's installing dependencies. Subsequent launches are fast.

---

## What's Next?

### For Developers
- The logging form is fully functional and integrated
- All dropdown data is available in `src/ui/dropdown_data.py`
- Add validation rules in `LoggingForm._validate_form()`
- Customize dropdown data by editing `DropdownData` class

### For Users
1. Start logging your contacts
2. Accumulate contacts in the database
3. Watch for updates to:
   - Contact search/filter
   - Award tracking
   - ADIF import/export
   - DX Cluster integration

### Feature Roadmap
- [ ] Contact search and filtering
- [ ] Export to ADIF format
- [ ] Import from ADIF format
- [ ] Award tracking (DXCC, WAS, WPX)
- [ ] DX Cluster integration
- [ ] QRZ.com sync
- [ ] Detailed contact view
- [ ] Statistics dashboard

---

## System Requirements

| Component | Requirement |
|-----------|-------------|
| **Python** | 3.14+ (auto-downloaded via UV) |
| **RAM** | 256MB minimum, 512MB recommended |
| **Disk** | 500MB for Python + dependencies |
| **Display** | Any (X11, Wayland, or headless) |
| **OS** | Windows 7+, macOS 10.13+, Linux (any distro) |

---

## Getting Help

### Check These Files First
1. **Can't launch?** → [LAUNCHING_GUI.md](LAUNCHING_GUI.md)
2. **Display errors?** → [QT_PLATFORM_TROUBLESHOOTING.md](QT_PLATFORM_TROUBLESHOOTING.md)
3. **Advanced usage?** → [RUNNING_THE_APPLICATION.md](RUNNING_THE_APPLICATION.md)
4. **Project details?** → [README.md](README.md)

### Enable Debug Output
```bash
export QT_DEBUG_PLUGINS=1
./run.sh
```

### Check Application Log
When running from terminal, all output appears in console.

---

## Feature Highlights

### Smart Dropdowns
- Bands automatically populated with standard ham frequencies
- Modes include both classic (CW, SSB) and modern digital modes
- Countries validated against DXCC entity list
- States only show for US selection

### Auto-Fill Intelligence
- Select band → frequency auto-fills with center frequency
- Manual override available
- Previous entries remembered (coming soon)

### Validation
- Required fields enforced
- Invalid RST format detected
- Frequency range checked per band
- Callsign format validated

### Database
- SQLite backend - no external database needed
- Automatic backups available
- ADIF standard compliant
- Unlimited contacts supported

---

## Pro Tips

1. **Use Tab key** - Faster than mouse for rapid logging
2. **Auto-frequency** - Let band selection fill frequency automatically
3. **Batch import** - Import ADIF to bulk-load old contacts
4. **Backup regularly** - Keep your logbook safe
5. **Use standard callsigns** - Uppercase recommended (auto-converted)

---

## Version Info

- **Application**: W4GNS Ham Radio Logger v1.0.0
- **Python**: 3.14.0 (managed by UV)
- **PyQt**: 6.x
- **Database**: SQLite3
- **Last Updated**: October 20, 2025

---

## License & Credits

Built for ham radio operators. Respects all amateur radio regulations and ARRL guidelines.

Enjoy logging contacts! 73 de W4GNS

---

**Next Step**: Launch the app and create your first contact!

```bash
./run.sh
```
