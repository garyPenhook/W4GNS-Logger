# ADIF Export Guide - SKCC Integration

**W4GNS Logger - ADIF 3.1.5 Export Reference**

---

## Overview

ADIF (Amateur Data Interchange Format) is the standard format for exchanging amateur radio contact logs between software applications, services, and websites.

**Current Standard:** ADIF 3.1.5
**Specification:** https://adif.org/
**SKCC Support:** Official fields since ADIF 3.0.3

---

## SKCC Fields in ADIF

The ADIF standard includes **two dedicated SKCC fields** for proper membership tracking:

### 1. **SKCC Field** (Contacted Station)

```
<SKCC:5>12345C
```

| Property | Value |
|----------|-------|
| **Field Name** | `SKCC` |
| **Data Type** | String (S) |
| **Description** | Straight Key Century Club member number of the *contacted station* |
| **Added** | ADIF 3.0.3 (2015-2016) |
| **Usage** | Records the SKCC number of the station you worked |

**Example Values:**
- `12345C` - Centurion member #12345
- `14276T` - Tribune member #14276
- `14276Tx4` - Tribune level 4 member #14276
- `9876S` - Senator member #9876
- *(blank)* - Non-SKCC member

---

### 2. **MY_SKCC Field** (Your Station)

```
<MY_SKCC:6>14276T
```

