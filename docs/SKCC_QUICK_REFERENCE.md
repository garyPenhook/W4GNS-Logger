# SKCC Quick Reference Guide

**W4GNS Logger SKCC Integration**

---

## SKCC Tiered Endorsements

```
CENTURION "C"        TRIBUNE "T"              SENATOR "S"
├─ 100 members       ├─ 50 T/C/S members      └─ 200 T/S members
├─ Cx2: 200          ├─ Tx2: 100 contacts         (600+ total)
├─ Cx3: 300          ├─ Tx3: 150 contacts
└─ etc.              ├─ Tx8: 400+ contacts
                     └─ → qualifies for S
```

---

## Core Awards Summary

### Endorsement Levels (Most Important)

| Level | Name | Goal | Next Step |
|-------|------|------|-----------|
| 1 | Centurion (C) | 100 SKCC members | Become Tribune |
| 2 | Tribune (T) | 50 C/T/S members | Reach Tx8 (400+ contacts) |
| 3 | Senator (S) | 200 more T/S members | Highest award |

### Geographic Awards

- **WAS** - All 50 US states
- **WAC** - All 6 continents
- **Canadian Maple** - 10 Canadian provinces/territories
- **DXC/DXQ** - International contacts (multiples of 25)

### Operating Skill Awards

- **QRP** - Low power contacts (1-5W)
- **QRP Miles Per Watt** - Distance/power ratio (1000+ MPW)
- **Triple Key** - 300 QSOs with 3 different key types
- **PFX** - Working diverse geographic prefixes

### Duration Awards

- **Ragchew (RC)** - 30+ minute conversations
- **Marathon (MAR)** - 100 QSOs each 60+ minutes

---

## Monthly Events Calendar

| Event | When | Duration | Type | Notes |
|-------|------|----------|------|-------|
| **WES** | 2nd Sat | 36h | Competition | Different theme monthly |
| **SKS** | 4th Wed | 2h | Sprint | Original SKCC event |
| **SKSE** | 1st Thu | 2h | Sprint | European focus, QRS segments |
| **SSS** | 1st day | 24h | Informal | Slow speed (~10-15 WPM) |
| **SKSA** | Varies | 2h | Sprint | Asia Region 3 focus |
| **OQS** | Varies | 12h | Informal | Pacific focus, ≤12 WPM |
| **Monthly Brag** | All month | - | Informal | Unique members worked |

---

## Annual Events

| Event | Month | Duration | Focus |
|-------|-------|----------|-------|
| **Straight Key Month (SKM)** | January | Full month | Club anniversary, 200+ operators |
| **Canadian Straight Key Month** | September | Full month | Canadian operators |
| **SKCC QSO Party** | June (3rd Sat) | 36h | Informal socializing |

---

## SKCC Operating Rules

### Key Requirement (CRITICAL)

**MUST USE MECHANICAL KEYS ONLY:**
- ✅ Straight Key
- ✅ Semi-Automatic Key (Bug)
- ✅ Sideswiper (Cootie)
- ❌ Electronic Keyers (not allowed for SKCC)

### Mode Requirement

**CW ONLY** - All SKCC activities, awards, and contests are CW mode exclusively

### Elmer Program

**Beginner Support Available:**
- **Frequency:** 7114 kHz
- **Speed:** Accommodating to beginners
- **Help:** Free mentoring from experienced members

---

## W4GNS Logger SKCC Features

### SKCC Number Field

```python
# Add SKCC member number to contacts
contact.skcc_number = "SKCC1234"
contact.mode = "CW"  # Enforced - CW only for SKCC

# Query SKCC contacts
contacts = repo.get_contacts_by_skcc("SKCC1234")

# Get statistics
stats = repo.get_skcc_statistics()
# {'total_skcc_contacts': X, 'unique_skcc_members': Y}

# Search by band
forty_meter = repo.search_skcc_by_band("SKCC1234", band="40M")
```

### CW Default Mode

```python
# When creating contact without specifying mode
contact = Contact(
    callsign="W5XYZ",
    qso_date="20241020",
    time_on="1430",
    band="40M"
    # mode defaults to "CW"
)
```

### Validation

```python
# SKCC-only validation
try:
    contact = Contact(
        callsign="K0ABC",
        qso_date="20241020",
        time_on="1430",
        band="80M",
        mode="SSB",
        skcc_number="SKCC1234"  # ERROR!
    )
    repo.add_contact(contact)
except ValueError as e:
    # "SKCC contacts must be CW mode only. Got mode: SSB"
```

---

## Important Links

| Resource | Purpose | Link |
|----------|---------|------|
| **SKCC Home** | Latest news & events | skccgroup.com |
| **Discussion Forum** | Community discussion | groups.io (SKCC) |
| **SkedPage** | Real-time meeting place | On SKCC website |
| **SKCC Logger** | Award tracking tool | In Files & Downloads |
| **Event Calendar** | Upcoming events | skccgroup.com |

---

## Handbook Reference

**Official Document:** SKCC_Handbook_2025_English.pdf (in project root)

**Contact:** skccboard@skccgroup.com

---

## Quick Award Hunting Tips

1. **Start with Centurion** - Work 100 different SKCC members
2. **Join Monthly Events** - Most accessible way to find SKCC operators
3. **Use SkedPage** - See who's active and arrange contacts
4. **Check Skill Level** - Mix experienced operators with beginners
5. **Multiple Endorsements** - Work toward Tribune, Senator levels
6. **Geographic Awards** - Combine with WAS, WAC goals
7. **Log Accurately** - Use W4GNS Logger to track progress toward awards

---

*Last Updated: October 21, 2025*
