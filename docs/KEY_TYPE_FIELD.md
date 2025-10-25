# Key Type Field Documentation

**W4GNS Logger - SKCC Key Type Tracking**

---

## Overview

The key type field allows you to track which mechanical key you used for each contact. This is essential for:
- SKCC award tracking
- Mechanical key proficiency demonstration
- Triple Key Award qualification (300 QSOs using all 3 key types)
- Historical logging and analysis

---

## Key Types

The logger supports three SKCC-approved mechanical key types:

### 1. **Straight Key** (Default)

**Code:** `STRAIGHT`

**Description:** Traditional mechanical key with spring return. Requires manual creation of both dots and dashes through vertical lever motion.

**Characteristics:**
- Most skill required
- Most authentic SKCC experience
- Spring automatically returns to center
- Both dots and dashes are hand-formed
- Popular with beginners and traditionalists

**Good For:** Learning CW, developing proper hand technique, SKCC spirit

---

### 2. **Semi-Automatic Key (Bug)**

**Code:** `BUG`

**Description:** Semi-automatic key with automatic dot generation. Horizontal paddle creates dots via mechanical oscillation; manual dashes via normal lever motion.

**Characteristics:**
- Intermediate skill level
- Automatic dot generation (oscillation)
- Manual dash generation
- Faster than straight key (easier rapid dots)
- Popular among SKCC experienced operators

**Good For:** Improved speed, reduced hand fatigue, maintaining proficiency

---

### 3. **Sideswiper (Cootie)**

**Code:** `SIDESWIPER`

**Description:** Horizontal lever key used primarily by experienced operators. Creates dots and dashes through side-to-side lever motion.

**Characteristics:**
- Advanced technique
- Requires practice and skill
- Very efficient operation
- Used by speed contest operators
- Both dots/dashes from side-to-side motion
- Most difficult to master

**Good For:** Advanced operators, speed contests, mechanical key mastery

---

## Database Schema

### Contact Model

```python
# In src/database/models.py
key_type = Column(String(20), default="STRAIGHT")

# Indexed columns for efficient queries
Index("idx_key_type", "key_type")
Index("idx_key_type_band_mode", "key_type", "band", "mode")
Index("idx_skcc_key_type", "skcc_number", "key_type")
```

### Available Values

| Code | Display Name | Abbreviation |
|------|--------------|--------------|
| `STRAIGHT` | Straight Key | SK |
| `BUG` | Semi-Automatic Key (Bug) | BUG |
| `SIDESWIPER` | Sideswiper (Cootie) | SW |

---

## Usage Examples

### Adding a Contact with Key Type

```python
from src.database.models import Contact
from src.database.repository import DatabaseRepository

repo = DatabaseRepository("/path/to/database.db")

# Create contact using Straight Key
contact = Contact(
    callsign="W5XYZ",
    qso_date="20241021",
    time_on="1430",
    band="40M",
    mode="CW",
    key_type="STRAIGHT"  # Explicitly set
)
repo.add_contact(contact)

# Default is STRAIGHT if not specified
contact_default = Contact(
    callsign="K0ABC",
    qso_date="20241020",
    time_on="1200",
    band="80M",
    mode="CW"
    # key_type defaults to "STRAIGHT"
)
repo.add_contact(contact_default)

# Using a Bug
bug_contact = Contact(
    callsign="N4DEF",
    qso_date="20241019",
    time_on="1530",
    band="20M",
    mode="CW",
    key_type="BUG"
)
repo.add_contact(bug_contact)

# Using a Sideswiper
sw_contact = Contact(
    callsign="W1GHI",
    qso_date="20241018",
    time_on="0900",
    band="15M",
    mode="CW",
    key_type="SIDESWIPER"
)
repo.add_contact(sw_contact)
```

### Querying by Key Type

```python
# Get all contacts made with Straight Key
straight_contacts = repo.get_contacts_by_key_type("STRAIGHT")

# Get all contacts made with Bug
bug_contacts = repo.get_contacts_by_key_type("BUG")

# Get all contacts made with Sideswiper
sw_contacts = repo.get_contacts_by_key_type("SIDESWIPER")
```

### Key Type Statistics

```python
# Get statistics on key type usage
stats = repo.get_key_type_statistics()

print(f"Straight Key QSOs:  {stats['straight_key']}")
print(f"Bug QSOs:           {stats['bug']}")
print(f"Sideswiper QSOs:    {stats['sideswiper']}")
print(f"Total QSOs:         {stats['total_key_contacts']}")
```

### Searching by Key Type and Band

```python
# Get all Straight Key contacts on 40M
straight_40m = repo.search_contacts_by_key_type_and_band("STRAIGHT", band="40M")

# Get all Bug contacts (any band)
bug_any_band = repo.search_contacts_by_key_type_and_band("BUG")

# Get all Sideswiper on 80M
sw_80m = repo.search_contacts_by_key_type_and_band("SIDESWIPER", band="80M")
```

---

## Triple Key Award

The Triple Key Award requires:
- **300 total QSOs**
- **Using all 3 key types** (Straight, Bug, Sideswiper)

### Tracking Triple Key Progress

```python
# Get Triple Key award progress
progress = repo.get_triple_key_progress()

print(f"Straight Key QSOs:    {progress['straight_key_qsos']}")
print(f"Bug QSOs:             {progress['bug_qsos']}")
print(f"Sideswiper QSOs:      {progress['sideswiper_qsos']}")
print(f"Total QSOs:           {progress['total_qsos']}")
print(f"Key Types Used:       {progress['key_types_used']}/3")
print(f"All 3 Key Types:      {progress['all_key_types_used']}")
print(f"Triple Key Qualified: {progress['triple_key_qualified']}")
print(f"Progress to 300:      {progress['progress_to_300']}")

# Example output:
# Straight Key QSOs:    125
# Bug QSOs:             95
# Sideswiper QSOs:      80
# Total QSOs:           300
# Key Types Used:       3/3
# All 3 Key Types:      True
# Triple Key Qualified: True
# Progress to 300:      300/300
```

