# SKCC Membership Integration - Implementation Plan

**Status:** TODO - Next Phase
**Priority:** HIGH
**Date Created:** October 21, 2025

---

## Overview

The W4GNS Logger needs to integrate SKCC membership data to properly track SKCC awards. Currently, the award tracking is database-centric but lacks real member validation and status information.

**Key Requirement:** Awards must revolve around SKCC membership - not just contact tracking.

---

## Current Gap

- ✅ SKCC number field exists in database
- ✅ SKCC award calculation logic exists in backend
- ❌ No way to input SKCC number in GUI
- ❌ No membership data synchronization
- ❌ No membership validation
- ❌ No update scheduling

---

## Membership Data Sources

### Primary Source (Confirmed)
**SKCC Membership Roster**
- URL: https://www.skccgroup.com/membership_data/membership_roster.php
- Format: Unknown (need to investigate)
- Access: Public or requires authentication (need to verify)
- Data fields: Need to determine what's available

### Action Items for Research
1. Visit URL and examine data format
2. Check if download/API available
3. Determine authentication requirements
4. Identify data structure (CSV, JSON, HTML table, etc.)
5. Check update frequency

### Alternative Sources to Research
- SKCC API (if exists)
- SKCC FTP server
- Direct file downloads
- Web scraping as fallback

---

## Implementation Requirements

### 1. SKCC Number Input Field in GUI

**Location:** src/ui/logging_form.py

**What to Add:**
```
SKCC Information Section:
├─ SKCC Number:    [_____________]  ← Text input (VARCHAR(20))
├─ Key Type:       [Dropdown ▼]      ← STRAIGHT/BUG/SIDESWIPER
└─ Member Status:  [Display only]    ← Shows fetched member info
```

**Fields:**
- `skcc_number`: Text input, optional
- `key_type`: Dropdown (STRAIGHT, BUG, SIDESWIPER)
- Member status display (read-only) showing:
  - Member name
  - Join date
  - Current suffix (C, T, S, etc.)
  - Last update time

---

### 2. Membership Data Management

**New Feature: Membership Synchronization**

**Location:** New module `src/database/skcc_membership.py`

**Key Principle:** Cache downloaded data until next update
- Downloaded data stored in `skcc_members` table
- Data persists across application restarts
- Only refetch when update is triggered (daily or manual)
- Lookups use cached data (fast, no network calls)

**Responsibilities:**
- Download/fetch SKCC membership roster
- Parse membership data
- Store in database (new table: `skcc_members`)
- Handle updates and scheduling
- Provide fast lookup methods from cache

**Database Table Structure:**
```sql
CREATE TABLE skcc_members (
    id INTEGER PRIMARY KEY,
    skcc_number VARCHAR(20) UNIQUE NOT NULL,
    call_sign VARCHAR(12),
    member_name VARCHAR(100),
    join_date VARCHAR(8),
    current_suffix VARCHAR(3),
    current_score INTEGER,
    last_updated DATETIME,
    created_at DATETIME,
    INDEX idx_skcc_number (skcc_number),
    INDEX idx_call_sign (call_sign),
    INDEX idx_last_updated (last_updated)
);
```

---

### 3. Update Scheduling

**Feature: Auto-update membership data**

**Update Methods:**
1. **On-Demand:** Button in settings to "Update SKCC Members Now"
2. **Daily Schedule:** Option to auto-update at specific time
3. **Manual Interval:** User can set update frequency

**Configuration:**
```yaml
skcc:
  auto_update: true
  update_frequency: 'daily'  # daily, weekly, manual
  update_time: '03:00'       # 3 AM daily
  last_sync: '2025-10-21T03:00:00Z'
  sync_interval_hours: 24
```

**Implementation Location:**
- Settings UI: `src/ui/settings_editor.py`
- Background task: `src/database/skcc_membership.py`
- Scheduler: Background thread or QTimer

---

### 4. GUI Integration Points

**Settings Tab Enhancement:**
```
SKCC Settings:
├─ ☑ Enable SKCC Membership Sync
├─ Update Frequency: [Daily ▼]
├─ Update Time: [03:00 ▼]
├─ [Update SKCC Members Now] button
└─ Last Updated: 2025-10-21 03:15:42
```

