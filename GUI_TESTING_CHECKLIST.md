# GUI Testing Checklist - QRP Power Tracking

**Testing Guide for W4GNS Logger GUI Components**

---

## Pre-Test Setup

### 1. Environment Preparation

```bash
cd /home/w4gns/Projects/W4GNS\ Logger
source venv/bin/activate
```

### 2. Start the Application

```bash
python3 -m src.main
```

**Expected Result:** Application window opens with 7 tabs visible

---

## Test 1: Contact Entry Form with Power Fields

### Objective
Verify TX/RX Power fields in contact logging form work correctly.

### Steps

**Step 1.1: Navigate to Logging Tab**
- [ ] Click "Logging" tab
- [ ] Contact entry form is displayed
- [ ] "Signal Reports & Power" section visible

**Step 1.2: Locate Power Fields**
- [ ] Find "TX Power:" field with spinbox
- [ ] Find "RX Power:" field with spinbox (NEW)
- [ ] Both show " W" suffix
- [ ] TX Power can be edited
- [ ] RX Power can be edited

**Step 1.3: Test TX Power Decimal Input**
- [ ] Click TX Power field
- [ ] Clear existing value
- [ ] Type: 5.0
- [ ] Press Tab
- [ ] Value shows as "5.0 W"
- [ ] Try: 0.5, 1.5, 12.3 (all should work)

**Step 1.4: Test RX Power Field**
- [ ] Click RX Power field
- [ ] Type: 4.5
- [ ] Press Tab
- [ ] Value shows as "4.5 W"
- [ ] Hover over RX Power label
- [ ] Tooltip shows: "Other station's transmit power (for 2-way QRP tracking)"

**Step 1.5: Complete Contact Entry**
- [ ] Fill in Callsign: W5TEST
- [ ] Set Band: 40M
- [ ] Set Mode: CW
- [ ] Set TX Power: 5.0
- [ ] Set RX Power: 4.5
- [ ] Click "Save Contact"
- [ ] Success message appears: "Contact with W5TEST saved successfully!"

**Step 1.6: Verify Form Clear**
- [ ] After save, form is cleared
- [ ] TX Power shows: 0.0 W
- [ ] RX Power shows: 0.0 W
- [ ] All other fields cleared

**Expected Results:**
- ✅ TX/RX Power fields accept decimal values
- ✅ Contact saves with power data
- ✅ Form clears properly after save

---

## Test 2: QRP Progress Widget

### Objective
Verify QRP Progress tab displays award progress correctly and auto-refreshes.

### Steps

**Step 2.1: Navigate to QRP Progress Tab**
- [ ] Click "QRP Progress" tab
- [ ] Four sections visible:
  - QRP x1 Award (Your Power ≤5W)
  - QRP x2 Award (Both Stations ≤5W)
  - QRP Miles Per Watt
  - Power Statistics

**Step 2.2: Check QRP x1 Section**
- [ ] Green progress bar visible
- [ ] Shows: "Points: X/300"
- [ ] Shows: "Bands: X"
- [ ] Shows: "Contacts: X"
- [ ] If qualified: Green text with ✓ QUALIFIED
- [ ] If not qualified: Black text

**Step 2.3: Check QRP x2 Section**
- [ ] Blue progress bar visible
- [ ] Shows: "Points: X/150"
- [ ] Shows: "Bands: X"
- [ ] Shows: "Contacts: X"
- [ ] Qualification status displayed

**Step 2.4: Check MPW Section**
- [ ] Header: "QRP Miles Per Watt (≥1000 MPW at ≤5W)"
- [ ] Shows: "Qualifications: X"
- [ ] If X > 0: List of qualifying contacts with MPW values
- [ ] Format: "callsign: 1500 MPW"
- [ ] If no qualifications: "No MPW qualifications yet..."

**Step 2.5: Check Statistics Section**
- [ ] Four columns visible:
  - QRP (≤5W): X contacts
  - Standard (5-100W): X contacts
  - QRO (>100W): X contacts
  - Average Power: X.X W

**Step 2.6: Test Auto-Refresh**
- [ ] Note the current timestamp
- [ ] Wait 5 seconds
- [ ] Numbers should update (if new contact was added)
- [ ] Or numbers remain same (if no new contacts)
- [ ] No errors in console

