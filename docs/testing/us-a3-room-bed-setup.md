# Testing: US-A3 Room and Bed Setup

## Test Files

- `alcura_ipd_ext/alcura_ipd_ext/doctype/hospital_room/test_hospital_room.py`
- `alcura_ipd_ext/alcura_ipd_ext/doctype/hospital_bed/test_hospital_bed.py`

## Test Framework

Frappe `IntegrationTestCase` with `frappe.db.rollback()` in `tearDown` for test isolation.

## Helper Functions

### Hospital Room Tests

- `_get_or_create_company(abbr, name)`: Ensures a Company record exists.
- `_get_or_create_hsut(name, inpatient_occupancy)`: Ensures a Healthcare Service Unit Type exists.
- `_get_or_create_ward(ward_code, company)`: Ensures a Hospital Ward exists.
- `_make_room(room_number, ward, **overrides)`: Factory to create a Hospital Room.

### Hospital Bed Tests

- Same company/HSUT/ward factories as above.
- `_get_or_create_room(room_number, ward)`: Ensures a Hospital Room exists.
- `_make_bed(bed_number, room, **overrides)`: Factory to create a Hospital Bed.
- `_setup_ward_with_hsu(ward_code)`: Creates a ward with a linked HSU group node for testing HSU auto-creation.

## Hospital Room Test Scenarios

### 1. test_create_room
**Scenario:** Create a valid Hospital Room with minimum required fields.
**Expected:** Document saves, has a name, is_active defaults to 1.

### 2. test_autoname_format
**Scenario:** Create a room in a specific ward.
**Expected:** Document name follows `{ward.name}-{ROOM_NUMBER}` pattern.

### 3. test_room_number_uppercased
**Scenario:** Create a room with lowercase room_number.
**Expected:** room_number is normalised to uppercase.

### 4. test_room_number_unique_per_ward
**Scenario:** Create two rooms with the same room_number in the same ward.
**Expected:** Second insert raises `frappe.ValidationError`.

### 5. test_room_number_same_number_different_ward
**Scenario:** Create rooms with the same room_number in different wards.
**Expected:** Both inserts succeed; names differ.

### 6. test_room_number_rejects_spaces
**Scenario:** Create a room with room_number containing spaces.
**Expected:** Raises `frappe.ValidationError`.

### 7. test_room_number_rejects_special_chars
**Scenario:** Create a room with room_number containing special characters.
**Expected:** Raises `frappe.ValidationError`.

### 8. test_room_number_allows_hyphens
**Scenario:** Create a room with hyphens in room_number.
**Expected:** Saves successfully.

### 9. test_hsut_must_have_inpatient_occupancy
**Scenario:** Link a non-inpatient HSUT to a room.
**Expected:** Raises `frappe.ValidationError`.

### 10. test_ward_must_be_active
**Scenario:** Add a room to an inactive ward.
**Expected:** Raises `frappe.ValidationError`.

### 11. test_company_fetched_from_ward
**Scenario:** Create a room; check company field.
**Expected:** Company matches the ward's company.

### 12. test_capacity_defaults_to_zero
**Scenario:** Create a room with no beds.
**Expected:** total_beds, occupied_beds, available_beds all 0.

### 13. test_available_beds_computed
**Scenario:** Set total_beds=4, occupied_beds=1, save.
**Expected:** available_beds = 3.

### 14. test_delete_blocked_when_beds_exist
**Scenario:** Create a room with a bed, attempt to delete the room.
**Expected:** Raises `frappe.LinkExistsError`.

### 15. test_disable_allowed
**Scenario:** Deactivate a room with no beds.
**Expected:** Saves with is_active=0.

### 16. test_hsu_group_auto_created
**Scenario:** Create a room in a ward that has an HSU group.
**Expected:** Room gets an auto-created HSU group node linked.

### 17. test_hsu_not_created_without_ward_hsu
**Scenario:** Create a room in a ward without HSU.
**Expected:** healthcare_service_unit stays blank.

### 18. test_ward_deletion_blocked_when_rooms_exist
**Scenario:** Delete a ward that has rooms.
**Expected:** Raises `frappe.LinkExistsError`.

## Hospital Bed Test Scenarios

### 1. test_create_bed
**Scenario:** Create a valid Hospital Bed.
**Expected:** Saves, is_active=1, occupancy_status=Vacant.

### 2. test_autoname_format
**Scenario:** Create a bed in a specific room.
**Expected:** Name follows `{room.name}-{BED_NUMBER}` pattern.

### 3. test_bed_number_uppercased
**Scenario:** Create a bed with lowercase bed_number.
**Expected:** bed_number normalised to uppercase.

### 4. test_bed_number_unique_per_room
**Scenario:** Duplicate bed_number in same room.
**Expected:** Raises `frappe.ValidationError`.

