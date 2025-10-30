# Repository Refactoring Plan

## Goal
Split the monolithic 2,274-line `repository.py` into focused, maintainable repository classes.

## New Structure

### 1. `base_repository.py` (~100 lines)
- Database connection management
- Session factory
- Schema migration
- Shared utilities

### 2. `contact_repository.py` (~500 lines)
**Methods to move:**
- add_contact()
- get_contact()
- get_contacts_by_callsign()
- get_all_contacts()
- search_contacts()
- update_contact()
- delete_contact()
- get_contact_count()
- get_contacts_by_skcc()
- search_skcc_by_band()
- get_contacts_by_key_type()
- search_contacts_by_key_type_and_band()
- get_skcc_contact_history()
- get_canadian_contacts()
- import_contacts_from_adif()
- _clean_adif_record()
- backfill_contact_distances()
- _contact_to_dict()

### 3. `award_repository.py` (~800 lines)
**Methods to move:**
- add_award_progress()
- get_award_progress()
- get_all_awards()
- update_award_progress()
- analyze_centurion_award_progress()
- analyze_tribune_award_progress()
- analyze_senator_award_progress()
- get_triple_key_progress()
- analyze_skcc_award_eligibility()
- analyze_qrp_award_progress()
- calculate_mpw_qualifications()
- get_canadian_maple_progress()
- count_contacts_by_achievement_level()
- count_qrp_points_by_band()

### 4. `member_repository.py` (~200 lines)
**Methods to move:**
- check_skcc_member_status()
- _load_member_sets()
- refresh_member_cache()
- get_skcc_member_summary()

### 5. `spot_repository.py` (~150 lines)
**Methods to move:**
- add_cluster_spot()
- get_recent_spots()
- get_spots_by_band()
- get_spots_by_callsign()
- delete_old_spots()

### 6. `statistics_repository.py` (~200 lines)
**Methods to move:**
- get_skcc_statistics()
- get_key_type_statistics()
- get_power_statistics()
- get_qrp_contacts()
- get_canadian_provinces_worked()
- get_statistics()

### 7. `repository.py` (FACADE - ~200 lines)
**Delegates all calls to sub-repositories for backward compatibility**

## Benefits
1. **Maintainability**: Each file has single responsibility
2. **Testability**: Easier to unit test focused classes
3. **Performance**: Can optimize each repository independently
4. **Collaboration**: Multiple developers can work on different repositories
5. **Backward Compatibility**: Existing code continues to work unchanged

## Implementation Order
1. ✅ Create base_repository.py
2. ✅ Create contact_repository.py
3. ✅ Create award_repository.py
4. ✅ Create member_repository.py
5. ✅ Update repository.py facade
6. ✅ Test compilation
7. ✅ Verify backward compatibility
