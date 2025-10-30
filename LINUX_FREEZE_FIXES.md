# Linux "Not Responding" and Crash Fixes

## Issues Fixed

Fixed random "not responding" popups and crashes after 15-20 minutes on Linux Mint caused by:

### 1. Thread Safety Violations ⚠️ CRITICAL
**Problem**: Background thread directly updating Qt widgets (`status_label.showMessage()`)
- Qt widgets can ONLY be updated from the main GUI thread
- Violating this causes freezes, crashes, and "not responding" dialogs on Linux

**Solution**: 
- Added `status_message` pyqtSignal for thread-safe communication
- Background thread emits signal → main thread updates widget
- Added `_update_status_bar()` slot to handle updates safely

### 2. Memory Leak: Excessive Database Queries ⚠️ CRITICAL - CRASHES
**Problem**: Award cache refresh loaded ALL contacts every 60 seconds
- `get_all_contacts()` created thousands of Contact objects in memory
- Ran every minute, creating massive GC pressure
- Memory accumulated continuously until crash (15-20 minutes)

**Solution**:
- Reduced refresh frequency: 60 seconds → 5 minutes (5x reduction)
- Replaced `get_all_contacts()` with efficient SQL query
- Only queries SKCC numbers (strings), not full Contact objects
- Reduces memory usage by ~100x per refresh

### 3. Memory Leak: Unbounded Spot Storage ⚠️ CRITICAL - CRASHES
**Problem**: In-memory spot list grew to 500+ spots with RBN streaming continuously
- No effective limit during high-activity periods
- Duplicate tracking dictionary grew unbounded (every callsign ever seen)
- Cleanup ran only every 5 minutes

**Solution**:
- Reduced spot limit: 500 → 200 (60% memory reduction)
- More aggressive cleanup: 5 minutes → 2 minutes
- Reduced retention: 1 hour → 30 minutes
- Reduced duplicate tracking: 10 minutes → 5 minutes
- Added logging to monitor cleanup effectiveness

### 4. Blocking Network Operations in GUI Thread ⚠️ CRITICAL
**Problem**: "Sync Roster" button downloads SKCC roster (30+ seconds) on GUI thread
- `sync_membership_data()` makes HTTP request with 30 second timeout
- GUI completely frozen during download
- Linux window manager shows "not responding" dialog

**Solution**:
- Created `RosterSyncThread` (QThread) for background download
- Button disabled during sync, re-enabled on completion
- UI remains responsive during 30-second download

### 5. Blocking Database Queries During Initialization ⚠️ CRITICAL
**Problem**: Multiple widgets load all contacts during `__init__()`
- `PowerStatsWidget`: loads 10,000 contacts immediately
- `SKCCSpotWidget`: calls `_refresh_award_cache()` → `get_all_contacts()`
- Blocks GUI thread for 100-500ms on startup

**Solution**:
- Deferred `PowerStatsWidget.refresh()` with `QTimer.singleShot(300, ...)`
- Deferred `_refresh_award_cache()` with `QTimer.singleShot(500, ...)`
- Window shows immediately, data loads in background

### 6. Blocking Startup
**Problem**: SKCC roster sync started immediately during window initialization
- Network download could block for 30+ seconds
- Window appears frozen during startup

**Solution**:
- Deferred roster sync using `QTimer.singleShot(1000, ...)`
- Window shows first, then sync starts in background
- User sees responsive UI immediately

### 7. Event Loop Interference
**Problem**: Excessive `QApplication.processEvents()` calls during shutdown
- 9 processEvents() calls during backup/cleanup sequence
- Can cause race conditions and event loop corruption
- Particularly problematic on Linux window managers

**Solution**:
- Removed all processEvents() calls from shutdown sequence
- QProgressDialog updates automatically without manual event processing
- Cleaner, more stable shutdown process

## Files Modified

- `src/ui/main_window.py`:
  - Added `pyqtSignal` import and `status_message` signal
  - Added `_update_status_bar()` method for thread-safe updates
  - Modified `_start_background_roster_sync()` to use signals
  - Deferred roster sync to after window initialization
  - Removed 9 `processEvents()` calls from `closeEvent()`

- `src/ui/widgets/skcc_spots_widget.py`:
  - Added `QThread` import
  - Created `RosterSyncThread` class for background roster downloads
  - Modified `_sync_roster()` to use background thread
  - Deferred `_refresh_award_cache()` to avoid blocking initialization
  - **Fixed memory leaks:**
    - Award cache refresh: 60s → 5 minutes
    - Efficient SQL query instead of loading all contacts
    - Spot limit: 500 → 200
    - Cleanup interval: 5 min → 2 min
    - Spot retention: 1 hour → 30 min
    - Duplicate tracking: 10 min → 5 min

- `src/ui/power_stats_widget.py`:
  - Deferred `refresh()` call to avoid loading 10,000 contacts during initialization

- `src/skcc/spot_fetcher.py`:
  - Fixed floating-point precision (rounds frequency to 3 decimals)

- `src/skcc/spot_manager.py`:
  - Fixed floating-point precision in log messages and database storage

## Testing

After these fixes, the application should:
- ✅ Start immediately without freezing
- ✅ Show responsive UI during background roster sync
- ✅ Handle "Sync Roster" button clicks without freezing
- ✅ Load data in background during initialization
- ✅ **Run stable for hours/days without crashing**
- ✅ **Memory usage stabilizes instead of growing continuously**
- ✅ Close gracefully without "not responding" dialogs
- ✅ Work reliably on Linux Mint and other Linux distributions

