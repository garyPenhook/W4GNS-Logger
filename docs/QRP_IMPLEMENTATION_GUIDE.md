# QRP Power Tracking Implementation Guide

**W4GNS Logger - QRP Power Features**

---

## Implementation Status: ✅ COMPLETE

All backend QRP power tracking functionality has been implemented and tested. Ready for GUI integration.

---

## What Was Implemented

### 1. Contact Model Methods (src/database/models.py)

Added 5 new methods to the Contact class for QRP power analysis:

#### `is_qrp_contact() -> bool`
```python
Returns True if tx_power ≤ 5W, False otherwise
Used for: QRP x1 award filtering
```

#### `is_qrp_two_way(other_station_power: float) -> bool`
```python
Returns True if both stations ≤ 5W
Used for: QRP x2 award filtering
```

#### `calculate_mpw(distance_miles: float) -> float`
```python
Returns: Miles Per Watt ratio (distance / power)
Example: 1500 miles ÷ 1W = 1500 MPW
```

#### `qualifies_for_mpw(distance_miles: float) -> bool`
```python
Returns True if: tx_power ≤ 5W AND MPW ≥ 1000
Used for: QRP Miles Per Watt award validation
```

#### `get_qrp_category() -> str`
```python
Returns power category:
- 'QRPp' (< 0.5W)   - Extreme QRP
- 'QRP' (0.5-5W)    - Standard QRP
- 'STANDARD' (5-100W) - Normal power
- 'QRO' (> 100W)    - High power
```

### 2. Repository Methods (src/database/repository.py)

Added 5 new methods to DatabaseRepository for QRP operations:

#### `get_qrp_contacts(skip_filter=False) -> List[Contact]`
Retrieves all contacts with tx_power ≤ 5W
- Useful for: Getting all QRP contacts, filtering for awards

#### `count_qrp_points_by_band() -> Dict[str, Any]`
Calculates QRP x1 points per band
- Returns: Band breakdown, total points, contact counts
- Enforces: One contact per band (SKCC rule)
- Point system:
  - 160M = 4 points
  - 80M, 10M = 3 points
  - 60M, 40M, 30m = 2 points
  - 20M, 17M, 15M, 12M = 1 point
  - 6M, 2M = 0.5 points

#### `analyze_qrp_award_progress() -> Dict[str, Any]`
Comprehensive QRP award analysis
- Returns: QRP x1 progress (need 300 points), QRP x2 progress (need 150 points)
- Includes: Contact counts, band breakdowns, qualification status
- QRP x2 uses rx_power field to determine if both stations ≤ 5W

#### `calculate_mpw_qualifications() -> List[Dict[str, Any]]`
Identifies all MPW-qualifying contacts
- Requires: distance field populated in contact record
- Filters: tx_power ≤ 5W AND MPW ≥ 1000
- Returns: List with callsign, date, distance, power, MPW calculation

#### `get_power_statistics() -> Dict[str, Any]`
Overall power statistics across database
- Returns: Counts by power category, average/min/max power
- Categories: QRPp, QRP, STANDARD, QRO
- Useful for: Dashboard statistics, power distribution analysis

---

## Data Model Additions

### Contact Table Updates

**Already Present (used by QRP features):**
- `tx_power` (Float) - Transmit power in watts
- `rx_power` (Float) - Receive power (used for 2-way QRP detection)
- `distance` (Float) - Distance to contacted station (in miles)
- `mode` (String) - Operating mode (filtered for CW-only)

**No new columns required** - QRP implementation uses existing fields!

---

## Usage Examples

### Example 1: Check if contact qualifies for QRP
```python
contact = repo.get_contact(contact_id=123)
if contact.is_qrp_contact():
    print(f"This is a QRP contact: {contact.tx_power}W")
```

### Example 2: Get QRP award progress
```python
progress = repo.analyze_qrp_award_progress()

print(f"QRP x1: {progress['qrp_x1']['points']}/300 points")
print(f"QRP x2: {progress['qrp_x2']['points']}/150 points")

if progress['qrp_x1']['qualified']:
    print("✅ QRP x1 Award Qualified!")
```