**Expected Results:**
- ✅ Widget displays all sections
- ✅ Auto-refresh timer works (5-second intervals)
- ✅ Data accurate based on contacts in database
- ✅ No performance issues

---

## Test 3: Power Statistics Dashboard

### Objective
Verify Power Statistics tab displays comprehensive power analysis.

### Steps

**Step 3.1: Navigate to Power Stats Tab**
- [ ] Click "Power Stats" tab
- [ ] Three sections visible:
  - Overall Statistics
  - Power Category Distribution
  - Power Statistics by Band

**Step 3.2: Check Overall Statistics**
- [ ] "Total Contacts:" X displayed in large font
- [ ] "Average Power:" X.X W displayed in large font
- [ ] "Power Range:" X.X - X.X W displayed
- [ ] Values match expected data

**Step 3.3: Check Distribution Table**
- [ ] 4 rows: QRPp, QRP, Standard, QRO
- [ ] Count column shows: Numbers with colors
  - Orange for QRPp
  - Green for QRP
  - Blue for Standard
  - Red for QRO
- [ ] Percentage column shows: X.X% with colors
- [ ] Percentages add up to ~100%

**Step 3.4: Check Band Table**
- [ ] Multiple rows (one per band with data)
- [ ] Columns: Band | Avg Power | Contacts | QRP Count
- [ ] Band names correct (10M, 20M, 40M, 80M, etc.)
- [ ] Average Power in watts (e.g., 12.3 W)
- [ ] Contact counts accurate
- [ ] QRP Count shows: X/Y format
- [ ] QRP counts highlighted in green

**Step 3.5: Test Auto-Refresh**
- [ ] Wait 10 seconds
- [ ] Numbers should update if new contact added
- [ ] Or remain same if no new contacts
- [ ] No errors in console

**Expected Results:**
- ✅ All sections display correctly
- ✅ Data accurate and calculated properly
- ✅ Auto-refresh works (10-second intervals)
- ✅ Colors consistent and meaningful
- ✅ No performance degradation

---

## Test 4: Multiple Contact Entry (Data Generation)

### Objective
Create multiple test contacts with various power levels to populate statistics.

### Steps

**Step 4.1: Add QRP Contacts**
- [ ] Logging tab → Add contact:
  - Callsign: W1QRP1, Band: 40M, TX: 3.0W
- [ ] Logging tab → Add contact:
  - Callsign: W2QRP2, Band: 80M, TX: 2.5W
- [ ] Logging tab → Add contact:
  - Callsign: W3QRP3, Band: 20M, TX: 5.0W

**Step 4.2: Add Standard Power Contacts**
- [ ] Logging tab → Add contact:
  - Callsign: W4STD1, Band: 10M, TX: 25.0W
- [ ] Logging tab → Add contact:
  - Callsign: W5STD2, Band: 15M, TX: 50.0W

**Step 4.3: Add High Power Contact**
- [ ] Logging tab → Add contact:
  - Callsign: W6QRO1, Band: 6M, TX: 150.0W

**Step 4.4: Verify in QRP Progress**
- [ ] Switch to QRP Progress tab
- [ ] Numbers should update:
  - QRP x1: Points calculated
  - Statistics show counts
- [ ] Wait 5 seconds, verify refresh occurs

**Step 4.5: Verify in Power Stats**
- [ ] Switch to Power Stats tab
- [ ] Distribution shows:
  - QRP: 3 contacts
  - Standard: 2 contacts
  - QRO: 1 contact
- [ ] Band table populated with 6 rows
- [ ] Average power calculated correctly

**Expected Results:**
- ✅ All 6 test contacts save successfully
- ✅ Statistics update in both tabs
- ✅ Data displayed correctly
- ✅ Calculations accurate

---

## Test 5: Award Eligibility Dialog (Future)

### Objective
Verify Award Eligibility dialog displays correctly.

**Note:** This test requires implementing the trigger point (SKCC entry in contact form)

### Steps (When Implemented)

