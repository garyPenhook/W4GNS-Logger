# W4GNS SKCC Logger v1.8

A comprehensive SKCC-focused ham radio contact logging application. Track QSOs, manage awards (Centurion, Tribune, Senator), and export to ADIF format.

---

## Running the Application

### Windows

1. **Download and extract** the W4GNS Logger folder
2. **Double-click** `run.bat` in the folder
3. The app will download Python, install dependencies, and start automatically

**Or from Command Prompt**:
```cmd
cd "W4GNS Logger"
run.bat
```

### macOS & Linux

1. **Download and extract** the W4GNS Logger folder
2. **Open Terminal** in the folder
3. **Run**:
```bash
./run.sh
```

The app will download Python 3.14, install dependencies, and start automatically.

### Alternative: Manual Python Setup

If you have Python 3.14+ installed:

```bash
cd "W4GNS Logger"
python src/main.py
```

---

## Using the Application

### Getting Started

1. **Settings Tab** - Configure your callsign and grid square first
2. **Logging Tab** - Enter QSOs (contacts)
3. **Contacts Tab** - View all logged contacts
4. **Awards Tab** - Track your progress toward awards

### Logging a Contact

1. Go to **Logging** tab
2. Enter callsign and contact details
3. The **Previous QSOs panel** (right side) shows all past contacts with this call
4. Click **Save Contact**

**Fields**:
- **Callsign** - Remote station call (required)
- **Date/Time** - When contact was made (automatic UTC)
- **Band** - Frequency band (required)
- **Mode** - CW, SSB, FM, etc. (required)
- **Frequency** - MHz (auto-fills from band)
- **RST Sent/Received** - Signal reports (default 599)
- **Country/State** - Station location
- **Grid/QTH** - Grid square and city
- **SKCC #** - SKCC member number (if applicable)
- **Power** - Transmit power in watts

### Editing a Contact

1. Go to **Contacts** tab
2. **Double-click** the contact you want to edit
3. Make corrections in the edit dialog
4. Click **Save Changes**

### Searching Contacts

1. Go to **Contacts** tab
2. Type callsign in **Search** field (auto-filters)
3. Select **Band** to filter by band
4. Select **View Mode**: "All Contacts" or "Last 10"

### Tracking Awards

1. Go to **Awards** tab
2. Select award type (Centurion, Tribune, Senator, etc.)
3. View your progress and required items
4. Log more contacts to advance

### Monitoring RBN Spots with Award Highlighting

1. Go to **SKCC/DX Spots** tab
2. Click **Start Monitoring** to connect to RBN (Reverse Beacon Network)
3. Spots appear in real-time as stations are heard on CW
4. **Color-coded highlighting** shows award relevance:
   - 🔴 **Red** - CRITICAL (≤5 needed for award) - Work immediately!
   - 🟠 **Orange** - HIGH (≤20 needed for award) - Important opportunity
   - 🟡 **Yellow** - MEDIUM (21+ needed for award) - Medium priority
   - 🟢 **Green** - LOW (already worked/not relevant) - Skip or low priority
5. **Hover over colored spots** to see exact award details ("Need 2 more for Centurion")
6. **Click a spot** to populate the logging form for quick QSO entry

**Features**:
- Automatically analyzes each spot against YOUR personal award progress
- Considers all active awards: Centurion, Tribune, Senator, Triple Key
- Updates highlighting as you log new contacts
- Displays signal strength, reporter location, and frequency
- Filters by band, mode (CW), and signal strength
- Prevents duplicate spots with 3-minute cooldown

### Exporting Contacts

1. Go to **File** → **Export ADIF**
2. Select location to save
3. File saved as ADIF format for other logging software

### Importing Contacts

1. Go to **File** → **Import ADIF**
2. Select ADIF file from another logger
3. Contacts are added to database

---

## Features

✓ **Contact Logging** - Complete QSO details with previous QSOs panel
✓ **Award Tracking** - Centurion, Tribune, Senator, QRP, and others
✓ **Contact Editing** - Double-click to correct mistakes
✓ **Previous QSOs Display** - Shows callsign history with date, time, band, mode, SKCC#, state, city
✓ **RBN Spot Monitoring** - Real-time CW spots from Reverse Beacon Network
✓ **Smart Spot Highlighting** - Award-based color coding (Red/Orange/Yellow/Green)
✓ **Intelligent Filtering** - Spots highlighted based on YOUR personal award progress
✓ **ADIF Import/Export** - Share with other logging software
✓ **Power Tracking** - Monitor QRP and power usage
✓ **Space Weather** - Solar flux, K-index, A-index monitoring
✓ **QRZ Integration** - Auto-fill callsign data
✓ **SKCC Database** - Auto-lookup SKCC member numbers
✓ **Cross-Platform** - Windows, macOS, Linux

---

## Help & Documentation

For complete documentation and step-by-step guides:

- **HELP.md** - Full user guide with interactive navigation
- **QUICK_START.md** - 5-minute quick start guide
- **SETTINGS_REFERENCE.md** - Configuration options
- **USER_SETTINGS_GUIDE.md** - Detailed settings explanation

**Access Help in App**:
- Press **F1** (or Help → Help Contents)
- Opens interactive HELP.md with clickable navigation

---

## System Requirements

- **Windows 10+** (64-bit recommended)
- **macOS 10.13+** (Intel or Apple Silicon)
- **Linux** - Ubuntu 18.04+, Debian, Fedora, etc.
- **RAM** - 2GB minimum (4GB recommended)
- **Storage** - ~200-250MB (includes Python 3.14 + dependencies; app code only is ~3MB)
- **Display** - 1024x768 minimum (1920x1080 recommended)

---

## First Time Setup

1. **Run the app** (see above)
2. Go to **Settings** tab
3. Enter your **Operator Callsign**
4. Enter your **Home Grid Square**
5. (Optional) Configure **QRZ Integration** for auto-fill
6. Click **Save Settings**
7. Start logging contacts!

---

## Data Backup

The application automatically:
- Backs up your database on shutdown
- Creates ADIF backups in the Logs folder
- Stores backups in multiple locations

**Manual Backup**:
1. Go to **Contacts** tab
2. Click **Export ADIF**
3. Save to external drive or cloud storage

---

## Support

If you encounter issues:

1. **Check HELP.md** - Press F1 in the app
   - Interactive navigation with all features explained
   - Troubleshooting section with solutions
   - Keyboard shortcuts reference

2. **Review Settings**
   - Settings tab → Check your configuration
   - Ensure callsign and grid square are set

3. **Verify Database**
   - Settings tab → Check database location
   - Ensure write permissions to database folder

---

## License

Ham Radio application for Straight Key Century Club (SKCC) operators.

---

**Version**: 1.8
**Last Updated**: October 2025
**Python**: 3.14+

**73 de W4GNS** 🎙️
