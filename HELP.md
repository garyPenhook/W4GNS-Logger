# W4GNS SKCC Logger - Complete User Guide

## 📑 Quick Navigation Table of Contents

### Main Topics
1. **[Getting Started](#getting-started)** - First time setup
2. **[Logging Tab](#logging-tab)** - Log new QSOs with Previous QSOs panel
3. **[Contacts Tab](#contacts-tab)** - View, search, and edit contacts
4. **[Awards Tab](#awards-tab)** - Track SKCC and other awards
5. **[Power Stats Tab](#power-stats-tab)** - Monitor power usage
6. **[Space Weather Tab](#space-weather-tab)** - Check propagation conditions
7. **[QRP Progress Tab](#qrp-progress-tab)** - Track low-power contacts
8. **[Settings Tab](#settings-tab)** - Configure preferences
9. **[Menu Bar & Toolbar](#menu-bar--toolbar)** - Keyboard shortcuts
10. **[Tips & Tricks](#tips--tricks)** - Workflow efficiency
11. **[Troubleshooting](#troubleshooting)** - Problem solving

### Quick Lookup (Common Tasks)
- **[First Time Setup](#first-time-setup)** - Get started in 3 steps
- **[How to Log a Contact](#step-by-step-logging-a-contact)** - Detailed logging guide
- **[Edit a Contact](#editing-a-contact)** - Double-click to edit
- **[Find & Search Contacts](#searching--filtering)** - Use search and filters
- **[Track an Award](#how-to-use-awards)** - Monitor award progress
- **[Export Contacts](#exporting-contacts)** - Save to ADIF format
- **[QRZ Integration](#qrz-integration)** - Auto-fill callsign data
- **[Keyboard Shortcuts](#keyboard-shortcuts-summary)** - Speed up workflow
- **[Solve Common Problems](#troubleshooting)** - Troubleshooting guide

---

## Getting Started

### First Time Setup

1. **Start the Application**
   - The W4GNS SKCC Logger window opens with the Logging tab active

2. **Configure Your Settings** (Important!)
   - Click the **Settings** tab
   - Enter your operator callsign and home grid square
   - Configure QRZ integration if desired
   - Click "Save Settings"

3. **Start Logging Contacts**
   - Return to the **Logging** tab
   - Begin entering QSO information

---

## Logging Tab

The Logging tab is where you enter new QSO (contact) information. It consists of:
- **Left side**: QSO entry form
- **Right side**: Previous QSOs with the entered callsign

### Step-by-Step: Logging a Contact

#### 1. Enter the Callsign

1. Click in the **Callsign** field
2. Type the remote station's call sign (e.g., W1ABC)
3. The application will automatically:
   - Convert to uppercase
   - Display all previous QSOs with this callsign on the right panel
   - Auto-fetch QRZ information if enabled (after tabbing away)

#### 2. Verify Date & Time

- **Date/Time**: Shows current UTC time (all times in UTC)
- If you need to correct it, click the field and edit
- Format: MM-DD HH:MM (UTC)

#### 3. Enter Signal Reports

- **RST Sent**: Report you sent (default: 599)
  - Range: 111-599
  - First digit: Readability (1-5)
  - Second digit: Strength (1-9)
  - Third digit: Tone (1-9)

- **RST Received**: Report you received (default: 599)

#### 4. Select Band & Mode

1. **Band Dropdown**
   - Select the frequency band (80m, 40m, 20m, etc.)
   - Frequency automatically updates to band center

2. **Mode Dropdown**
   - Select transmission mode (CW, SSB, FM, etc.)
   - Default is CW

3. **Frequency (MHz)**
   - Auto-fills from band selection
   - Can manually adjust for specific frequency

#### 5. Enter Location Information

- **Country**: Select from dropdown (required for contest verification)
  - When USA is selected, State field becomes enabled

- **State**: Auto-enabled when "United States" selected
  - Select the remote station's state

- **Grid Square**: Maidenhead grid locator (e.g., EM87ui)
  - Auto-filled if QRZ data available

- **QTH/City**: City or location name
  - Auto-filled if QRZ data available

#### 6. SKCC-Specific Information

- **SKCC Number**: Member number if SKCC member
  - Auto-filled from SKCC membership database
  - Shows previous SKCC contacts on right panel

- **Operator Name**: Remote operator's name
  - Auto-filled if QRZ data available
  - Useful for tracking who you've worked

- **Key Type**: Type of mechanical key used
  - STRAIGHT, BUG, SIDESWIPER, or NONE
  - Affects SKCC awards tracking

- **Paddle**: Type of paddle if applicable
  - ELECTRONIC, SEMI-AUTO, IAMBIC, MECHANICAL
  - Optional field

#### 7. County Information

- **County**: County of remote station (if applicable)
  - Auto-filled from QRZ if available
  - Useful for ARCI awards

#### 8. TX Power

- **QRP Checkbox**: Check if contact was QRP (≤5W)
- **Power (Watts)**: Transmit power used in watts
  - Leave as 0 if not tracking power

#### 9. Review Previous QSOs

On the **right side**, you'll see:
- All previous contacts with this callsign
- **Columns shown**:
  - Date (YYYY-MM-DD) - **bold** for visibility
  - Time (UTC)
  - Band
  - Mode
  - Frequency
  - RST (Sent/Received)
  - SKCC # (if applicable)
  - State
  - City/QTH

*This helps you avoid duplicate contacts and remember previous exchanges.*

#### 10. Save the Contact

1. Review all information
2. Click **Save Contact** (green button)
3. Success message appears
4. Form clears automatically
5. Ready for next contact

**[:arrow_up: Back to Top](#-quick-navigation-table-of-contents)**

---

## Contacts Tab

The Contacts tab displays all your logged contacts in a searchable, sortable table.

### Viewing Contacts

1. Click the **Contacts** tab
2. See all contacts with columns:
   - Callsign
   - Date (UTC)
   - Time (UTC)
   - Band
   - Mode
   - SKCC Number
   - Power

### Searching & Filtering

#### Search by Callsign

1. Type in **Callsign** search field
2. Table automatically filters to matching calls
3. Partial matches work (e.g., "W1" finds all W1xxx calls)

#### Filter by Band

1. Click **Band** dropdown
2. Select a band (80m, 40m, etc.)
3. Table shows only that band
4. Select "All Bands" to see everything

#### View Modes

- **All Contacts**: Display entire contact log
- **Last 10 Contacts**: Show only 10 most recent QSOs

### Editing a Contact

To correct mistakes in an existing contact:

1. **Double-click** the contact row you want to edit
2. **Edit Dialog** opens with all fields:
   - Callsign, Date, Time On/Off
   - Band, Mode, Frequency
   - RST Sent/Received
   - Country, State, Grid, QTH
   - Operator Name, SKCC Number, County, TX Power

3. Make corrections to any field
4. Click **Save Changes**
5. Contact updates immediately in the table

### Exporting Contacts

- **File → Export ADIF**: Save contacts in ADIF format
  - Use for submitting to award programs
  - Import into other logging software
  - Share with other operators

### Importing Contacts

- **File → Import ADIF**: Load contacts from another logger
  - Adds to existing database
  - Does not duplicate existing contacts

**[:arrow_up: Back to Top](#-quick-navigation-table-of-contents)**

---

## Awards Tab

The Awards tab tracks your progress toward various ham radio awards.

### Available Awards

#### Straight Key Century Club (SKCC) Awards

1. **Centurion**: 100 CW contacts with SKCC members
   - Shows progress toward 100
   - Lists contacts that count

2. **Tribune**: 1,000 CW contacts with SKCC members
   - Requires 1,000 different SKCC members
   - Shows percentage complete

3. **Senator**: 10,000 CW contacts with SKCC members
   - Ultimate SKCC award
   - Tracks progress

#### Other Awards

- **Canadian Maple**: Contact all Canadian provinces
- **DX Award**: Work countries worldwide
- **RAG Chew**: Extended QSO contacts
- **PFX Award**: Work various prefixes
- **Triple Key Award**: Use different key types
- **WAS**: All US states (American award)
- **WAC**: All continents (Worked All Continents)

### How to Use Awards

1. Click **Awards** tab
2. Select award sub-tab
3. View:
   - **Progress bar**: Visual completion percentage
   - **Statistics**: Current count, target, percentage
   - **Required items**: States/countries/members needed
   - **Contacts list**: QSOs that count toward award

4. To work towards an award:
   - Log contacts meeting the award requirements
   - Application automatically tracks progress
   - Check awards tab to see real-time updates

**[:arrow_up: Back to Top](#-quick-navigation-table-of-contents)**

---

## Power Stats Tab

Track your transmit power usage across all contacts.

### Features

- **Power Distribution**: Shows how power is distributed
  - QRP (≤5W)
  - Low (5-50W)
  - Medium (50-100W)
  - High (>100W)

- **Statistics**:
  - Total contacts by power level
  - Percentage breakdown
  - Visual charts

### Using Power Stats

1. Click **Power Stats** tab
2. View power usage patterns
3. Hover over chart sections for details
4. Use to understand typical power levels used

### Logging Power

- In Logging tab, enter **TX Power (Watts)**
- Application tracks all power levels
- Stats update automatically

**[:arrow_up: Back to Top](#-quick-navigation-table-of-contents)**

---

## Space Weather Tab

Monitor solar conditions affecting radio propagation.

### Space Weather Data

- **Solar Flux Index (SFI)**: Sun's radio emissions
  - Higher = better propagation on higher bands
  - Lower = better for lower frequency bands

- **Planetary K-Index**: Earth's magnetic field disruption
  - Low (0-3) = good propagation
  - High (6-9) = poor propagation, auroras possible

- **A-Index**: 24-hour magnetic stability
  - Low = stable propagation
  - High = unstable conditions

### Using Space Weather

1. Click **Space Weather** tab
2. Check current conditions before operations
3. Use to plan which bands to operate
4. Correlation with QSO frequency helps optimize operations

**[:arrow_up: Back to Top](#-quick-navigation-table-of-contents)**

---

## QRP Progress Tab

Track your QRP (low power) activity and awards.

### QRP Awards & Tracking

- **QRP Contacts**: Total contacts at ≤5W
- **QRP Countries**: Different countries worked on QRP
- **QRP States**: Different states worked on QRP

### Logging QRP Contacts

1. In Logging tab, check **QRP** checkbox
2. Set **Power** to value ≤5W
3. Save contact
4. Application automatically counts toward QRP awards

**[:arrow_up: Back to Top](#-quick-navigation-table-of-contents)**

---

## Settings Tab

Configure application preferences and behavior.

### General Settings

1. **Operator Callsign**: Your ham radio call sign
   - Used for logging database identification
   - Stored with each contact

2. **Home Grid Square**: Your Maidenhead locator
   - e.g., EM87ui
   - Used for distance calculations

3. **Home State**: Your state (if in USA)
   - Used for award verification

### Database Settings

1. **Database Location**: Where contacts are stored
   - Default: Application directory
   - Shows file path

2. **Auto Backup**: Automatic backup settings
   - Backup frequency
   - Backup location

3. **Export Directory**: Where ADIF exports go
   - Default: Logs folder

### UI Settings

1. **Theme**:
   - Light mode: Bright interface
   - Dark mode: Easy on eyes

2. **Font Size**: Adjust for readability

### QRZ Integration

1. **Enable QRZ**: Toggle QRZ lookups
2. **API Key**: Your QRZ.com API key
3. **Auto Fetch**: Automatically lookup callsigns when entered
4. **Auto Upload**: Send contacts to QRZ.com automatically

### Other Features

- **SKCC Database**: Enable/disable SKCC number lookups
- **Notifications**: Toast notifications for events
- **Raw Config**: Direct YAML editing for advanced users

### Saving Settings

- **Save Settings**: Apply all changes
- **Reset to Defaults**: Return to factory settings
- Settings auto-load on application restart

**[:arrow_up: Back to Top](#-quick-navigation-table-of-contents)**

---

## Menu Bar & Toolbar

### File Menu

- **New Contact** (Ctrl+N): Jump to Logging tab
- **Import ADIF** (Ctrl+I): Import contacts from file
- **Export ADIF** (Ctrl+E): Save contacts to ADIF
- **Exit** (Ctrl+Q): Close application

### Edit Menu

- **Settings** (Ctrl+,): Open Settings tab

### View Menu

- **Toggle Dark Mode**: Switch theme

### Tools Menu

- **Verify Awards**: Manually refresh award calculations

### Help Menu

- **Help Contents** (F1): This help file
- **About**: Application version and info

### Toolbar

Quick-access buttons for common operations:
- **New Contact**: Open Logging tab
- **Import**: Import ADIF file
- **Export**: Export contacts to ADIF

**[:arrow_up: Back to Top](#-quick-navigation-table-of-contents)**

---

## Tips & Tricks

### Logging Efficiency

1. **Use Tab Key**
   - Navigate between fields with Tab
   - Shift+Tab to go backwards
   - Faster than mouse clicking

2. **Auto-Fill Features**
   - Band dropdown auto-fills frequency
   - QRZ auto-fills location info
   - SKCC database auto-fills member numbers

3. **Previous QSOs Panel**
   - Check right panel before saving
   - Avoid duplicate contacts
   - Review previous exchanges quickly

4. **Keyboard Shortcuts**
   - Alt+L: Switch to Logging tab
   - Alt+C: Switch to Contacts tab
   - Alt+A: Switch to Awards tab

### Award Tracking

1. **Focus on One Award**
   - Complete SKCC Centurion first (100 contacts)
   - Then work toward Tribune (1,000)
   - Then Senator (10,000)

2. **Track Progress**
   - Check Awards tab weekly
   - Use Power Stats to verify QRP contacts
   - Review Space Weather for optimal conditions

3. **Export for Submission**
   - Export ADIF when award complete
   - Include required data fields
   - Submit to award administrator

### Database Management

1. **Regular Backups**
   - Enable auto-backup in Settings
   - Manually backup before major updates
   - Keep backup copies in multiple locations

2. **Archive Old Data**
   - Export ADIF regularly
   - Keep yearly archives
   - Prevents database bloat

3. **Data Integrity**
   - Edit form ensures clean data
   - Double-check before saving
   - Use consistent state/country names

**[:arrow_up: Back to Top](#-quick-navigation-table-of-contents)**

---

## Troubleshooting

### Contact Won't Save

**Error**: "Validation Error"

**Solution**:
- Callsign is required
- Band is required
- Mode is required
- Frequency must be > 0
- Check all highlighted fields

### Previous QSOs Not Showing

**Issue**: Right panel is empty

**Solutions**:
1. Check callsign spelling
2. Ensure previous contacts exist in database
3. Try refreshing (close and reopen Logging tab)

### Can't Find Contact to Edit

**Issue**: Contact not visible in Contacts tab

**Solutions**:
1. Clear callsign search filter
2. Set Band filter to "All Bands"
3. Change view mode to "All Contacts"
4. Scroll table to find contact

### Awards Not Updating

**Issue**: Award progress shows old numbers

**Solutions**:
1. In Settings tab, click "Verify Awards"
2. Close and reopen Awards tab
3. Check that contacts have required fields (SKCC #, State, etc.)
4. Ensure contacts are CW mode for SKCC awards

### Settings Won't Save

**Solutions**:
1. Check file permissions
2. Ensure disk space available
3. Try closing and reopening application
4. Check configuration file location

### Export/Import Issues

**Can't import ADIF**:
- Ensure ADIF file is valid format
- Check file isn't corrupted
- Try smaller chunks if file is very large

**Export shows no data**:
- Ensure at least one contact exists
- Verify contacts have all required fields
- Check export file location has write permissions

### Display/UI Issues

**Window doesn't appear**:
- Check monitor is on
- Ensure application is running (`ps aux | grep w4gns`)
- Try pressing Alt+Tab to switch windows

**Text is too small/large**:
- Settings tab → UI → Font Size
- Adjust and save
- Restart application

**[:arrow_up: Back to Top](#-quick-navigation-table-of-contents)**

---

## Data Backup & Recovery

### Automatic Backups

The application automatically backs up:
- ADIF files to Logs folder
- Database to secondary location
- On application shutdown

### Manual Backup

1. Contacts tab → Export ADIF
2. Save to external drive
3. Keep multiple versions with dates

### Recovery

1. **Restore from ADIF**:
   - File → Import ADIF
   - Select backup file
   - Contacts reloaded

2. **Restore from Database Backup**:
   - Settings tab → Database Location
   - Replace database file with backup
   - Restart application

**[:arrow_up: Back to Top](#-quick-navigation-table-of-contents)**

---

## Keyboard Shortcuts Summary

| Shortcut | Action |
|----------|--------|
| Ctrl+N | New Contact |
| Ctrl+I | Import ADIF |
| Ctrl+E | Export ADIF |
| Ctrl+, | Settings |
| Ctrl+Q | Exit |
| F1 | Help |
| Tab | Next field |
| Shift+Tab | Previous field |
| Alt+L | Logging tab |
| Alt+C | Contacts tab |
| Alt+A | Awards tab |

**[:arrow_up: Back to Top](#-quick-navigation-table-of-contents)**

---

## Advanced Features

### QRZ Integration

1. Get API key from QRZ.com account
2. Settings → QRZ Integration → Enter API Key
3. Enable "Auto Fetch"
4. When you enter a callsign, QRZ data auto-fills:
   - Operator name
   - State
   - Grid square
   - QTH/City
   - County

### SKCC Membership Database

- Application includes SKCC member list
- When you enter a call, it checks membership
- Auto-fills SKCC number if member found
- Helps identify valid SKCC contacts

### Custom Configuration

1. Settings tab → Raw Config
2. Edit YAML directly
3. Advanced options:
   - Frequency bands
   - Mode definitions
   - Award thresholds
4. Changes take effect on restart

**[:arrow_up: Back to Top](#-quick-navigation-table-of-contents)**

---

## Getting Help

### In-Application Help

- **Settings** button: Configure options
- **Tooltips**: Hover over fields for descriptions
- **Validation messages**: Clear error explanations

### Documentation Files

- **QUICK_START.md**: 5-minute quick start
- **USER_SETTINGS_GUIDE.md**: Detailed settings explanation
- **SETTINGS_REFERENCE.md**: All configuration options
- **README.md**: Full project documentation

### Contact Support

- Check GitHub Issues: github.com/anthropics/w4gns-logger
- Review documentation before contacting
- Provide error messages and steps to reproduce

**[:arrow_up: Back to Top](#-quick-navigation-table-of-contents)**

---

## About This Application

**W4GNS SKCC Logger v1.8**

A comprehensive ham radio contact logging application built for the Straight Key Century Club (SKCC) with features including:

- ✓ Contact logging with complete QSO information
- ✓ Award tracking (Centurion, Tribune, Senator, etc.)
- ✓ SKCC membership integration
- ✓ QRZ.com integration for callsign lookup
- ✓ Space weather monitoring
- ✓ Power tracking (QRP, Low, Medium, High)
- ✓ ADIF import/export
- ✓ Contact editing and correction
- ✓ Previous QSO display

**Technology Stack**:
- Framework: PyQt6
- Database: SQLite
- Python: 3.14+
- Platform: Linux, Windows, macOS

---

## License & Credits

**Made by W4GNS for the ham radio community**

73 de W4GNS 🎙️

**[:arrow_up: Back to Top](#-quick-navigation-table-of-contents)**

---

*Last Updated: October 2025*
*Version: 1.8*