**Logging Form Enhancement:**
```
SKCC Information:
├─ SKCC Number: [_____________]
│  ↓ (on blur or button click)
│  Member: W5XYZ - John Smith
│  Status: Tribune (T) - 125/150 points
│  Join Date: 1999-03-15
│
├─ Key Type: [STRAIGHT ▼]
│  Options: STRAIGHT, BUG, SIDESWIPER
│
└─ [Refresh Member Info] button
```

---

### 5. Award Validation Logic

**Before:** Award based only on contact count
```python
if contact_count >= 100:
    award = "Centurion"  # ❌ No validation
```

**After:** Award must validate membership
```python
# 1. Check SKCC membership
member = db.get_skcc_member(skcc_number)
if not member:
    return None  # Not a member - no award

# 2. Check member suffix (C, T, S)
if not member.is_eligible_for_centurion():
    return None  # Already has higher award

# 3. Count qualifying contacts
qualifying_contacts = db.get_qualifying_contacts(
    skcc_number=skcc_number,
    required_count=100
)

if len(qualifying_contacts) >= 100:
    award = "Centurion"  # ✓ Validated
```

---

## TODO Tasks

### Phase 1: Research & Planning
- [ ] Investigate SKCC roster URL
  - [ ] Examine data format
  - [ ] Test download/access
  - [ ] Check authentication
  - [ ] Document data structure
- [ ] Research alternative SKCC data sources
  - [ ] Search for SKCC API
  - [ ] Check for FTP server
  - [ ] Look for direct downloads
- [ ] Document findings

### Phase 2: Backend Implementation
- [ ] Create `src/database/skcc_membership.py` module
  - [ ] Implement data fetching (based on source)
  - [ ] Implement data parsing
  - [ ] Implement database storage
  - [ ] Implement update scheduling
- [ ] Create `skcc_members` database table
- [ ] Add membership lookup methods to DatabaseRepository
- [ ] Update award validation logic to check membership
- [ ] Add error handling for network/data issues

### Phase 3: GUI Implementation
- [ ] Add SKCC Number field to LoggingForm
- [ ] Add Key Type dropdown to LoggingForm
- [ ] Add member info display (read-only)
- [ ] Add "Refresh Member Info" button
- [ ] Add SKCC settings to Settings tab
- [ ] Add "Update SKCC Members Now" button
- [ ] Add update schedule configuration

### Phase 4: Background Tasks
- [ ] Implement background update scheduler
- [ ] Handle daily auto-updates
- [ ] Log update events
- [ ] Display last update time in UI
- [ ] Handle update errors gracefully

### Phase 5: Testing
- [ ] Unit tests for membership fetching
- [ ] Unit tests for data parsing
- [ ] Unit tests for award validation
- [ ] Integration tests with GUI
- [ ] Test update scheduling
- [ ] Test error scenarios

---

## Data Sources to Investigate

### URL 1: SKCC Membership Roster (Primary)
**https://www.skccgroup.com/membership_data/membership_roster.php**
- Status: Confirmed available
- Need to: Test access, determine format, check fields

### Research Tasks
```
For each potential source:
1. Access the URL/resource
2. Document:
   - Data format (CSV, JSON, HTML, etc.)
   - Available fields (SKCC#, Callsign, Name, etc.)
   - Authentication required (Y/N)
   - Update frequency
   - Completeness (all members or subset)
3. Estimate parsing difficulty
4. Identify backup sources
```

---

## Implementation Strategy

### Option A: Simple CSV Download
If roster is downloadable as CSV:
1. Download CSV file
2. Parse with pandas or csv module
3. Insert into database
4. Update member_info display in form

### Option B: Web Scraping
If only HTML available:
1. Scrape HTML table from URL
2. Parse with BeautifulSoup
3. Extract member data
4. Insert into database

### Option C: API Integration
If SKCC has API:
1. Authenticate with API
2. Query member data
3. Parse JSON response
4. Insert into database

### Option D: Hybrid
Use multiple sources for redundancy:
1. Primary: Official source
2. Fallback: Alternative source
3. Cache: Local database

---

## Configuration Example

