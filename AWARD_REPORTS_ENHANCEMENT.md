# Award Reports Enhancement - Complete Implementation

## Overview

Enhanced the award report system to support **ALL SKCC awards** with rule-based filtering instead of being limited to Tribune, Centurion, and Senator.

## Key Changes

### 1. Award Report Generator (`src/adif/award_report_generator.py`)

#### New Methods

**`get_available_awards()`**
- Dynamically discovers all available awards in the system
- Returns list of award names: `['Centurion', 'Tribune', 'Senator', 'WAS', 'WAC', 'DXCC', 'CanadianMaple', 'RagChew', 'PFX', 'TripleKey', 'SKCCDx']`
- Caches award classes for efficient access

**`get_award_class(award_name: str)`**
- Retrieves the award class for a given award name
- Maps award names to their module implementations
- Handles missing awards gracefully

**`generate_report(award_name, format, include_summary, achievement_date)`**
- Universal report generation for ANY SKCC award
- Automatically uses the award's validation rules
- Filters contacts based on the specific award's requirements:
  - CW mode only
  - SKCC number required
  - Award-specific validation (dates, member types, etc.)
- Supports achievement date filtering for endorsement applications

### 2. Award Report Dialog (`src/ui/dialogs/award_report_dialog.py`)

#### UI Enhancements

**Award Selection**
- Changed from fixed radio buttons (Tribune/Centurion/Senator) to **dynamic dropdown**
- Automatically populated with all available awards
- Shows award description when selected:
  - Requirements summary
  - Date restrictions
  - Contact type requirements

**Dynamic Achievement Date Visibility**
- Automatically shows achievement date filter for endorsement-eligible awards:
  - Tribune
  - Senator
  - Centurion
- Hidden for awards that don't support endorsements

**Report Generation**
- Uses universal `generate_report()` method
- Respects each award's specific validation rules
- Shows progress during generation

## Supported Awards

| Award | Requirements | Notes |
|-------|--------------|-------|
| **Centurion** | 100+ unique SKCC members | No date restriction |
| **Tribune** | 50+ Tribune/Senator members | Valid from 2007-03-01, x2-x35 endorsements |
| **Senator** | 200+ Tribune/Senator (after Tribune x8) | Valid from 2013-08-01, x2-x8+ endorsements |
| **WAS** | All 50 US States | Valid from 2011-10-09 |
| **WAC** | All 6 continents | Valid from 2011-10-09 |
| **DXCC** | 100+ confirmed DXCC entities | Award-specific validation |
| **Canadian Maple** | All Canadian provinces/territories | Canadian locations only |
| **Rag Chew** | 300+ minutes of CW conversation | Valid from 2013-07-01 |
| **PFX** | Prefix collection tracking | Prefix-based contacts |
| **Triple Key** | SSB + CW + Digital modes | Multi-mode participation |
| **SKCC DX** | DX (outside USA) contacts | International contacts |

## How It Works

### Report Generation Flow

```
1. User selects award from dropdown
2. Dialog shows award-specific requirements
3. User selects report format (Text, CSV, TSV, HTML)
4. User optionally filters by achievement date
5. Click "Generate Report"
6. System:
   a. Gets all CW contacts with SKCC numbers
   b. Retrieves award's validation class
   c. Validates each contact using award rules
   d. Filters by achievement date (if applicable)
   e. Formats output in requested format
7. Preview generated report
8. Export to file or copy to clipboard
```

### Award Validation

Each award has its own `validate()` method that checks:
- Mode (CW only)
- SKCC number presence
- Date restrictions (award-specific)
- Member type (Tribune/Senator, etc.)
- Geographic location (for WAS, WAC, etc.)
- Other award-specific rules

## File Modifications

### Modified Files

1. **`src/adif/award_report_generator.py`**
   - Added `get_available_awards()` method
   - Added `get_award_class()` method
   - Added universal `generate_report()` method
   - Added award caching mechanism
   - Kept existing award-specific methods for backward compatibility

2. **`src/ui/dialogs/award_report_dialog.py`**
   - Replaced radio button award selection with QComboBox
   - Added dynamic award description display
   - Made achievement date group dynamic/conditional
   - Updated report generation to use universal method
   - Improved UI layout to accommodate all awards

## Usage Examples

### Generate Tribune Report
1. Open Awards tab → Click "Generate Award Report"
2. Select "Tribune" from dropdown
3. Shows: "Requirements: 50+ Tribune/Senator members (valid from 2007-03-01)"
4. Choose format (Text, CSV, HTML)
5. Optionally filter to contacts after achievement date
6. Click "Generate Report"
7. Export to file or copy to clipboard

### Generate WAS Report
1. Select "WAS" from dropdown
2. Shows: "Requirements: All 50 US States (valid from 2011-10-09)"
3. Choose format
4. Generate (no achievement date option shown)
5. Export

### Generate Multiple Award Reports
Users can now generate reports for any combination of awards without restarting the application or changing code.

## Benefits

✅ **No code changes needed for new awards** - Automatically discovers them

✅ **Consistent validation** - Each award's rules are enforced uniformly

✅ **Extensible design** - Adding a new award just requires creating the award class

✅ **Better UX** - Shows award requirements inline

✅ **Rule-based filtering** - Reports respect each award's specific requirements

✅ **Endorsement support** - Achievement date filtering for all eligible awards

## Technical Details

### Award Discovery

The system discovers awards by:
1. Importing all award modules (centurion, tribune, senator, was, wac, etc.)
2. Finding classes that end with "Award"
3. Extracting award name by removing "Award" suffix
4. Caching for efficient access

### Validation Process

For each contact, the system:
1. Converts Contact ORM object to dictionary
2. Calls `award_instance.validate(contact_dict)`
3. Adds contact to list if validation passes
4. All validation respects the award's specific rules

## Backward Compatibility

- Existing award-specific methods remain functional
- Old code using `generate_tribune_report()` continues to work
- New code should use `generate_report()` for flexibility

## Future Enhancements

Possible additions:
- Batch report generation (multiple awards at once)
- PDF export with styled output
- Email integration for direct manager submission
- Award progress tracking tied to reports
- Report archive/history
- Custom filtering by band, mode, date range

## Testing Recommendations

1. **Single Award Reports**: Test each award individually
2. **Format Variations**: Verify Text, CSV, TSV, HTML outputs
3. **Achievement Date Filtering**: Test endorsement applications
4. **Edge Cases**: Empty results, large contact lists (1000+)
5. **Error Handling**: Invalid dates, missing data

## Files Modified

- `src/adif/award_report_generator.py` - Core report generation logic
- `src/ui/dialogs/award_report_dialog.py` - UI for report generation

## Status

✅ **COMPLETE** - All awards now support automated report generation based on their specific rules
