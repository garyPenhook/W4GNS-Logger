# SKCC Contact History & Award Eligibility Window

**W4GNS Logger - Contact Lookup Feature**

---

## Overview

When logging an SKCC contact, operators need to quickly see:
1. Previous contacts with that SKCC member
2. What achievement level (suffix) they had at each contact date
3. Current eligibility for awards based on total contacts

This window provides real-time visibility into contact history and award progress.

---

## Features

### 1. Quick Callsign/SKCC Lookup

**Search Options:**
- By Callsign (e.g., "W5XYZ")
- By SKCC Number (e.g., "SKCC12345")
- By Callsign Prefix (e.g., "W5")

**Auto-Complete:**
- Suggests previous contacted callsigns
- Shows SKCC number if available
- Shows last contact date

---

### 2. Contact History Display

**Table showing all previous contacts with this station:**

| Date | Time | Band | Mode | Key Type | SKCC # at Contact | Current SKCC # | Notes |
|------|------|------|------|----------|-------------------|-----------------|-------|
| 2024-10-21 | 14:30 | 40M | CW | STRAIGHT | 12345C | 12345Tx2 | Good signal |
| 2024-09-15 | 09:00 | 80M | CW | BUG | 12345C | 12345Tx2 | Rag chew |
| 2024-08-20 | 19:45 | 20M | CW | SIDESWIPER | 12345C | 12345Tx2 | New member then |

**Key Information:**
- Shows SKCC suffix at time of each contact (historical accuracy)
- Highlights if station has achieved new level since last contact
- Shows key type used for each contact (useful for Triple Key tracking)
- Color-coded rows for quick visual scanning

---

### 3. Award Eligibility Analysis

**Real-time calculation showing:**

#### Centurion Achievement
```
Status: QUALIFIED ✅
  • Requirement: 100 unique SKCC member contacts
  • Your total: 127 SKCC contacts
  • Achievement Level: C (Centurion)
  • Date Achieved: 2023-01-15
```

#### Tribune Achievement
```
Status: QUALIFIED ✅
  • Requirement: 50 contacts with C, T, or S members (after Centurion)
  • Your total: 89 qualified contacts
  • Progress: 89/50 (178% complete)
  • Achievement Level: Tx3
  • Date Achieved: 2023-06-20
```

#### Senator Achievement
```
Status: IN PROGRESS ⏳
  • Requirement: 200 contacts with T or S members (after Tribune Tx8)
  • Current Tribune Level: Tx3 (need Tx8 first)
  • Contacts needed: Tribune must reach Tx8, then 200 T/S contacts
  • Next Step: Reach Tribune Tx8 level
```

#### Other Awards Tracking
```
Triple Key Progress:
  ├─ Straight Key: 42 QSOs ✅
  ├─ Bug: 35 QSOs ✅
  ├─ Sideswiper: 28 QSOs ✅
  └─ Status: 105/300 contacts (35% to Triple Key)

Geographic Awards:
  ├─ WAS (Worked All States): 47/50 states ⏳
  ├─ WAC (All Continents): 5/6 continents ⏳
  └─ Canadian Maple: 8/10 provinces ⏳
```

---

### 4. Current Station Status

**Display current achievement level and progress:**

```
SKCC #12345 - Tribune (Tx2)
├─ Member Since: 2023-01-01
├─ Total SKCC QSOs: 127
├─ Current Level: Tribune Tx2
├─ Progress to Tx3: 15 more contacts
├─ Centurion Contacts: 100
├─ Tribune Contacts: 27
├─ Senator Contacts: 0
└─ Last Contact: 2024-10-21 @ 14:30 UTC
```

---

## Window Layout

### Design Mockup