### Example 3: Find MPW qualifications
```python
mpw_contacts = repo.calculate_mpw_qualifications()

for contact in mpw_contacts:
    print(f"{contact['callsign']}: {contact['mpw']:.0f} MPW ✓")
```

### Example 4: Get power statistics
```python
stats = repo.get_power_statistics()

print(f"QRP Contacts: {stats['qrp_count']}")
print(f"Average Power: {stats['average_power']:.1f}W")
print(f"Power Range: {stats['min_power']}W - {stats['max_power']}W")
```

---

## Testing

### Test Coverage

All features have been tested with the test suite `test_qrp_implementation.py`:

**Test 1: Contact Model Methods** ✅
- ✓ is_qrp_contact() - QRP and non-QRP contacts
- ✓ is_qrp_two_way() - 2-way QRP detection
- ✓ calculate_mpw() - Miles per watt calculation
- ✓ qualifies_for_mpw() - 1000 MPW threshold
- ✓ get_qrp_category() - Power categorization (QRPp, QRP, STANDARD, QRO)

**Test 2: Repository Methods** ✅
- ✓ get_qrp_contacts() - QRP contact filtering
- ✓ count_qrp_points_by_band() - Point calculation with band limits
- ✓ analyze_qrp_award_progress() - QRP x1 and x2 award analysis
- ✓ get_power_statistics() - Power category breakdown