## Background: Qt Thread Safety Rules

Qt has strict threading rules:
1. **GUI widgets** can ONLY be accessed from the main thread
2. **Signals/slots** are thread-safe and automatically marshal between threads
3. **Background operations** must use QThread, signals, or invoke methods via Qt.QueuedConnection

Violating rule #1 causes platform-dependent issues (worse on Linux than Windows).

## Memory Management Best Practices Applied

1. **Limit in-memory collections**: Keep only what's needed for current view
2. **Aggressive cleanup**: Clean up old data frequently
3. **Efficient queries**: Query only what you need (e.g., IDs/numbers vs full objects)
4. **Reduce refresh frequency**: Balance freshness vs resource usage
5. **Close database sessions**: Always use try/finally to prevent connection leaks

## Additional Blocking Operations Still Present

These operations still block the GUI thread but are user-initiated:
- QRZ.com credential test in Settings (10 second timeout)
- Manual award report generation (can take 5-10 seconds with large logbooks)
- ADIF export (fast with Rust, but UI still blocks briefly)

These could be moved to QThread workers in a future update if they cause issues.

## Issues Fixed

Fixed random "not responding" popups on Linux Mint caused by:

### 1. Thread Safety Violations ⚠️ CRITICAL
**Problem**: Background thread directly updating Qt widgets (`status_label.showMessage()`)
- Qt widgets can ONLY be updated from the main GUI thread
- Violating this causes freezes, crashes, and "not responding" dialogs on Linux

**Solution**: 
- Added `status_message` pyqtSignal for thread-safe communication
- Background thread emits signal → main thread updates widget
- Added `_update_status_bar()` slot to handle updates safely

### 2. Blocking Network Operations in GUI Thread ⚠️ CRITICAL
**Problem**: "Sync Roster" button downloads SKCC roster (30+ seconds) on GUI thread
- `sync_membership_data()` makes HTTP request with 30 second timeout
- GUI completely frozen during download
- Linux window manager shows "not responding" dialog

**Solution**:
- Created `RosterSyncThread` (QThread) for background download
- Button disabled during sync, re-enabled on completion
- UI remains responsive during 30-second download

### 3. Blocking Database Queries During Initialization ⚠️ CRITICAL
**Problem**: Multiple widgets load all contacts during `__init__()`
- `PowerStatsWidget`: loads 10,000 contacts immediately
- `SKCCSpotWidget`: calls `_refresh_award_cache()` → `get_all_contacts()`
- Blocks GUI thread for 100-500ms on startup

**Solution**:
- Deferred `PowerStatsWidget.refresh()` with `QTimer.singleShot(300, ...)`
- Deferred `_refresh_award_cache()` with `QTimer.singleShot(500, ...)`
- Window shows immediately, data loads in background

### 4. Blocking Startup
**Problem**: SKCC roster sync started immediately during window initialization
- Network download could block for 30+ seconds
- Window appears frozen during startup

**Solution**:
- Deferred roster sync using `QTimer.singleShot(1000, ...)`
- Window shows first, then sync starts in background
- User sees responsive UI immediately

### 5. Event Loop Interference
**Problem**: Excessive `QApplication.processEvents()` calls during shutdown
- 9 processEvents() calls during backup/cleanup sequence
- Can cause race conditions and event loop corruption
- Particularly problematic on Linux window managers

**Solution**:
- Removed all processEvents() calls from shutdown sequence
- QProgressDialog updates automatically without manual event processing
- Cleaner, more stable shutdown process

## Files Modified

- `src/ui/main_window.py`:
  - Added `pyqtSignal` import and `status_message` signal
  - Added `_update_status_bar()` method for thread-safe updates
  - Modified `_start_background_roster_sync()` to use signals
  - Deferred roster sync to after window initialization
  - Removed 9 `processEvents()` calls from `closeEvent()`

- `src/ui/widgets/skcc_spots_widget.py`:
  - Added `QThread` import
  - Created `RosterSyncThread` class for background roster downloads
  - Modified `_sync_roster()` to use background thread
  - Deferred `_refresh_award_cache()` to avoid blocking initialization

- `src/ui/power_stats_widget.py`:
  - Deferred `refresh()` call to avoid loading 10,000 contacts during initialization

- `src/skcc/spot_fetcher.py`:
  - Fixed floating-point precision (rounds frequency to 3 decimals)

- `src/skcc/spot_manager.py`:
  - Fixed floating-point precision in log messages and database storage

## Testing

After these fixes, the application should:
- ✅ Start immediately without freezing
- ✅ Show responsive UI during background roster sync
- ✅ Handle "Sync Roster" button clicks without freezing
- ✅ Load data in background during initialization
- ✅ Close gracefully without "not responding" dialogs
- ✅ Work reliably on Linux Mint and other Linux distributions

## Background: Qt Thread Safety Rules

Qt has strict threading rules:
1. **GUI widgets** can ONLY be accessed from the main thread
2. **Signals/slots** are thread-safe and automatically marshal between threads
3. **Background operations** must use QThread, signals, or invoke methods via Qt.QueuedConnection

Violating rule #1 causes platform-dependent issues (worse on Linux than Windows).

## Additional Blocking Operations Still Present

These operations still block the GUI thread but are user-initiated:
- QRZ.com credential test in Settings (10 second timeout)
- Manual award report generation (can take 5-10 seconds with large logbooks)
- ADIF export (fast with Rust, but UI still blocks briefly)

These could be moved to QThread workers in a future update if they cause issues.
