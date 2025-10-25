# QRP Power Tracking for SKCC Awards

**W4GNS Logger - QRP and Power-Based Awards**

---

## Overview

SKCC awards include several power-based categories that require tracking transmit power. This document covers QRP (low power) requirements, award definitions, and implementation for W4GNS Logger.

---

## Official SKCC QRP Definition

**SKCC Standard: QRP = 5 watts or less**

This is the official SKCC definition used for all QRP-related awards and activities. All SKCC-approved mechanical keys apply to QRP operations.

---

## SKCC QRP Awards

### 1. QRP x1 Award (1-Way QRP)

**Power Requirement:** Only your station operates at 5 watts or less
- Contacted station can be at any power level
- Your power must be 5W or less for the entire QSO

**Points Required:** 300 points total

**Point Distribution by Band:**
| Band | Points | Notes |
|------|--------|-------|
| 160m | 4 | Highest points - challenging band |
| 80m, 10m | 3 | |
| 60m, 40m, 30m | 2 | |
| 20m, 17m, 15m, 12m | 1 | |
| 6m, 2m | 0.5 | VHF |

**Contact Rules:**
- Can contact same station multiple times (once per band max)
- Each band counts separately
- Only contacts where YOUR power ≤ 5W count

**Documentation:** Date, time (UTC), band/frequency, both SKCC numbers, your power level

**Example:**
```
Contact 1: 40M, 5W → 3 points
Contact 2: 40M, 3W → Can't count (same band as Contact 1)
Contact 3: 80M, 5W → 3 points
Contact 4: 20M, 5W → 1 point
Total: 7 points (need 300)
```

---

### 2. QRP x2 Award (2-Way QRP)

**Power Requirement:** Both stations operate at 5 watts or less
- You: ≤ 5W
- Other station: ≤ 5W
- More difficult to achieve, hence lower point requirement

**Points Required:** 150 points total (50% of x1)

**Point Distribution:** Same as QRP x1 (160m = 4 pts, 80m = 3 pts, etc.)

**Contact Rules:**
- Both operators must confirm power levels
- Same band limit applies (once per band)
- Typically exchange power info in QSO

**Documentation Required:**
- Date, time (UTC)
- Band/frequency
- Both SKCC numbers
- **Your power level**
- **Other operator's power level** (verification of 2xQRP)

**Why It's Harder:** Requires finding other QRP operators specifically, making qualification more challenging

**Difference from QRP x1:**
```
QRP x1: You 5W + Them 100W = Counts (1 point on 20M)
QRP x2: You 5W + Them 100W = Doesn't count (need them ≤ 5W)
QRP x2: You 5W + Them 5W = Counts (1 point on 20M)
```

---

### 3. QRP Miles Per Watt (MPW) Award

**Qualification Formula:**
```
Miles Per Watt = Distance (miles) ÷ Power (watts)
Requirement: ≥ 1,000 MPW
```

**Power Requirement:** ≤ 5 watts for entire QSO
- Contact may not be initiated at high power then reduced
- Entire QSO must be conducted at ≤ 5W

**Examples:**
- 500 miles at 0.5 watts = 1,000 MPW ✅ QUALIFIES
- 2,500 miles at 5 watts = 500 MPW ❌ Doesn't qualify
- 5,000 miles at 5 watts = 1,000 MPW ✅ QUALIFIES
- 1,000 miles at 1 watt = 1,000 MPW ✅ QUALIFIES

**Key Types:** Only SKCC-approved mechanical keys
- Straight Key
- Semi-Automatic Key (Bug)
- Sideswiper (Cootie)

**Distance Calculation:**
- Uses N9SSA Distance and Miles Per Watt Calculator
- Based on latitude/longitude or grid squares
- Must provide location information

**Documentation Required:**
- Date and time (UTC)
- Callsign
- Band
- SKCC numbers (both stations)
- QSO location (grid square or lat/long)
- **Transmit power (must be ≤ 5W)**
- Distance (calculated)
- MPW calculation
- Antenna description
- Key type used

**Multiple Qualifications:**
- Can have multiple MPW awards
- Each qualifying contact = 1x MPW award
- Can work same station on multiple bands for separate awards
- Points system doesn't apply (binary: qualifies or doesn't)

---

## Power Categories for Other Awards

### QRO (High Power) - Optional Tracking

While not a primary SKCC award, worth tracking:
- **QRO:** 100 watts or less
- **High Power:** Over 100 watts

Not required for SKCC awards but useful for general statistics.

---

## Implementation Requirements

### Database Schema

**Add to Contact Model (src/database/models.py):**