### 5. test_bed_number_same_in_different_rooms
**Scenario:** Same bed_number in different rooms.
**Expected:** Both succeed.

### 6. test_bed_number_rejects_spaces
**Scenario:** Bed number with spaces.
**Expected:** Raises `frappe.ValidationError`.

### 7. test_bed_number_rejects_special_chars
**Scenario:** Bed number with special characters.
**Expected:** Raises `frappe.ValidationError`.

### 8. test_bed_number_allows_hyphens
**Scenario:** Bed number with hyphens.
**Expected:** Saves.

### 9. test_room_must_be_active
**Scenario:** Add bed to inactive room.
**Expected:** Raises `frappe.ValidationError`.

### 10. test_ward_and_company_inherited
**Scenario:** Create a bed; check inherited fields.
**Expected:** hospital_ward, company, service_unit_type match room values.

### 11. test_occupancy_defaults_vacant
**Scenario:** New bed occupancy.
**Expected:** Vacant.

### 12. test_housekeeping_defaults_clean
**Scenario:** New bed housekeeping.
**Expected:** Clean.

### 13. test_cannot_disable_when_occupied
**Scenario:** Set bed to Occupied, try to disable.
**Expected:** Raises `frappe.ValidationError`.

### 14. test_cannot_delete_when_occupied
**Scenario:** Delete an Occupied bed.
**Expected:** Raises `frappe.ValidationError`.

### 15. test_disable_allowed_when_vacant
**Scenario:** Disable a Vacant bed.
**Expected:** Saves with is_active=0.

### 16. test_room_capacity_rollup_on_insert
**Scenario:** Create 2 beds in a room.
**Expected:** Room total_beds=2, available_beds=2.

### 17. test_room_capacity_rollup_on_delete
**Scenario:** Create a bed, then delete it.
**Expected:** Room total_beds goes from 1 to 0.

### 18. test_ward_capacity_rollup_on_insert
**Scenario:** Create 2 beds in a ward.
**Expected:** Ward total_beds=2, available_beds=2.

### 19. test_ward_capacity_rollup_on_delete
**Scenario:** Create a bed, then delete it.
**Expected:** Ward total_beds goes from 1 to 0.

### 20. test_hsu_leaf_auto_created
**Scenario:** Create a bed in a room that has an HSU group.
**Expected:** Bed gets an auto-created HSU leaf node with inpatient_occupancy=1.

### 21. test_hsu_not_created_without_room_hsu
**Scenario:** Create a bed in a room without HSU.
**Expected:** healthcare_service_unit stays blank.

### 22. test_occupancy_sync_bed_to_hsu
**Scenario:** Change bed occupancy to Occupied, save.
**Expected:** Linked HSU occupancy_status becomes Occupied.

### 23. test_gender_restriction_default
**Scenario:** New bed gender restriction.
**Expected:** No Restriction.

### 24. test_maintenance_hold_persists
**Scenario:** Set maintenance_hold=1, save, reload.
**Expected:** Value persists.

### 25. test_infection_block_persists
**Scenario:** Set infection_block=1, save, reload.
**Expected:** Value persists.

### 26. test_housekeeping_status_transitions
**Scenario:** Cycle housekeeping through Clean → Dirty → In Progress → Clean.
**Expected:** All transitions succeed.

## Coverage Summary

| Category | Room Tests | Bed Tests |
|----------|-----------|-----------|
| CRUD basics | 1 | 1 |
| Naming / autoname | 1 | 1 |
| Number format validation | 3 | 3 |
| Uniqueness | 2 | 2 |
| Parent active check | 1 | 1 |
| Field inheritance | 1 | 1 |
| Capacity / defaults | 2 | 2 |
| Deletion protection | 1 | 1 |
| Disable behaviour | 1 | 2 |
| HSU auto-creation | 2 | 2 |
| Occupancy sync | - | 1 |
| Operational fields | - | 4 |
| Cross-doctype (ward) | 1 | 2 |
| **Total** | **16** | **23** |

## Running Tests

```bash
cd /path/to/frappe-bench

# Hospital Room tests
bench --site <site> run-tests --app alcura_ipd_ext --doctype "Hospital Room"

# Hospital Bed tests
bench --site <site> run-tests --app alcura_ipd_ext --doctype "Hospital Bed"

# All app tests
bench --site <site> run-tests --app alcura_ipd_ext
```

Or with pytest:

```bash
cd /path/to/frappe-bench/apps/alcura_ipd_ext

# Room tests
pytest alcura_ipd_ext/alcura_ipd_ext/doctype/hospital_room/test_hospital_room.py -v

# Bed tests
pytest alcura_ipd_ext/alcura_ipd_ext/doctype/hospital_bed/test_hospital_bed.py -v
```