**Test 3: MPW Calculations** ✅
- ✓ 500 miles at 0.5W = 1000 MPW (qualifies)
- ✓ 1200 miles at 1W = 1200 MPW (qualifies)
- ✓ 2500 miles at 5W = 500 MPW (doesn't qualify)
- ✓ 100 miles at 0.1W = 1000 MPW (qualifies)

### Running Tests

```bash
cd /home/w4gns/Projects/W4GNS\ Logger
source venv/bin/activate
python3 test_qrp_implementation.py
```

Expected Output: ✅ ALL TESTS PASSED!

---

## GUI Integration Points

### 1. Contact Entry Form

**Fields to add/expose:**
- TX Power input: `contact.tx_power` (Float, text box accepting decimals)
- RX Power input: `contact.rx_power` (Float, optional for 2-way QRP)
- QRP Status indicator: Call `contact.is_qrp_contact()`
- Power Category: Call `contact.get_qrp_category()` for display

**Example UI:**
```
TX Power: [___5.0___] W
RX Power: [___4.5___] W (optional)

✓ QRP Contact (≤5W)
Category: QRP
```

### 2. Award Progress Dashboard

**Call repository methods:**
```python
# For award progress display
progress = repo.analyze_qrp_award_progress()

# Display QRP x1 progress bar
print(f"QRP x1: {progress['qrp_x1']['progress']}")
# Output: "QRP x1: 87/300"

# Display QRP x2 progress bar
print(f"QRP x2: {progress['qrp_x2']['progress']}")
# Output: "QRP x2: 45/150"

# Display band breakdown
for band, points in progress['band_breakdown']['x1'].items():
    print(f"{band}: {points} points")
```

### 3. Contact History View

**Add column for power:**
```
Date       Band Mode Power  Category Notes
2024-10-21 40M  CW   5W     QRP      Good signal
2024-10-20 80M  CW   3W     QRP      Rag chew
2024-10-19 20M  CW   25W    STD      New member
```

**Code to populate:**
```python
for contact in contacts:
    power_cat = contact.get_qrp_category()
    display_row(contact.qso_date, contact.band,
                contact.mode, contact.tx_power,
                power_cat, contact.notes)
```

### 4. MPW Award Tracker

**Display qualifying contacts:**
```python
mpw_quals = repo.calculate_mpw_qualifications()

for qual in mpw_quals:
    print(f"{qual['callsign']}: {qual['distance_miles']}mi ÷ {qual['tx_power']}W = {qual['mpw']:.0f} MPW ✓")
```

### 5. Statistics Panel

**Show power distribution:**
```python
stats = repo.get_power_statistics()

print(f"QRPp (<0.5W):      {stats['qrpp_count']} QSOs")
print(f"QRP (0.5-5W):      {stats['qrp_count']} QSOs")
print(f"STANDARD (5-100W): {stats['standard_count']} QSOs")
print(f"QRO (>100W):       {stats['qro_count']} QSOs")
print(f"\nAverage Power: {stats['average_power']:.1f}W")
```

---

## ADIF Integration

### Export Format

When exporting to ADIF, use the standard TX_PWR field:

```python
# From contact model
if contact.tx_power:
    f.write(f"<TX_PWR:{len(str(contact.tx_power))}>{contact.tx_power}\n")
```

**ADIF Output:**
```
<TX_PWR:1>5        # 5 watts
<TX_PWR:3>0.5      # 0.5 watts
<TX_PWR:4>12.5     # 12.5 watts
```

### Import Format

When importing ADIF, extract TX_PWR field:

```python
# From ADIF parsing
if 'TX_PWR' in adif_record:
    contact.tx_power = float(adif_record['TX_PWR'])
```

---

## Database Queries Reference

### Get all QRP contacts
```python
qrp_contacts = repo.get_qrp_contacts()
```

### Filter QRP by band
```python
qrp_80m = [c for c in repo.get_qrp_contacts() if c.band == '80M']
```

### Get contacts with power data
```python
contacts_with_power = repo.get_all_contacts()  # Filter in GUI or use:
with_power = [c for c in contacts_with_power if c.tx_power is not None]
```

### Find QRP contacts in date range
```python
qrp = repo.get_qrp_contacts()
date_filtered = [c for c in qrp if c.qso_date >= '20240101' and c.qso_date <= '20241031']
```

### Get 2-way QRP contacts
```python
two_way = [c for c in repo.get_qrp_contacts()
           if c.rx_power is not None and c.rx_power <= 5.0]
```

---

## Feature Completeness Checklist

- ✅ Contact model QRP validation methods
- ✅ Repository QRP filtering and analysis methods
- ✅ QRP x1 award progress calculation (300 points)
- ✅ QRP x2 award progress calculation (150 points, both ≤5W)
- ✅ Miles Per Watt (MPW) qualification tracking (≥1000 MPW)
- ✅ Power categorization (QRPp, QRP, STANDARD, QRO)
- ✅ Power statistics and distribution analysis
- ✅ Comprehensive test suite with 3 test classes
- ✅ ADIF TX_PWR field support documentation
- ✅ Usage examples and documentation

### Pending (GUI Implementation)

- 🔲 TX Power input field in contact entry form
- 🔲 RX Power input field for 2-way QRP
- 🔲 QRP status indicator in real-time
- 🔲 QRP award progress bars in dashboard
- 🔲 Power category column in contact list view
- 🔲 MPW qualification display window
- 🔲 Power statistics charts/graphs
- 🔲 2-way QRP confirmation workflow

---

## Summary

The QRP power tracking implementation provides a complete backend infrastructure for tracking SKCC QRP awards:

1. **Database Layer** - No schema changes needed (uses existing fields)
2. **Model Layer** - 5 new methods on Contact for power analysis
3. **Repository Layer** - 5 new methods for QRP queries and calculations
4. **Testing** - Comprehensive test suite validating all features
5. **Documentation** - Complete with usage examples and GUI integration points

All code is production-ready and tested. The next step is GUI integration to display these features to the user.

---

## Technical Notes

### Power Field Units
- All power values are in **watts**
- Decimals supported: 0.5W, 1.5W, etc.
- Typical range: 0.1W - 1500W
- SKCC QRP limit: ≤ 5W

### Distance Field Units
- All distance values are in **miles**
- Required for MPW calculations
- Can be populated from grid square calculation or GPS data

### Mode Filtering
- QRP awards are **CW-only**
- Methods automatically filter for mode="CW"
- Non-CW modes excluded from award calculations

### Award Point System (QRP x1)
- One contact per band maximum
- Points by band (lowest to highest):
  - 6m: 0.5pts | 2m: 0.5pts
  - 20m-12m: 1pt
  - 60m-30m: 2pts
  - 80m, 10m: 3pts
  - 160m: 4pts
- Requirement: 300 total points

---

*Last Updated: October 21, 2025*
*Implementation Status: Complete & Tested*
*Ready for GUI Integration*
