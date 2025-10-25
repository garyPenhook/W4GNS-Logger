# W4GNS Ham Radio Logger - Help

## Getting Started

### Logging a Contact

1. Click the **Logging** tab
2. Fill in the contact details:
   - **Callsign**: Remote station callsign (required)
   - **Date & Time**: When you made the contact
   - **Band**: Select from dropdown (required)
   - **Mode**: Select from dropdown (required)
   - **Frequency**: MHz (auto-fills from band)
   - **Country**: Optional
   - **State**: Optional (auto-enables for USA)
   - **Grid Square**: Optional
   - **RST Sent/Received**: Signal reports
   - **TX Power**: Your transmit power
   - **Operator Name**: Remote operator name
3. Click **Save Contact**

### Settings

1. Click the **Settings** tab
2. Configure:
   - **General**: Your callsign, grid, default mode/power
   - **Database**: Storage location, backups
   - **UI**: Theme, font size
   - **Features**: Enable/disable features
   - **Raw Config**: Advanced YAML editing
3. Click **Save Settings**

Settings are automatically saved and persist across sessions.

### Viewing Contacts

The **Contacts** tab (coming soon) will display all saved contacts.

### Awards

The **Awards** tab (coming soon) will track DXCC, WAS, and other awards.

### DX Cluster

The **DX Cluster** tab (coming soon) will show real-time DX spots.

## Tips

- **Auto-frequency**: Select a band to auto-fill the frequency
- **Callsign format**: Callsigns are automatically converted to uppercase
- **Tab navigation**: Use Tab key to move between fields
- **Save frequently**: Use auto-save or click Save regularly
- **Backup**: Settings are stored in `~/.w4gns_logger/config.yaml`

## Common Tasks

### Change Your Callsign

1. Settings tab → General → Operator Callsign
2. Enter your call
3. Click Save Settings

### Change Theme

1. Settings tab → UI → Theme
2. Select "light" or "dark"
3. Click Save Settings

### Reset Settings

1. Settings tab
2. Click "Reset to Defaults"
3. Confirm

### View Configuration File

Linux/macOS:
```
~/.w4gns_logger/config.yaml
```

Windows:
```
%USERPROFILE%\.w4gns_logger\config.yaml
```

## Troubleshooting

### GUI Window Doesn't Appear

- Check that you have a display server running (X11, Wayland, or Windows/macOS)
- Try closing and relaunching the app
- See QT_PLATFORM_TROUBLESHOOTING.md for detailed help

### Settings Won't Save

- Ensure the app has permission to write to `~/.w4gns_logger/`
- Check available disk space
- Try restarting the application

### Can't Find Configuration File

- Linux/macOS: Enable hidden files (Ctrl+H in file manager)
- Or navigate to: `~/.w4gns_logger/`
- Windows: Check `%USERPROFILE%\.w4gns_logger\`

### Form Validation Error

- All required fields must be filled
- Callsign, Band, Mode, Frequency are required
- RST must be 1-3 digits if provided
- Frequency must be greater than 0

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| Tab | Move to next field |
| Shift+Tab | Move to previous field |
| Enter | Submit form (from any field) |
| Ctrl+Q | Close application |

## What's Next

The application is in early development. Coming soon:

- Contact search and filtering
- ADIF import/export
- Award tracking (DXCC, WAS, WPX)
- DX Cluster integration
- QRZ.com synchronization
- Statistics dashboard

## Support

For more detailed information:

- **Settings**: See USER_SETTINGS_GUIDE.md
- **Launching**: See LAUNCHING_GUI.md
- **Display Issues**: See QT_PLATFORM_TROUBLESHOOTING.md
- **Full Documentation**: See README.md

## About

**W4GNS Ham Radio Logger v1.0.0**

A comprehensive ham radio contact logging application with support for ADIF, award tracking, and DX cluster integration.

Database: SQLite
Framework: PyQt6
Python: 3.14+

---

**73 de W4GNS** 🎙️