| Property | Value |
|----------|-------|
| **Field Name** | `MY_SKCC` |
| **Data Type** | String (S) |
| **Description** | Your own (logging operator's) Straight Key Century Club member number |
| **Added** | ADIF 3.0.3 (2015-2016) |
| **Usage** | Records your SKCC membership number |

**Usage in W4GNS Logger:**
- Set once in application configuration
- Automatically included in all exported ADIF files
- Represents the primary operator's SKCC status

---

## SKCC Membership Number Format

SKCC membership numbers include **achievement level suffixes**:

### Achievement Levels

| Suffix | Level | Requirement | Notes |
|--------|-------|-------------|-------|
| **C** | **Centurion** | 100 unique SKCC member contacts | Entry level award |
| **T** | **Tribune** | 50 contacts with C, T, or S members | After earning Centurion |
| **Tx1-Tx8** | **Tribune Levels** | Progressive contact requirements | Shows progression toward Senator |
| **S** | **Senator** | 200 contacts with T or S members | Highest award (600+ total contacts) |

### Examples

```
12345C        # Centurion (basic level)
14276T        # Tribune (mid level)
14276Tx4      # Tribune at level 4 (progressing)
9876S         # Senator (highest level)
```

---

## ADIF Format and Syntax

### Field Format

ADIF fields use this format:

```
<FIELDNAME:LENGTH>VALUE
```

### SKCC Field Examples

```
<SKCC:5>12345C
<SKCC:7>14276Tx4
<MY_SKCC:6>14276T
```

### Complete QSO Record with SKCC

```
<QSO_DATE:8>20241021
<TIME_ON:4>1430
<CALL:6>W5XYZ
<BAND:3>40M
<MODE:2>CW
<SKCC:5>12345C
<MY_SKCC:6>14276T
<EOR>
```

---

## W4GNS Logger ADIF Export

### Database to ADIF Mapping

**W4GNS Logger Fields → ADIF Standard Fields:**

| W4GNS Field | ADIF Field | Notes |
|-------------|-----------|-------|
| `callsign` | `CALL` | Contacted station callsign |
| `qso_date` | `QSO_DATE` | Format: YYYYMMDD |
| `time_on` | `TIME_ON` | Format: HHMM |
| `band` | `BAND` | e.g., "40M", "80M" |
| `mode` | `MODE` | "CW" for SKCC |
| `frequency` | `FREQ` | MHz frequency |
| `rst_sent` | `RST_SENT` | Signal report sent (CW: 579, etc.) |
| `rst_rcvd` | `RST_RCVD` | Signal report received |
| `skcc_number` | `SKCC` | ← **IMPORTANT: Contacted station SKCC #** |
| `operator_skcc` | `MY_SKCC` | Your own SKCC number (configuration) |
| `country` | `COUNTRY` | Contacted station location |
| `state` | `STATE` | US state (if applicable) |
| `dxcc` | `DXCC` | DXCC entity number |
| `tx_power` | `TX_PWR` | Transmit power in watts |
| `notes` | `COMMENT` | Any additional comments |

### Field Placement in ADIF

**Standard ADIF Export Order** (recommended by ADIF spec):

```
QSO record fields (in order):
1. <CALL> - Contacted station
2. <QSO_DATE> - Date of contact
3. <TIME_ON> - Time started
4. <BAND> - Band
5. <MODE> - Operating mode
6. <FREQ> - Frequency
7. <RST_RCVD> - Signal report received
8. <RST_SENT> - Signal report sent
9. ...
10. <SKCC> - Contacted station SKCC number ← HERE
11. ...
12. <MY_SKCC> - Your SKCC number ← AND HERE
13. <EOR> - End of record marker
```

---

## Exporting SKCC Data from W4GNS Logger

### Python Code Example

```python
from src.database.repository import DatabaseRepository
from src.database.models import Contact

repo = DatabaseRepository("/path/to/database.db")

def export_to_adif(filename, my_skcc_number="14276T"):
    """Export contacts to ADIF file with SKCC fields"""

    contacts = repo.get_all_contacts()

    with open(filename, 'w') as f:
        # ADIF header
        f.write("ADIF Export from W4GNS Logger\n")
        f.write("Version: 3.1.5\n")
        f.write("Program: W4GNS Logger\n")
        f.write("<ADIF_VER:5>3.1.5\n")
        f.write("<PROGRAM:12>W4GNS Logger\n")
        f.write("<EOH>\n\n")

        # Write QSO records
        for contact in contacts:
            f.write(f"<CALL:{len(contact.callsign)}>{contact.callsign}\n")
            f.write(f"<QSO_DATE:8>{contact.qso_date}\n")
            f.write(f"<TIME_ON:4>{contact.time_on}\n")
            f.write(f"<BAND:{len(contact.band)}>{contact.band}\n")
            f.write(f"<MODE:2>CW\n")

            # SKCC field for contacted station
            if contact.skcc_number:
                f.write(f"<SKCC:{len(contact.skcc_number)}>{contact.skcc_number}\n")

            # Your SKCC number
            f.write(f"<MY_SKCC:{len(my_skcc_number)}>{my_skcc_number}\n")

            # Other fields
            if contact.country:
                f.write(f"<COUNTRY:{len(contact.country)}>{contact.country}\n")
            if contact.notes:
                f.write(f"<COMMENT:{len(contact.notes)}>{contact.notes}\n")

            f.write("<EOR>\n")

# Export
export_to_adif("/tmp/w4gns_export.adi", my_skcc_number="14276T")
```

### ADIF Output Example

```
ADIF Export from W4GNS Logger
Version: 3.1.5
Program: W4GNS Logger
<ADIF_VER:5>3.1.5
<PROGRAM:12>W4GNS Logger
<EOH>

<CALL:5>W5XYZ
<QSO_DATE:8>20241021
<TIME_ON:4>1430
<BAND:3>40M
<MODE:2>CW
<SKCC:5>12345C
<MY_SKCC:6>14276T
<COUNTRY:14>United States
<EOR>

<CALL:6>K0ABC
<QSO_DATE:8>20241020
<TIME_ON:4>1200
<BAND:3>80M
<MODE:2>CW
<SKCC:7>14276Tx4
<MY_SKCC:6>14276T
<EOR>
```

---

## Importing ADIF with SKCC Fields

### Parsing SKCC from ADIF

```python
def parse_adif_file(filename):
    """Parse ADIF file and extract SKCC numbers"""

    contacts = []
    current_record = {}

    with open(filename, 'r') as f:
        for line in f:
            line = line.strip()

            # Parse field
            if line.startswith('<') and line.endswith('>'):
                parts = line.split(':')
                if len(parts) >= 2:
                    # Extract field name, length, and value
                    field_match = parts[0].strip('<')
                    field_length = int(parts[1].split('>')[0])
                    field_value = '>'.join(parts[2:]).rstrip('>')

                    current_record[field_match] = field_value

            # End of record
            if '<EOR>' in line or '</EOR>' in line:
                if current_record:
                    contacts.append(current_record)
                    current_record = {}

    return contacts

# Use
contacts = parse_adif_file("/tmp/import.adi")
for contact in contacts:
    if 'SKCC' in contact:
        print(f"{contact['CALL']}: SKCC #{contact['SKCC']}")
```

---

## Software Compatibility

### SKCC Field Support by Logging Software

| Software | SKCC Support | MY_SKCC | Notes |
|----------|--------------|---------|-------|
| **SKCC Logger** | ✅ Full | ✅ Yes | Official SKCC software, recommended |
| **MacLoggerDX** | ✅ Full | ✅ Yes | Regular SKCC database updates |
| **N1MM Logger+** | ✅ Full | ✅ Yes | Standard ADIF support |
| **Log4OM** | ✅ Full | ✅ Yes | Imports/exports ADIF 3.1.5 |
| **fldigi** | ✅ Basic | ✅ Yes | Internal log to ADIF |
| **ADIF Master** | ✅ Full | ✅ Yes | View/edit ADIF files |
| **DXKeeper** | ✅ Full | ✅ Yes | DXLabs suite component |
| **W4GNS Logger** | ✅ Full | ✅ Yes | Standard ADIF export |

---

## Best Practices

### 1. **Always Use SKCC, Never Comments**
✅ CORRECT:
```
<SKCC:5>12345C
```

❌ INCORRECT:
```
<COMMENT:18>SKCC member 12345C
```

### 2. **Include Achievement Suffix**
✅ CORRECT:
```
<SKCC:5>12345C
<SKCC:7>14276Tx4
```

❌ INCORRECT:
```
<SKCC:5>12345
<SKCC:5>14276
```

### 3. **Blank for Non-Members**
✅ CORRECT (omit or leave blank for non-members):
```
<CALL:5>N0NEM
<MODE:2>CW
<EOR>
```

### 4. **Set MY_SKCC Consistently**
- Set your SKCC number in application configuration
- Include in all exported files
- Update when achievement level changes

### 5. **Preserve Suffixes During Import**
- When importing ADIF, preserve the complete SKCC string including suffixes
- Don't strip off C, T, S, or Tx# designations

---

## SKCC Database Integration

The SKCC Logger software maintains a live database of SKCC membership that includes:
- Member numbers
- Current achievement levels (C, T, S, Tx#)
- Address information
- Database URL: https://www.skccgroup.com/ (members only)

### Automatic SKCC Lookup
Professional SKCC software (SKCC Logger) automatically:
1. Looks up callsign in SKCC member database
2. Populates SKCC number and current suffix
3. Updates based on QSO date (to show correct level at time of contact)

---

## Troubleshooting ADIF/SKCC Issues

### Issue: SKCC field not recognized by software
- **Solution:** Ensure exporting ADIF 3.1.5 or later
- **Check:** Field name is exactly `SKCC` (case-sensitive)

### Issue: SKCC suffix lost during import
- **Solution:** Ensure field stored as String (S) type, not Integer
- **Check:** Value includes C, T, or S suffix

### Issue: MY_SKCC not in export
- **Solution:** Configure your SKCC number in application settings
- **Check:** MY_SKCC field included in export routine

### Issue: Non-members showing blank SKCC
- **Expected:** This is correct behavior
- **Note:** Only members have SKCC numbers

---

## W4GNS Logger ADIF Implementation

### Configuration

**Application Settings (config/settings.py):**
```python
# Your SKCC membership information
MY_SKCC_NUMBER = "14276T"  # Your SKCC number with suffix
```

### Export Function

**Usage:**
```python
from src.database.adif_export import ADIFExporter

exporter = ADIFExporter(db_path="/path/to/database.db")
exporter.export_to_file("/path/to/export.adi", my_skcc="14276T")
```

### Import Function

**Usage:**
```python
from src.database.adif_import import ADIFImporter

importer = ADIFImporter(db_path="/path/to/database.db")
contacts_imported = importer.import_from_file("/path/to/import.adi")
```

---

## Reference Documents

- **ADIF Specification:** https://adif.org/
- **ADIF Field Reference:** https://adif.org/305
- **SKCC Official:** https://www.skccgroup.com/
- **SKCC Logger User Guide:** https://www.ac2c.net/skcclogger/userguide/
- **DXLabs ADIF Guide:** https://www.dxlabsuite.com/ADIF.htm

---

## Summary

| Item | Answer |
|------|--------|
| **SKCC field in ADIF?** | Yes - standard field `SKCC` |
| **Where to put SKCC number?** | `<SKCC>` field, NOT comments |
| **Your own SKCC number?** | `<MY_SKCC>` field |
| **Field type?** | String (S) - preserves suffixes |
| **Suffixes required?** | Yes - include C, T, Tx#, or S |
| **Non-members?** | Leave `<SKCC>` field blank or omit |
| **ADIF version?** | 3.1.5 (SKCC fields since 3.0.3) |

---

*Last Updated: October 21, 2025*
*ADIF Specification Version: 3.1.5*
*SKCC Handbook: 2025*
