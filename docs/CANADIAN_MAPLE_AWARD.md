# SKCC Canadian Maple Award

## Overview

The Canadian Maple Award recognizes SKCC operators who have made CW contacts with Canadian SKCC members from provinces and territories. Four levels of achievement are available, each with increasing requirements.

**Award Provider:** [SKCC Group](https://www.skccgroup.com/operating_awards/canadian_maple_award/)

## Award Levels

### 1. Yellow Maple
**Easiest Level - Entry Point**

- **Requirement:** 10 contacts from any 10 Canadian provinces/territories
- **Bands:** Mixed (any HF band)
- **Mode:** CW only
- **Description:** Make your first contacts across Canada!

**Provinces/Territories to Contact (pick any 10):**
- British Columbia (BC)
- Alberta (AB)
- Saskatchewan (SK)
- Manitoba (MB)
- Ontario (ON)
- Quebec (QC)
- New Brunswick (NB)
- Nova Scotia (NS)
- Prince Edward Island (PE)
- Newfoundland & Labrador (NL)
- Yukon (YT)
- Northwest Territories (NT)
- Nunavut (NU)
- VE0 (Stations at sea)
- VY9 (Government of Canada)

### 2. Orange Maple
**Band-Specific Achievement**

- **Requirement:** 10 contacts from same 10 provinces/territories on a single HF band
- **Note:** One award per band (10M, 12M, 15M, 17M, 20M, 30M, 40M, 60M, 80M, 160M)
- **Mode:** CW only
- **Description:** Choose your favorite band and work all regions on it!

### 3. Red Maple
**Challenging - All Provinces Across All Bands**

- **Requirement:** 90 total contacts
  - 10 contacts from each of the 10 Canadian provinces
  - Contacts must span 9+ different HF bands
- **Required Provinces:** BC, AB, SK, MB, ON, QC, NB, NS, PE, NL
- **Bands:** 160M, 80M, 60M, 40M, 30M, 20M, 17M, 15M, 12M, 10M
- **Mode:** CW only
- **Description:** Work all provinces thoroughly across multiple bands!

### 4. Gold Maple
**Prestigious - QRP Contacts Only**

- **Requirement:** 90 QRP contacts (≤5W power)
  - Contacts must span 9+ different HF bands
- **Power Limit:** 5 watts or less
- **Bands:** 160M, 80M, 60M, 40M, 30M, 20M, 17M, 15M, 12M, 10M
- **Mode:** CW only
- **Description:** Demonstrate QRP efficiency with low-power contacts across Canada!

## Basic Rules (ALL CRITICAL - MUST BE MET)

1. **CW Mode Only** - All contacts must be in Morse code (CW)
   - No SSB, FM, RTTY, or other modes allowed
   - Enforced in validation

2. **SKCC Members Only** - Contact must be with an SKCC member
   - Remote station must have valid SKCC number in contact record
   - Enforced in validation

3. **HF Bands Only** - 160, 80, 60, 40, 30, 20, 17, 15, 12, 10 meters
   - WARC bands allowed (60M, 30M)
   - Enforced in validation

4. **Valid Contact Date** - CRITICAL RULE
   - **Provinces:** September 1, 2009 (20090901) or later
   - **Territories:** January 2014 (20140101) or later
   - Enforced in validation
   - Contacts before these dates will be rejected automatically

5. **Province Identification** - CRITICAL RULE
   - Remote station's province/territory MUST be logged in state field
   - Valid codes: BC, AB, SK, MB, ON, QC, NB, NS, PE, NL, YT, NT, NU, VE0, VY9
   - Enforced in validation

6. **Mechanical Key Policy** - CRITICAL RULE
   - Contact must use mechanical key (STRAIGHT, BUG, or SIDESWIPER)
   - Electronic paddles (ELECTRONIC, IAMBIC) NOT allowed for Canadian Maple
   - Key type must be specified when logging contact
   - Enforced in validation
   - Invalid key types will be rejected automatically

## Implementation in W4GNS Logger

### Database Fields Used

- `country` - Must be "Canada"
- `state` - Canadian province/territory code (BC, AB, ON, QC, YT, etc.)
- `mode` - Must be "CW"
- `skcc_number` - Remote station's SKCC number
- `tx_power` - Transmit power (for Gold Maple calculation)
- `band` - Operating band (160M, 80M, etc.)

### How to Log a Canadian Contact (CRITICAL FIELDS)

**REQUIRED FIELDS (Must be correct for Canadian Maple to count):**

1. **Callsign:** The remote station's callsign
2. **Country:** **MUST BE** "Canada" (case-insensitive)
3. **State:** **MUST BE** valid Canadian province/territory code:
   - Provinces: BC, AB, SK, MB, ON, QC, NB, NS, PE, NL
   - Territories: YT, NT, NU, VE0, VY9
4. **SKCC Number:** The remote operator's SKCC number (required)
5. **Mode:** **MUST BE** "CW" (any other mode will be rejected)
6. **Band:** **MUST BE** HF band (160M, 80M, 60M, 40M, 30M, 20M, 17M, 15M, 12M, or 10M)
7. **Date (QSO Date):** **MUST BE:**
   - For provinces: September 1, 2009 (20090901) or later
   - For territories: January 2014 (20140101) or later
8. **Key Type:** **MUST BE** mechanical key (STRAIGHT, BUG, or SIDESWIPER)
   - Electronic paddles (ELECTRONIC, IAMBIC) will be REJECTED
   - Leave blank to accept any key type
9. **TX Power:** Your transmit power (important for Gold Maple award)

**VALIDATION WORKFLOW:**

When you save a contact, the application will:
- ✅ Automatically validate against ALL Canadian Maple rules
- ✅ Show error if any critical field is missing or invalid
- ✅ Reject contact if date is before valid range
- ✅ Reject contact if key type is invalid
- ✅ Update your progress toward all four levels
- ✅ Track province coverage
- ✅ Calculate band diversity
- ✅ Show which level(s) you've achieved

### Checking Your Progress

Use the Awards tab to view your Canadian Maple Award progress:
- Current level achieved
- Progress toward each level
- Provinces worked
- Bands worked (for Red and Gold Maple)
- Contacts needed to reach next level

### Repository Methods

**Get Canadian Maple Progress:**
```python
progress = repository.get_canadian_maple_progress()
# Returns: {
#   'yellow': {...},
#   'orange': {...},
#   'red': {...},
#   'gold': {...},
#   'current_level': 'Yellow Maple' | 'Orange Maple' | 'Red Maple' | 'Gold Maple' | 'Not Yet'
# }
```

**Get Canadian Contacts:**
```python
# All Canadian CW contacts
contacts = repository.get_canadian_contacts()

# Specific province
contacts = repository.get_canadian_contacts(province='ON')
```

**Get Provinces Worked:**
```python
provinces = repository.get_canadian_provinces_worked()
# Returns: {'BC': 5, 'AB': 3, 'ON': 12, ...}
```

## Award Class Implementation

The `CanadianMapleAward` class in `src/awards/canadian_maple.py` handles:

1. **Validation:** Checks each contact against Canadian Maple rules
2. **Progress Calculation:** Computes progress for all four levels
3. **Statistics:** Provides detailed breakdowns by province and band

### Key Methods

- `validate(contact)` - Check if contact qualifies
- `calculate_progress(contacts)` - Get progress for all levels
- `_calculate_yellow(contacts)` - Yellow Maple progress
- `_calculate_orange(contacts)` - Orange Maple progress
- `_calculate_red(contacts)` - Red Maple progress
- `_calculate_gold(contacts)` - Gold Maple progress

## Tips for Success

### Yellow Maple (Easy Start)
- Pick any 10 provinces/territories
- Use your favorite band
- Should take 10-20 QSOs

### Orange Maple (Band Focus)
- Choose a band you operate frequently (usually 20M or 40M)
- Work systematically to get all 10 regions on that band
- Multiple awards possible (one per band)

### Red Maple (Comprehensive)
- Requires dedication and band diversity
- Track which provinces you still need on each band
- Plan to work Canadian operators when they're active
- Takes time but very prestigious

### Gold Maple (QRP Challenge)
- Requires low-power capability
- Build a good antenna system for QRP efficiency
- Work Canadian operators during peak propagation
- Most prestigious Canadian Maple award

## Canadian SKCC Activity

Canadian SKCC operators are very active on:
- **40M band:** Often the most active for Canadian contacts
- **20M band:** Excellent for skip propagation
- **80M band:** Good for regional coverage
- **80M/160M Winter:** Propagation favorable during winter months

## Resources

- **Official Rules:** https://www.skccgroup.com/operating_awards/canadian_maple_award/
- **SKCC Group:** https://www.skccgroup.com/
- **Canadian SKCC Directory:** Contact list of Canadian SKCC members

## Technical Notes

### Province Code Mappings

| Province/Territory | Code | Country |
|---|---|---|
| British Columbia | BC | Canada |
| Alberta | AB | Canada |
| Saskatchewan | SK | Canada |
| Manitoba | MB | Canada |
| Ontario | ON | Canada |
| Quebec | QC | Canada |
| New Brunswick | NB | Canada |
| Nova Scotia | NS | Canada |
| Prince Edward Island | PE | Canada |
| Newfoundland & Labrador | NL | Canada |
| Yukon | YT | Canada |
| Northwest Territories | NT | Canada |
| Nunavut | NU | Canada |
| At Sea | VE0 | Canada |
| Government of Canada | VY9 | Canada |

### Band Handling

The application recognizes these HF bands:
- 160M (1.8 MHz)
- 80M (3.5 MHz)
- 60M (5 MHz - WARC band)
- 40M (7 MHz)
- 30M (10 MHz)
- 20M (14 MHz)
- 17M (18 MHz)
- 15M (21 MHz)
- 12M (24 MHz)
- 10M (28 MHz)

## Validation Rules & What Gets Rejected

### Why Your Contact Was Rejected

The application will automatically **REJECT** (not count) contacts that:

1. **Mode is not CW** → Contact logged in SSB, FM, RTTY, etc.
   - Fix: Change mode to "CW"

2. **Country is not "Canada"** → Wrong country code
   - Fix: Set country to exactly "Canada"

3. **State code is invalid** → Misspelled or incorrect province code
   - Fix: Use: BC, AB, SK, MB, ON, QC, NB, NS, PE, NL, YT, NT, NU, VE0, or VY9

4. **SKCC Number is missing** → No remote operator SKCC number logged
   - Fix: Add the remote operator's SKCC number

5. **Band is not HF** → Used VHF, UHF, or non-HF band
   - Fix: Log on: 160M, 80M, 60M, 40M, 30M, 20M, 17M, 15M, 12M, or 10M

6. **Date is TOO OLD** → Contact before valid date for that region
   - Fix: Check date is correct:
     - Provinces: Sept 1, 2009 (20090901) or later
     - Territories: Jan 2014 (20140101) or later

7. **Key Type is electronic** → Used electronic paddle, not mechanical key
   - Fix: Change key type to STRAIGHT, BUG, or SIDESWIPER
   - Invalid types (ELECTRONIC, IAMBIC) will be rejected

## FAQ

**Q: What if I logged a contact before Sept 1, 2009?**
A: Those contacts will NOT count toward Canadian Maple. Only contacts from Sept 1, 2009 (provinces) or Jan 2014 (territories) onward are valid.

**Q: Can I count a contact from before I have a SKCC number?**
A: You must be an SKCC member at time of contact AND log the remote operator's SKCC number. The remote station must also be an SKCC member.

**Q: Can I use SSB or other modes?**
A: No - Canadian Maple Award is CW-only per SKCC rules. SSB contacts will be rejected automatically.

**Q: Can I count the same station multiple times?**
A: Yes - you can work the same station multiple times (if from different provinces) and different times, and each counts toward the award.

**Q: How do I verify I have the right province?**
A: Check the SKCC member database or the operator's QRZ page to confirm their province of operation.

**Q: What if my antenna can't do 160M or other bands?**
A: You can achieve Yellow, Orange, and Gold Maple without all bands. Red Maple requires multiple bands but doesn't require all of them.

**Q: Can I use the same province on multiple bands for Red Maple?**
A: Yes! Red Maple requires 10 contacts from each province ACROSS 9 bands, so the same province can be on different bands.

---

**Implementation Status:** ✅ Complete
**Last Updated:** October 26, 2025