### Triple Key by Callsign

```python
# Track Triple Key progress for specific callsign
progress = repo.get_triple_key_progress(callsign="W5XYZ")

# Shows progress for that specific callsign's contacts
```

---

## Constants and Dropdown Lists

### Available in `src/database/constants.py`

```python
# Dictionary of key types
from src.database.constants import KEY_TYPES
# {
#     "STRAIGHT": "Straight Key",
#     "BUG": "Semi-Automatic Key (Bug)",
#     "SIDESWIPER": "Sideswiper (Cootie)",
# }

# Ordered list for dropdown menus
from src.database.constants import KEY_TYPE_CHOICES
# [
#     ("STRAIGHT", "Straight Key"),
#     ("BUG", "Semi-Automatic Key (Bug)"),
#     ("SIDESWIPER", "Sideswiper (Cootie)"),
# ]

# Default key type
from src.database.constants import DEFAULT_KEY_TYPE
# "STRAIGHT"

# Descriptions for tooltips/help text
from src.database.constants import KEY_TYPE_DESCRIPTIONS
# {
#     "STRAIGHT": "Traditional mechanical key...",
#     "BUG": "Semi-automatic key (bug)...",
#     "SIDESWIPER": "Horizontal lever key...",
# }
```

---

## GUI Integration (Dropdown)

### For Flask/Web Interface

```html
<select name="key_type" id="key_type">
  <option value="STRAIGHT" selected>Straight Key</option>
  <option value="BUG">Semi-Automatic Key (Bug)</option>
  <option value="SIDESWIPER">Sideswiper (Cootie)</option>
</select>
```

### For PyQt/Desktop Interface

```python
from src.database.constants import KEY_TYPE_CHOICES

# Create combobox
key_type_combo = QComboBox()
for code, display_name in KEY_TYPE_CHOICES:
    key_type_combo.addItem(display_name, code)
```

---

## SKCC Requirements

✅ **SKCC Policy on Key Types:**
- All SKCC activities use **mechanical keys only**
- No electronic keyers permitted
- Any of the three key types (Straight, Bug, Sideswiper) are acceptable
- Key type choice is operator preference
- Mixed key types encouraged for skill development

**Reference:** SKCC Handbook 2025, Participation Guidelines

---

## Data Validation

### Valid Key Type Values

The following values are valid:

```python
VALID_KEY_TYPES = [
    "STRAIGHT",
    "BUG",
    "SIDESWIPER"
]
```

Any other value will be rejected or default to `"STRAIGHT"`.

---

## Indexes for Performance

The following indexes are automatically created for efficient querying:

```
idx_key_type
  └─ Fast lookup by key type alone

idx_key_type_band_mode
  └─ Fast lookup by key type, band, and mode combination

idx_skcc_key_type
  └─ Fast lookup by SKCC number and key type
```

---

## Repository Methods

### `get_contacts_by_key_type(key_type: str) -> List[Contact]`
Get all contacts made with specified key type.

### `get_key_type_statistics() -> Dict[str, Any]`
Get statistics on key type usage:
```python
{
    "straight_key": 125,      # Straight Key QSOs
    "bug": 95,                # Bug QSOs
    "sideswiper": 80,         # Sideswiper QSOs
    "total_key_contacts": 300 # Total with key types tracked
}
```

### `search_contacts_by_key_type_and_band(key_type, band=None) -> List[Contact]`
Search contacts by key type and optionally by band.

### `get_triple_key_progress(callsign=None) -> Dict[str, Any]`
Get Triple Key award progress:
```python
{
    "straight_key_qsos": 125,
    "bug_qsos": 95,
    "sideswiper_qsos": 80,
    "total_qsos": 300,
    "key_types_used": 3,
    "triple_key_qualified": True,
    "progress_to_300": "300/300",
    "all_key_types_used": True
}
```

---

## Tips for Users

1. **Always Set Key Type:** While "STRAIGHT" is the default, explicitly set the key type used to ensure accurate tracking

2. **Log Consistently:** When changing keys during a session, log each QSO with the correct key type

3. **Track for Triple Key:** If pursuing the Triple Key Award, ensure you're using all three key types and tracking them

4. **Review Statistics:** Periodically check `get_key_type_statistics()` to see your key type distribution

5. **SKCC Compliance:** Remember that SKCC strictly requires mechanical keys - electronic keyers are not permitted for SKCC activities

---

## Integration with Other Features

### SKCC Number + Key Type

```python
# Get SKCC contacts made with Straight Key
skcc_straight = repo.get_contacts_by_key_type("STRAIGHT")
skcc_contacts = [c for c in skcc_straight if c.skcc_number]

# Better method: direct SKCC query already filters for CW
skcc_cw = repo.get_contacts_by_skcc("SKCC1234")
# Key types will be in the returned contacts
```

### Awards Integration

Key type tracking supports:
- **Triple Key Award** - All 3 key types, 300 QSOs
- **SKCC Events** - Track key type used during monthly/annual events
- **Statistics** - Analyze operator preferences and skill development

---

## Reference

- **SKCC Handbook:** Section "Participation Guidelines - Key Types"
- **Triple Key Award:** SKCC Handbook, Addendum II
- **Database Schema:** `src/database/models.py` (line 76)
- **Constants:** `src/database/constants.py`
- **Repository:** `src/database/repository.py` (lines 277-365)

---

*Last Updated: October 21, 2025*
