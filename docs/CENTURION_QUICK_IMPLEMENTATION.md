# Centurion Award Quick Implementation Guide

## One-Page Implementation Checklist

Follow these 5 steps to add Centurion award tracking to the W4GNS Logger.

---

## Step 1: Create Award Program Class (5 minutes)

Create: `src/awards/centurion.py`

Key requirements:
- Inherit from `AwardProgram` base class
- Implement 4 abstract methods: `validate()`, `calculate_progress()`, `get_requirements()`, `get_endorsements()`
- Count unique SKCC members (base number, ignore C/T/S suffixes)
- Requirement: 100 unique members at CW mode
- Support endorsement levels: C, Cx2, Cx3... Cx10+

---

## Step 2: Add Repository Methods (10 minutes)

Edit: `src/database/repository.py`

Add two methods to `DatabaseRepository` class:

```python
def analyze_centurion_progress(self, skcc_number: str = None) -> Dict[str, Any]:
    # Returns: unique_members, required, qualified, progress_pct, endorsement_level
    # Query: Contact where skcc_number IS NOT NULL and mode == "CW"
    # Count: DISTINCT base_skcc (remove C/T/S/x suffixes)

def get_centurion_statistics(self) -> Dict[str, Any]:
    # Returns: total_skcc_contacts, unique_skcc_members, centurion_qualified
    # Query: All CW SKCC contacts, distinct members
```

---

## Step 3: Create UI Widget (15 minutes)

Create: `src/ui/centurion_progress_widget.py`