```python
# Power tracking fields
tx_power = Column(Float)  # Transmit power in watts (ALREADY EXISTS)
rx_power = Column(Float)  # Receive power/signal strength (ALREADY EXISTS)
qrp_category = Column(String(10))  # QRP, QRPp, STANDARD, QRO
```

**Existing Fields:** `tx_power` and `rx_power` already in Contact model!
- `tx_power`: Your transmit power (watts)
- `rx_power`: Receive power or other station's power

### Validation Rules

**For SKCC QRP Awards:**
```python
def is_qrp_contact(self) -> bool:
    """Check if contact qualifies as QRP (5W or less)"""
    return self.tx_power is not None and self.tx_power <= 5.0

def is_qrp_two_way(self, other_station_power: float) -> bool:
    """Check if both stations are QRP (5W or less)"""
    return (self.tx_power is not None and self.tx_power <= 5.0 and
            other_station_power is not None and other_station_power <= 5.0)

def calculate_mpw(self, distance_miles: float) -> float:
    """Calculate Miles Per Watt ratio"""
    if self.tx_power is None or self.tx_power <= 0:
        return 0
    return distance_miles / self.tx_power

def qualifies_for_mpw(self, distance_miles: float) -> bool:
    """Check if QSO qualifies for MPW award (≥1000 MPW at ≤5W)"""
    return (self.tx_power is not None and self.tx_power <= 5.0 and
            self.calculate_mpw(distance_miles) >= 1000.0)
```

### Repository Methods

**Add to DatabaseRepository:**

```python
def get_qrp_contacts(self, skip_filter=False) -> List[Contact]:
    """Get all QRP contacts (≤5W)"""

def count_qrp_points_by_band(self) -> Dict[str, int]:
    """Count QRP points per band for x1 award"""

def analyze_qrp_award_progress(self) -> Dict[str, Any]:
    """Complete QRP x1 and x2 award analysis"""

def calculate_mpw_qualifications(self) -> List[Dict]:
    """Find all MPW-qualifying contacts"""

def get_power_statistics(self) -> Dict[str, Any]:
    """Overall power statistics"""
```

---

## ADIF Integration

**ADIF Standard Fields:**

```
<TX_PWR:1>5        # 5 watts
<RX_PWR:3>0.5      # 0.5 watts receive power
```

**Export Format:**
```
<CALL:5>W5XYZ
<QSO_DATE:8>20241021
<TIME_ON:4>1430
<BAND:3>40M
<MODE:2>CW
<TX_PWR:1>5        # Your power (5W)
<RX_PWR:3>0.5      # Optional: other station power
<SKCC:5>12345C
<MY_SKCC:6>14276T
<EOR>
```

---

## GUI Implementation

### Contact Entry Form

**Fields Needed:**
```
┌─────────────────────────────────────┐
│ QSO Entry Form                      │
├─────────────────────────────────────┤
│ Callsign: [W5XYZ_____________]      │
│ Band: [40M_]  Mode: [CW__]          │
│ ...                                 │
│ TX Power: [5_] W                    │ ← New/Visible field
│ RX Power: [___] W (optional)        │
│ QRP Contact: [✓] 5W or less         │ ← Auto-calculated
│ ...                                 │
│           [Save]  [Cancel]          │
└─────────────────────────────────────┘
```

**Features:**
- Text field for transmit power (supports decimals: 0.5, 1.5, etc.)
- Optional RX power field for 2xQRP tracking
- Auto-calculate QRP status as user types
- Visual indicator: "✓ QRP" or "⚠ Above 5W"
- Warn if power exceeds threshold but still allow logging (may be non-SKCC contact)

### Contact History Window

**Add Power Display:**

```
Date       Time Band Mode Key  Power  2xQRP  Notes
2024-10-21 14:30 40M  CW  STR  5W     —      Good
2024-10-15 09:00 80M  CW  BUG  3W     ✓ 3W   Both QRP
2024-09-20 19:45 20M  CW  SIDE 5W     —      Solo QRP
```

### Award Progress Window

**QRP Award Tracking:**
```
┌─────────────────────────────────────┐
│ QRP Award Progress                  │
├─────────────────────────────────────┤
│ QRP x1 Award (1-way QRP):           │
│ ████████░░░░░░░░░░░░ 87/300 pts    │
│ Breakdown by band:                  │
│   160m: 4/8 pts (1 contact @ 4pts)  │
│   80m:  6/9 pts (2 contacts)        │
│   40m:  18/6 pts (full!)            │
│   20m:  2/25 pts (1 contact)        │
│                                     │
│ QRP x2 Award (2-way QRP):           │
│ ███░░░░░░░░░░░░░░░░░ 18/150 pts    │
│ Contacts with other QRP ops: 6     │
│                                     │
│ QRP Miles Per Watt:                 │
│ • Contact 1: 500mi / 5W = 100 MPW   │
│ • Contact 2: 1200mi / 1W = 1200MPW ✓│
│   (1 MPW qualification achieved)    │
│                                     │
│ Total MPW Qualifications: 1        │
└─────────────────────────────────────┘
```