```
┌─────────────────────────────────────────────────────────────────────┐
│ SKCC CONTACT HISTORY & AWARD ELIGIBILITY                    [_][□][X]│
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│ Lookup: [W5XYZ_____________] [Search ✓]  [Clear]                   │
│                                                                      │
├─────────────────────────────────────────────────────────────────────┤
│ STATION: W5XYZ  │  SKCC: 12345C → 12345Tx2  │  Last: 2024-10-21    │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│ PREVIOUS CONTACTS:                                                  │
│ ┌──────────────────────────────────────────────────────────────────┐│
│ │ Date       Time  Band Mode Key Type  SKCC@Contact Current Notes  ││
│ ├──────────────────────────────────────────────────────────────────┤│
│ │ 2024-10-21 14:30 40M  CW   STRAIGHT 12345C       Tx2     Good ││
│ │ 2024-09-15 09:00 80M  CW   BUG      12345C       Tx2     Rag  ││
│ │ 2024-08-20 19:45 20M  CW   SIDESWP  12345C       Tx2     New  ││
│ │ 2024-07-10 16:20 15M  CW   STRAIGHT 12345C       Tx2           ││
│ │ ... (scroll to see more)                                       ││
│ └──────────────────────────────────────────────────────────────────┘│
│                                                                      │
├─────────────────────────────────────────────────────────────────────┤
│ AWARD ELIGIBILITY:                                                  │
│ ┌──────────────────────────────────────────────────────────────────┐│
│ │ Centurion: ████████████████████ QUALIFIED ✅                    ││
│ │ Tribune:   ███████████████████  Tx3 (89/50) ✅                   ││
│ │ Senator:   ▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒░░ IN PROGRESS ⏳ (need Tx8)    ││
│ │ Triple Key: ███████░░░░░░░░░░░░ 105/300 (35%) ⏳                ││
│ │ WAS:        █████████░░░░░░░░░░ 47/50 states ⏳                 ││
│ │ WAC:        ███████░░░░░░░░░░░░ 5/6 continents ⏳               ││
│ └──────────────────────────────────────────────────────────────────┘│
│                                                                      │
│ NOTES:                                                              │
│ Contact reached Tribune Level 3 on 2024-08-20. Currently working   │
│ toward Tribune Level 8 for Senator qualification.                  │
│                                                                      │
│                              [Close]                                │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Implementation Details

### Data Requirements

#### Contact History Query
```python
def get_skcc_contact_history(skcc_number: str) -> List[Dict]:
    """
    Returns all SKCC contacts for a member with details

    Returns:
    [
        {
            'contact_id': 123,
            'callsign': 'W5XYZ',
            'qso_date': '20241021',
            'time_on': '1430',
            'band': '40M',
            'mode': 'CW',
            'key_type': 'STRAIGHT',
            'skcc_number': '12345C',          # Their number AT contact time
            'skcc_current': '12345Tx2',       # Their current number
            'notes': 'Good signal'
        },
        ...
    ]
    """
```

#### Award Eligibility Query
```python
def calculate_award_eligibility(skcc_number: str) -> Dict:
    """
    Calculate current award eligibility status

    Returns:
    {
        'centurion': {
            'qualified': True,
            'date_qualified': '2023-01-15',
            'total_contacts': 127,
            'requirement': 100
        },
        'tribune': {
            'qualified': True,
            'current_level': 3,  # Tx3
            'qualified_contacts': 89,
            'requirement_current_level': 50
        },
        'senator': {
            'qualified': False,
            'status': 'need_tribune_tx8',
            'current_tribune_level': 3
        },
        'triple_key': {
            'straight_key': 42,
            'bug': 35,
            'sideswiper': 28,
            'total': 105,
            'requirement': 300,
            'all_types_used': True
        },
        'geographic': {
            'was': {'count': 47, 'requirement': 50},
            'wac': {'count': 5, 'requirement': 6},
            'canadian_maple': {'count': 8, 'requirement': 10}
        }
    }
    """
```

---

### Database Queries Needed

```python
# 1. Get all contacts for SKCC member
def get_skcc_member_contacts(skcc_number: str) -> List[Contact]:
    """All CW contacts with this SKCC member number"""