**Step 5.1: Enter SKCC Number**
- [ ] Logging tab → Enter SKCC number: 12345C
- [ ] Dialog automatically opens (trigger to be implemented)
- [ ] Or manually trigger from Tools menu

**Step 5.2: Check Dialog Contents**
- [ ] Title shows: "Award Eligibility - SKCC 12345C"
- [ ] Member info section visible
- [ ] Award eligibility section visible
- [ ] Contact history table visible

**Step 5.3: Verify Member Info**
- [ ] Callsign displayed
- [ ] Total contact count shown
- [ ] Last contact date/time shown

**Step 5.4: Verify Award Status**
- [ ] All awards listed with status
- [ ] ✓ for qualified awards
- [ ] ○ for non-qualified awards
- [ ] Centurion progress shown
- [ ] Tribune/Tribune Levels shown
- [ ] Senator progress shown
- [ ] Triple Key progress shown
- [ ] Geographic awards shown

**Step 5.5: Verify Contact History**
- [ ] Last 10 contacts displayed in table
- [ ] Columns: Date | Time | Band | Mode | SKCC Suffix
- [ ] Data accurate and formatted correctly

**Step 5.6: Close Dialog**
- [ ] Click Close button
- [ ] Dialog closes cleanly
- [ ] No errors

---

## Test 6: Error Handling

### Objective
Verify error handling and edge cases work correctly.

### Steps

**Step 6.1: Invalid Power Values**
- [ ] Try entering negative value in TX Power
  - Expected: Spinbox minimum enforced (0)
- [ ] Try entering very large value (9999.9)
  - Expected: Value accepted (range is 0-10000)

**Step 6.2: Save Contact Without Power**
- [ ] Fill all required fields EXCEPT Power
- [ ] Leave TX Power at 0.0
- [ ] Click Save Contact
- [ ] Contact should save successfully
- [ ] Power field can be optional

**Step 6.3: Mixed Power Entry**
- [ ] Enter TX Power: 5.0
- [ ] Leave RX Power: 0.0
- [ ] Save contact
- [ ] RX Power should be NULL in database (not 0)
- [ ] QRP x2 should not count this as 2-way

**Expected Results:**
- ✅ Error handling works correctly
- ✅ Edge cases handled gracefully
- ✅ No crashes or unexpected behavior

---

## Test 7: Performance Testing

### Objective
Verify application performance with GUI updates.

### Steps

**Step 7.1: Monitor CPU/Memory**
- [ ] Open system monitor
- [ ] Watch CPU usage while in QRP Progress tab
- [ ] Should be minimal (mostly idle)
- [ ] Check memory usage (reasonable)

**Step 7.2: Monitor During Auto-Refresh**
- [ ] Stay in QRP Progress tab for 30 seconds
- [ ] Tab auto-refreshes every 5 seconds (6 times)
- [ ] Monitor for:
  - CPU spikes during refresh (should be brief)
  - Memory increases (should be minimal)
  - Smooth UI updates (no freezing)

**Step 7.3: Monitor Power Stats Refresh**
- [ ] Stay in Power Stats tab for 30 seconds
- [ ] Tab auto-refreshes every 10 seconds (3 times)
- [ ] Monitor for:
  - CPU spikes during refresh
  - Memory increases
  - Smooth UI updates

**Step 7.4: Tab Switching Performance**
- [ ] Rapidly switch between tabs (10 times)
- [ ] No lag or freezing
- [ ] No memory leaks
- [ ] Timers properly stop/start

**Expected Results:**
- ✅ CPU usage minimal when idle
- ✅ Refresh cycles use brief CPU bursts
- ✅ Memory usage stable
- ✅ No lag during tab switching
- ✅ UI remains responsive

---

## Test 8: Data Persistence

### Objective
Verify data saves and loads correctly from database.

### Steps

**Step 8.1: Add Test Contact**
- [ ] Add contact with: TX: 5.0W, RX: 4.5W
- [ ] Note the callsign

**Step 8.2: Close Application**
- [ ] Close W4GNS Logger
- [ ] Wait a few seconds

**Step 8.3: Reopen Application**
- [ ] Start W4GNS Logger again
- [ ] Navigate to QRP Progress tab
- [ ] Statistics should show the saved contact
- [ ] Numbers should be preserved