```yaml
# ~/.w4gns_logger/config.yaml

skcc:
  # Membership data sync
  auto_update: true
  update_frequency: 'daily'     # daily, weekly, manual
  update_time: '03:00'           # Time in HH:MM format (UTC)
  update_timezone: 'US/Central'  # User's timezone

  # Data source
  data_source: 'official'        # official, cached, api

  # Settings
  validate_membership: true      # Require member check for awards
  include_inactive: false        # Include inactive members

  # Update history
  last_sync_date: '2025-10-21'
  last_sync_time: '03:15:42'
  sync_status: 'success'         # success, pending, failed
  error_message: null
```

---

## Critical Design Principle: Data Caching

**IMPORTANT:** Downloaded membership data MUST be cached locally and retained until next update.

### Why Caching is Essential

1. **Performance:** SKCC roster lookup is instant (database query, no network)
2. **Reliability:** Works offline - if network down, still uses cached data
3. **Responsiveness:** UI doesn't freeze waiting for network calls
4. **Efficiency:** Don't refetch same data multiple times per day
5. **User Experience:** Membership info displays instantly when entering SKCC#

### Cache Implementation

```python
# Lookup flow:
1. User enters SKCC number in form
2. Query skcc_members table (LOCAL DATABASE)  <- Fast, instant
3. Display cached member info
4. (No network call needed)

# Update flow:
1. Daily trigger at 03:00 (or manual click)
2. Download fresh roster from SKCC website
3. Parse and update skcc_members table
4. All subsequent lookups use new data
```

### Cache Lifecycle

```
Database: skcc_members table
├─ Created: First download
├─ Used: Every SKCC# lookup (instant)
├─ Updated: Daily (or manual update)
├─ Persisted: Across restarts (until next update)
└─ Timestamp: last_updated field tracks when
```

### Storage Details

```sql
-- Each member record stored with:
- skcc_number (unique key)
- call_sign, name, join_date
- current_suffix (C, T, S status)
- current_score (points toward next level)
- last_updated (when this record was cached)

-- Timestamps allow knowing data age
-- When update runs, all records refresh
```

---

## Key Considerations

### 1. Data Privacy
- Don't store sensitive member info
- Only store: Number, Call, Name, Suffix, Score
- Respect SKCC's terms of service

### 2. Performance
- Cache membership data locally
- Update once per day (not per contact)
- Quick lookups during contact entry

### 3. Reliability
- Handle network failures gracefully
- Fallback to cached data if update fails
- Log all update attempts
- Display update status to user

### 4. User Experience
- Auto-populate member name when SKCC# entered
- Show member status inline
- One-click membership refresh
- Clear error messages

### 5. Award Validation
- Only award if member found in database
- Check member's current suffix
- Prevent double-awarding
- Validate against official SKCC records

---

## Success Criteria

- ✓ SKCC members data successfully imported
- ✓ Members can input SKCC number in logging form
- ✓ Member info displays when SKCC# entered
- ✓ Awards validated against membership
- ✓ Daily auto-update works
- ✓ Manual update available
- ✓ On-demand lookup works
- ✓ Error handling graceful
- ✓ Update status visible in UI
- ✓ All tests pass

---

## Timeline Estimate

- Research: 1-2 hours
- Backend implementation: 4-6 hours
- GUI implementation: 2-3 hours
- Testing: 2-3 hours
- **Total: 9-14 hours**

---

## Resources Needed

### Code Examples (for reference)
- CSV parsing with pandas
- Web scraping with BeautifulSoup
- Background scheduling with QTimer
- API integration patterns

### Documentation
- SKCC membership data format
- Terms of service for data use
- Update frequency recommendations

### Tools
- Network debugger (curl, Postman)
- Data inspector (for examining format)
- Web scraper (BeautifulSoup)

---

## Notes for Next Session

**Current Status:**
- SKCC number and key_type fields exist in database
- No GUI fields to input them
- No membership data source integrated
- No update scheduling

**Next Steps:**
1. Start with research on data source
2. Test SKCC roster URL
3. Document findings
4. Create implementation plan details

**Starting Point:**
```bash
# To begin investigation:
curl -v https://www.skccgroup.com/membership_data/membership_roster.php
# Or visit in browser and examine page source
```

---

**END TODO**

This is a high-priority feature that validates the entire award system. Without membership data integration, awards cannot be properly verified against official SKCC records.

Next session should begin with investigating the membership data source.