# 2. Count contacts by SKCC level at specific date
def count_contacts_by_level_at_date(
    skcc_number: str,
    before_date: str,
    level: str
) -> int:
    """
    Count how many contacts were made with member when they had
    specific level (e.g., "C", "T", "Tx3", "S")
    """

# 3. Get all Centurion/Tribune/Senator contacts
def get_contacts_by_achievement_level(
    skcc_number: str,
    level: str  # "C", "T", "S"
) -> List[Contact]:
    """All contacts made with members of specific level"""

# 4. Analyze triple key progress
def analyze_triple_key_progress(skcc_number: str) -> Dict:
    """
    Count QSOs by key type to track Triple Key Award
    """

# 5. Analyze geographic progress
def analyze_geographic_awards(skcc_number: str) -> Dict:
    """
    Count unique states, continents, provinces for awards
    """
```

---

## Features in Detail

### Suffix History Tracking

**Why important:**
- Shows what level contact was at previous QSO
- Demonstrates historical achievement progression
- Useful for understanding when to pursue next award level

**How it works:**
1. Store SKCC number WITH suffix in each contact record
2. Display both historical and current suffix
3. Highlight when suffix has changed

**Example:**
```
Date: 2024-01-15  SKCC at Contact: 12345C    Current: 12345Tx2
  → Shows they were Centurion then, now Tribune Level 2
```

---

### Award Eligibility Logic

#### Centurion (C)
- **Status:** QUALIFIED if 100+ unique SKCC member CW contacts
- **Progress:** Show total count vs. 100

#### Tribune (T)
- **Prerequisite:** Must have Centurion level
- **Status:** Track Tribune level (Tx1-Tx8)
- **Each Level:**
  - Tx1: 50 C/T/S contacts (after Centurion)
  - Tx2: 100 C/T/S contacts
  - Tx3: 150 C/T/S contacts
  - ... up to Tx8: 400+ C/T/S contacts

#### Senator (S)
- **Prerequisite:** Tribune Tx8
- **Status:** After Tx8, need 200 more T/S level contacts
- **Total:** 600+ SKCC contacts minimum

#### Triple Key
- **Requirement:** 300 QSOs using all 3 key types
- **Track:** Separate counts for STRAIGHT, BUG, SIDESWIPER
- **Status:** Show if all 3 types have been used

#### Geographic Awards
- **WAS:** Count unique US states
- **WAC:** Count unique continents
- **Canadian Maple:** Count unique Canadian provinces/territories

---

## Color Coding & Visual Indicators

```
✅ QUALIFIED    - Green background, checkmark
⏳ IN PROGRESS  - Yellow background, hourglass
❌ NOT STARTED  - Gray background, dash
↑ NEW LEVEL     - Blue highlight when station achieved new suffix
```

---

## Filter & Sort Options

### Filters
- By Band (40M, 80M, etc.)
- By Mode (CW)
- By Key Type (STRAIGHT, BUG, SIDESWIPER)
- By Date Range (From/To)
- By Signal Report (599, 569, etc.)

### Sort Options
- By Date (newest/oldest)
- By Band (160M down to 70CM)
- By SKCC Level (C, T, S)
- By Key Type

---

## Integration with Contact Entry Form

**When operator enters callsign/SKCC during logging:**

1. Open/refresh this window automatically
2. Show previous contacts immediately
3. Check if this is a new contact or repeat
4. Alert if station has achieved new level since last contact
5. Show current award eligibility status
6. Guide operator on which award to pursue next

---

## User Workflow

### Typical Usage:

1. **Operator enters callsign:** "W5XYZ"
2. **Window opens automatically showing:**
   - All previous contacts with W5XYZ
   - Historical SKCC suffix at each contact
   - Current SKCC status (changed from C to Tx2 since last QSO?)
   - How many more contacts needed for next award level

3. **Operator sees:**
   - This is 5th contact with W5XYZ
   - They were C when first contacted, now Tx2
   - This contact will count toward Tribune requirement
   - Currently 89/50 Tribune contacts (78 more than needed)

4. **Operator decides:** Worth pursuing now, or should wait for more variety?

---

## Technical Implementation

### Frontend Components (PyQt/Web)

```python
class SKCCContactWindow(QDialog):
    """SKCC Contact History & Award Eligibility Window"""

    def __init__(self, parent, skcc_number):
        self.skcc_number = skcc_number
        self.contact_history = []
        self.award_eligibility = {}

    def load_contact_history(self):
        """Load all previous contacts with this SKCC member"""

    def calculate_eligibility(self):
        """Calculate current award status"""

    def display_contact_table(self):
        """Show table of previous contacts"""

    def display_award_status(self):
        """Show award eligibility and progress bars"""

    def on_callsign_search(self, text):
        """Search and auto-complete callsigns"""

    def on_skcc_search(self, text):
        """Search by SKCC number"""