---

## Power Level Recommendations

### Typical Power Levels by Equipment

**Portable/Field:**
- 100-500mW (0.1-0.5W) - Minimalist/extreme QRP
- 1-5W - Typical field portable with battery
- 5W - Standard portable rig

**Handheld/Mobile:**
- 2.5-5W - Mobile operation
- 5-25W - High power mobile
- 25-50W - Very high power mobile

**Home Station:**
- 5-50W - QRP home station
- 50-100W - Low power home
- 100W+ - Standard home station

---

## SKCC QRP Operating Tips

### For Successful QRP Contacts:

1. **Use Lower Bands**
   - 160m and 80m earn more points
   - Better propagation at low power
   - Longer distances achievable

2. **Antenna Quality Important**
   - At QRP levels, antenna makes huge difference
   - Good antenna at 5W > poor antenna at 50W
   - Document antenna type in notes

3. **Operating Times**
   - Evening hours better for DX
   - Sunspot activity critical
   - 160m/80m most productive at night

4. **Key Selection**
   - Choose appropriate key for conditions
   - Sideswiper efficient for fast CW
   - Straight key easier for ragchews

5. **Signal Reports**
   - Expect lower signal reports at QRP
   - 339-349 typical for QRP on same band
   - 229-249 for longer distances

### For MPW Award (Most Challenging):

1. **Location Information Critical**
   - Accurate grid square or lat/long needed
   - Affects distance calculation
   - Use GPS or map for accuracy

2. **Long Distance DX**
   - Target DX stations for higher MPW
   - Lower power = higher MPW ratio
   - Combine with antenna efficiency

3. **Band Selection**
   - Lower bands more likely to achieve distance
   - Higher bands need more power for same distance
   - 160m/80m best for MPW hunting

---

## Database Queries for QRP Reports

### Query Examples

```python
# Get all QRP contacts
qrp_contacts = session.query(Contact).filter(
    Contact.tx_power <= 5.0
).all()

# Get QRP contacts by band
band_40m_qrp = session.query(Contact).filter(
    Contact.band == '40M',
    Contact.tx_power <= 5.0
).all()

# Get potential 2xQRP contacts
two_way_qrp = session.query(Contact).filter(
    Contact.tx_power <= 5.0,
    Contact.rx_power <= 5.0  # Assuming rx_power = other station power
).all()

# Calculate total QRP points
qrp_points = calculate_qrp_points(qrp_contacts)

# Find MPW qualifications
mpw_quals = [c for c in qrp_contacts
             if calculate_mpw(c, distance) >= 1000]
```

---

## Validation & Error Handling

### Input Validation

```python
def validate_power(power: float) -> bool:
    """Validate power input"""
    return power is None or (power > 0 and power <= 1500)

def validate_qrp_power(power: float) -> bool:
    """Validate power for QRP tracking"""
    return power is not None and power <= 5.0
```

### User Warnings

- ⚠️ "This power level exceeds 5W - won't count toward QRP awards"
- ⚠️ "Two-way QRP requires other station ≤ 5W"
- ✓ "This is a valid QRP contact"
- ✓ "This qualifies for 2-way QRP (if other station confirms ≤ 5W)"

---

## Summary Table

| Award | Power Limit | Requirement | Challenge | Points |
|-------|-------------|-------------|-----------|--------|
| **QRP x1** | Your ≤ 5W | 300 pts | Medium | 0.5-4 pts/QSO |
| **QRP x2** | Both ≤ 5W | 150 pts | High | 0.5-4 pts/QSO |
| **MPW** | Your ≤ 5W | ≥1000 MPW | Very High | Binary (qualify/not) |

---

## References

- **SKCC Official:** https://www.skccgroup.com/
- **SKCC Handbook:** 2025 Edition
- **ADIF Standard:** TX_PWR field documentation
- **ARRL QRP:** https://www.arrl.org/qrp
- **N9SSA MPW Calculator:** For distance calculations

---

## Implementation Checklist

- [ ] Add power display field to contact entry form
- [ ] Add tx_power validation rules
- [ ] Create QRP award analysis methods
- [ ] Add MPW calculation functions
- [ ] Create QRP progress dashboard
- [ ] Add power statistics to main stats
- [ ] Document power fields in user guide
- [ ] Create QRP operating tips guide
- [ ] Test with mock QRP data
- [ ] Export power data in ADIF correctly

---

*Last Updated: October 21, 2025*
*SKCC Handbook Reference: 2025*
*ADIF Version: 3.1.5*