Key sections:
1. **Progress Bar** - Shows members/100 with SKCC orange color (#FF6B35)
2. **Status Label** - "Members: X/100 | Status: [QUALIFIED|Not Qualified]"
3. **Endorsement Levels** - Checklist of C, Cx2, Cx3... Cx10+
4. **Recent Members Table** - Last 10 unique SKCC members worked

Features:
- Auto-refresh every 10 seconds (QTimer)
- Call `db.analyze_centurion_progress()` on refresh
- Update labels and progress bar

---

## Step 4: Integrate into Main Window (5 minutes)

Edit: `src/ui/main_window.py`

In `_create_awards_tab()` method:

```python
# After imports
from src.ui.centurion_progress_widget import CenturionProgressWidget

# In _create_awards_tab
centurion_widget = CenturionProgressWidget(self.db)
layout.addWidget(centurion_widget)
```

---

## Step 5: Update Documentation (5 minutes)

Files:
- `docs/AWARD_IMPLEMENTATION_PATTERN.md` - Already complete reference
- `docs/SKCC_AWARDS_GUIDE.md` - Already has Centurion details
- Create `docs/CENTURION_QUICK_IMPLEMENTATION.md` - This file

---

## Testing Checklist

- [ ] Unit test: `CenturionAward.validate()` with various inputs
- [ ] Unit test: `CenturionAward.calculate_progress()` with 50, 100, 200 contacts
- [ ] Integration test: `analyze_centurion_progress()` with test database
- [ ] UI test: CenturionProgressWidget renders correctly
- [ ] UI test: Progress bar updates on new contacts
- [ ] Manual test: Load real database and verify calculations

---

## Key Implementation Details

### SKCC Number Parsing

SKCC numbers include achievement suffixes:
- `1234C` - Centurion
- `1234T` or `1234Tx1` - Tribune level 1
- `1234Tx8` - Tribune level 8
- `1234S` - Senator

Strip suffixes to get base number:
```python
base_skcc = skcc_number.rstrip('CTStx0123456789')
```

### Database Constraints

- SKCC contacts are **CW-only** (enforced in `Contact.validate_skcc()`)
- Contact.skcc_number field is String(20)
- Indexed for performance: `Index("idx_skcc_number")`

### UI Colors

- Progress bar: SKCC orange `#FF6B35`
- Qualified status: green with bold font
- Not qualified: default text

### Auto-Refresh

- QRPProgressWidget: 5 seconds
- PowerStatsWidget: 10 seconds
- CenturionProgressWidget: 10 seconds (recommend for consistency)

---

## Dependency Chain

```
CenturionProgressWidget
    ├── uses: DatabaseRepository.analyze_centurion_progress()
    │   └── uses: Contact model (skcc_number, mode fields)
    │
    └── uses: QTimer for auto-refresh
```

---

## Database Fields Used

From Contact model (src/database/models.py):

| Field | Type | Purpose |
|-------|------|---------|
| skcc_number | String(20) | SKCC member number with suffix |
| mode | String(20) | Operating mode (must be "CW") |
| qso_date | String(8) | Contact date (YYYYMMDD) |
| time_on | String(4) | Contact time (HHMM) |
| band | String(10) | Band (40M, 20M, etc.) |
| callsign | String(12) | Remote station callsign |

---

## Performance Considerations

### Database Indexes

Already exist:
- `idx_skcc_number` - On skcc_number field
- `idx_skcc_callsign_band_mode` - Composite on skcc_number, callsign, band, mode

No additional indexes needed.

### Query Optimization

```python
# Good: Filters at query level
session.query(Contact).filter(
    Contact.skcc_number.isnot(None),
    Contact.mode == "CW"
).all()

# Less efficient: Filter in Python
all_contacts = session.query(Contact).all()
skcc_contacts = [c for c in all_contacts if c.skcc_number and c.mode == "CW"]
```

---

## Common Pitfalls

1. **Counting duplicates**: Remember to use `set()` for unique members
2. **Suffix handling**: Must strip C/T/S/x from base number
3. **Non-CW mode**: Filter for mode == "CW" (SKCC requirement)
4. **Widget lifecycle**: Stop QTimer in `closeEvent()` to prevent memory leaks
5. **Database session**: Always close session in `finally` block

---

## Reference Implementation Files

Location: `/home/w4gns/Projects/W4GNS Logger`

### Existing Award Implementations

- `src/awards/base.py` - Base class to inherit from
- `src/awards/dxcc.py` - DXCC award example

### Existing UI Widgets

- `src/ui/qrp_progress_widget.py` - QRP widget (similar structure)
- `src/ui/power_stats_widget.py` - Power stats widget (similar structure)

### Database Layer

- `src/database/models.py` - Contact and AwardProgress models
- `src/database/repository.py` - Repository pattern implementation

---

## Testing with Mock Data

Create test contacts:

```python
from src.database.models import Contact

# Test member 1: Centurion
c1 = Contact(
    callsign="W5XYZ",
    skcc_number="9999C",
    qso_date="20251025",
    time_on="1400",
    band="20M",
    mode="CW"
)

# Test member 2: Tribune
c2 = Contact(
    callsign="N0ABC",
    skcc_number="8888Tx2",
    qso_date="20251025",
    time_on="1430",
    band="40M",
    mode="CW"
)

# Create 100+ test contacts to test Centurion qualification
for i in range(100):
    contact = Contact(
        callsign=f"W{i}ABC",
        skcc_number=f"{1000+i}C",
        qso_date="20251025",
        time_on=f"{1400 + (i % 60):04d}",
        band="20M",
        mode="CW"
    )
    db.add_contact(contact)
```

---

## Troubleshooting

| Issue | Cause | Solution |
|-------|-------|----------|
| Widget shows 0 members | No SKCC contacts | Insert test data or import ADIF |
| Progress bar stuck | Timer not running | Check closeEvent() cleanup |
| Duplicate members counted | Not using set() | Use set() to deduplicate |
| Mode filter not working | Check Contact.mode values | May need case-insensitive compare |
| SKCC number parsing wrong | Suffix stripping logic | Test with real SKCC numbers like "1234Tx8" |

---

## Next Steps After Implementation

1. Write unit and integration tests
2. Add Centurion to Awards dashboard
3. Consider Tribune and Senator awards (similar pattern)
4. Add band-specific Centurion variants (if needed)
5. Export Centurion achievement to ADIF/CSV

---

End of Quick Implementation Guide

For detailed information, see: `/home/w4gns/Projects/W4GNS Logger/docs/AWARD_IMPLEMENTATION_PATTERN.md`
