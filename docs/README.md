# W4GNS Logger Documentation

This directory contains documentation for the W4GNS Logger application, with a focus on SKCC (Straight Key Century Club) integration and award tracking.

## Documentation Files

### 📖 SKCC Awards & Operating Guide
**File:** [`SKCC_AWARDS_GUIDE.md`](SKCC_AWARDS_GUIDE.md)

Comprehensive guide to SKCC membership, operating awards, endorsements, and events. Based on the official SKCC Handbook 2025.

**Contents:**
- SKCC Membership & Rules
- Operating Awards & Endorsements (Centurion, Tribune, Senator)
- Award Programs (Geographic, Skills, Duration-based)
- Monthly Events & Schedules
- Annual Events
- Key Resources
- Database Integration Notes

**Best For:** Understanding SKCC award structure and requirements

---

### ⚡ SKCC Quick Reference
**File:** [`SKCC_QUICK_REFERENCE.md`](SKCC_QUICK_REFERENCE.md)

Quick lookup guide for SKCC awards, events, and rules. Includes W4GNS Logger-specific features.

**Contents:**
- SKCC Tiered Endorsements (C, T, S levels)
- Core Awards Summary
- Monthly Events Calendar
- Annual Events
- Operating Rules
- W4GNS Logger SKCC Features
- Award Hunting Tips

**Best For:** Quick lookups while operating or planning contacts

---

## SKCC Handbook

**File:** `../SKCC_Handbook_2025_English.pdf` (in project root)

Official SKCC Handbook 2025 (English) - 7 pages

**Contents:**
- Participation Guidelines
- Online Community Resources
- CW Operating Guidance
- Logging and Award Applications
- Monthly and Annual Events
- Web Resources and Support

---

## W4GNS Logger SKCC Integration

### Key Features

1. **SKCC Number Field**
   - Store SKCC member numbers in contacts
   - Indexed for fast lookups
   - Model: `Contact.skcc_number`

2. **CW-Only Enforcement**
   - SKCC contacts must be CW mode
   - Default mode is "CW"
   - Validation on add/update operations
   - Query methods automatically filter for CW

3. **SKCC Repository Methods**
   ```python
   repo.get_contacts_by_skcc(skcc_number)      # Get CW contacts
   repo.get_skcc_statistics()                   # Get SKCC stats
   repo.search_skcc_by_band(skcc_number, band)  # Search by band
   ```

4. **Award Tracking**
   - Supports SKCC award program tracking via AwardProgress table
   - Centurion, Tribune, Senator level tracking
   - Geographic and skill-based awards
   - Endorsements and multiples

### Database Schema

**Contact Table**
- `skcc_number` (String, optional) - SKCC member number
- `mode` (String, default="CW") - Contact mode (CW-only for SKCC)
- Indexed: `idx_skcc_number`, `idx_skcc_callsign_band_mode`

**AwardProgress Table**
- Tracks SKCC awards: Centurion, Tribune, Senator, WAS, WAC, etc.
- Supports mode-specific and band-specific endorsements

---

## Quick Start: Logging SKCC QSOs

### Adding a Contact with SKCC Number

```python
from src.database.models import Contact
from src.database.repository import DatabaseRepository

repo = DatabaseRepository("/path/to/database.db")

# Create SKCC CW contact
contact = Contact(
    callsign="W5XYZ",
    qso_date="20241021",
    time_on="1430",
    band="40M",
    mode="CW",  # Default and required for SKCC
    skcc_number="SKCC1234",
    country="United States"
)

# Add to database (validates SKCC constraints)
repo.add_contact(contact)
```

### Querying SKCC Contacts

```python
# Get all CW contacts for an SKCC member
contacts = repo.get_contacts_by_skcc("SKCC1234")

# Get statistics
stats = repo.get_skcc_statistics()
print(f"Total SKCC contacts: {stats['total_skcc_contacts']}")
print(f"Unique SKCC members: {stats['unique_skcc_members']}")

# Search by band
band_40m = repo.search_skcc_by_band("SKCC1234", band="40M")
```

---

## SKCC Resources

| Resource | Purpose |
|----------|---------|
| **SKCC Home Page** | Latest news, events, resources | skccgroup.com |
| **Discussion Forum** | Community discussion forum | groups.io (SKCC) |
| **SkedPage** | Real-time meeting place for arranging contacts | On SKCC website |
| **SKCC Logger** | Award tracking tool (recommended) | Files & Downloads on SKCC site |
| **Elmer Program** | Free CW mentoring | 7114 kHz |
| **Event Calendar** | Upcoming events | skccgroup.com |

---

## SKCC Operating Rules (Key Points)

✅ **Required:**
- Mechanical keys only (straight key, bug, or sideswiper)
- CW mode exclusively
- SKCC member number for award tracking

❌ **Not Allowed:**
- Electronic keyers
- Non-mechanical keying devices
- Non-CW modes for SKCC activities

---

## Contact & Support

**SKCC Board of Directors:** skccboard@skccgroup.com

**W4GNS Logger Issues:** See project repository

---

## Version Information

- **SKCC Handbook Version:** 2025 (English)
- **W4GNS Logger Updated:** October 21, 2025
- **Documentation Updated:** October 21, 2025

---

## Related Documentation

- Database Models: `src/database/models.py`
- Repository Methods: `src/database/repository.py`
- SKCC Handbook PDF: `SKCC_Handbook_2025_English.pdf` (project root)

---

*SKCC Documentation - W4GNS Logger Project*