```

### Backend Methods Needed

```python
# In DatabaseRepository class

def get_skcc_contact_history(self, skcc_number: str):
    """Get all contacts with SKCC member, sorted by date"""

def get_contact_count_for_award(self, skcc_number: str, level: str):
    """Count contacts with members of specific level"""

def analyze_skcc_award_progress(self, skcc_number: str):
    """Comprehensive award eligibility analysis"""

def get_triple_key_analysis(self, skcc_number: str):
    """Analyze Triple Key award progress"""

def get_geographic_analysis(self, skcc_number: str):
    """Analyze WAS, WAC, Canadian Maple progress"""
```

---

## Sample Data Display

### Example: Looking up W5XYZ (SKCC 12345)

**Contact History:**
```
Date       Time  Band Mode Key    SKCC@Contact  Current  Notes
2024-10-21 14:30 40M  CW   STR    12345C        Tx2      Gained Tribune!
2024-09-15 09:00 80M  CW   BUG    12345C        Tx2      Nice rag chew
2024-08-20 19:45 20M  CW   SIDE   12345C        Tx2      Met at Straight Key Month
2024-07-10 16:20 15M  CW   STR    12345C        Tx2
2024-06-05 12:15 40M  CW   BUG    12345C        Tx2
```

**Award Status:**
```
Centurion:  ████████████████████ 100/100 ✅ QUALIFIED (2023-01-15)
Tribune:    ██████████████████░░ Tx3 (89/150) ✅ IN PROGRESS
Senator:    ░░░░░░░░░░░░░░░░░░░░ Need Tx8 first ❌ NOT ELIGIBLE
Triple Key: █████░░░░░░░░░░░░░░ 105/300 (35%) ⏳ IN PROGRESS
WAS:        █████████░░░░░░░░░░ 47/50 states ⏳ IN PROGRESS
```

---

## Benefits

1. **Real-time decision making** - Know immediately if this contact helps current award pursuit
2. **Historical accuracy** - See what level contact had at time of QSO
3. **Award tracking** - Visual progress on all awards
4. **Prevents duplicates** - Know if already contacted this member
5. **Identifies new levels** - Alert when member achieved new suffix
6. **Strategic planning** - Know what award to pursue next
7. **CW proficiency tracking** - Shows key type usage for Triple Key

---

## Future Enhancements

- Export contact history as PDF
- Print award certificates
- Email reminders for award thresholds
- Integration with SKCC Logger database
- Automatic SKCC number lookup from callsign
- Award achievement notifications
- Historical achievement timeline chart
- Comparison with other operators' progress

---

## Related Documentation

- [SKCC Awards Guide](SKCC_AWARDS_GUIDE.md)
- [SKCC Quick Reference](SKCC_QUICK_REFERENCE.md)
- [Key Type Field](KEY_TYPE_FIELD.md)
- [ADIF Export Guide](ADIF_EXPORT_GUIDE.md)

---

*Last Updated: October 21, 2025*
*Design Version: 1.0*