**Step 8.4: Verify in Database**
- [ ] (Optional) Query database directly
- [ ] Verify contact has:
  - tx_power: 5.0
  - rx_power: 4.5
- [ ] Data persisted correctly

**Expected Results:**
- ✅ Contact data saves to database
- ✅ Data loads on application restart
- ✅ Statistics reflect saved data
- ✅ No data loss or corruption

---

## Test 9: Styling & Appearance

### Objective
Verify UI styling is consistent and visually appealing.

### Steps

**Step 9.1: Check Color Schemes**
- [ ] QRP x1 progress bar: Green
- [ ] QRP x2 progress bar: Blue
- [ ] Power distribution colors:
  - Orange for QRPp
  - Green for QRP
  - Blue for Standard
  - Red for QRO
- [ ] Colors are vibrant and easy to distinguish

**Step 9.2: Check Text Styling**
- [ ] Section headers: Bold, visible
- [ ] Values: Large and readable
- [ ] Labels: Clear and descriptive
- [ ] Qualified status: Green and bold

**Step 9.3: Check Alignment**
- [ ] Fields aligned properly
- [ ] Tables aligned correctly
- [ ] No overlapping text or widgets
- [ ] Responsive to window resizing

**Step 9.4: Check Font Sizes**
- [ ] Headers: 9pt bold
- [ ] Values: 11-16pt (appropriate size)
- [ ] Labels: 9pt
- [ ] Table text: 9-10pt

**Expected Results:**
- ✅ Consistent color scheme
- ✅ Clear visual hierarchy
- ✅ Professional appearance
- ✅ Responsive layout

---

## Test 10: User Experience Flow

### Objective
Verify the complete user workflow is smooth and intuitive.

### Workflow

**Step 10.1: Start Fresh**
- [ ] Close application
- [ ] Open application
- [ ] Default landing tab: Logging

**Step 10.2: Enter QSO**
- [ ] Fill in contact details
- [ ] Enter TX Power: 5.0
- [ ] Enter RX Power: 4.5
- [ ] Click Save
- [ ] Success confirmation

**Step 10.3: Check Progress**
- [ ] Click QRP Progress tab
- [ ] See points updated
- [ ] Understand current status

**Step 10.4: Analyze Statistics**
- [ ] Click Power Stats tab
- [ ] See distribution and breakdown
- [ ] Understand power usage pattern

**Step 10.5: Return to Logging**
- [ ] Click Logging tab
- [ ] Form is cleared and ready
- [ ] Can immediately log another contact

**Expected Results:**
- ✅ Workflow is natural and intuitive
- ✅ All information accessible
- ✅ Easy to understand progress
- ✅ No confusion about where to find information

---

## Summary of Tests

| Test | Item | Status |
|------|------|--------|
| 1 | Contact Form Power Fields | ⬜ |
| 2 | QRP Progress Widget | ⬜ |
| 3 | Power Statistics Dashboard | ⬜ |
| 4 | Multiple Contacts | ⬜ |
| 5 | Award Eligibility Dialog | ⬜ |
| 6 | Error Handling | ⬜ |
| 7 | Performance | ⬜ |
| 8 | Data Persistence | ⬜ |
| 9 | Styling & Appearance | ⬜ |
| 10 | User Experience | ⬜ |

---

## Test Results Log

### Date: ____________
### Tester: ____________
### Application Version: ____________

#### Notes:
```




```

#### Issues Found:
```




```

#### Recommendations:
```




```

---

## Pass/Fail Criteria

### PASS: All tests pass with no critical issues

### FAIL: Any test fails or critical issues found

---

**Test Execution:** Please mark each test as PASS ✅ or FAIL ❌

Test 1: ⬜ → ____
Test 2: ⬜ → ____
Test 3: ⬜ → ____
Test 4: ⬜ → ____
Test 5: ⬜ → ____
Test 6: ⬜ → ____
Test 7: ⬜ → ____
Test 8: ⬜ → ____
Test 9: ⬜ → ____
Test 10: ⬜ → ____

**Overall Status:** ____________________

---

*End of Testing Checklist*
