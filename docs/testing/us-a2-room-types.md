# Testing: US-A2 Room Types

## Test File

`alcura_ipd_ext/tests/test_room_type_custom_fields.py`

## Test Framework

Frappe `IntegrationTestCase` with `frappe.db.rollback()` in `tearDown` for test isolation. Custom fields are installed once in `setUpClass`.

## Helper Functions

- `_ensure_custom_fields()`: Idempotently installs custom fields before the test class runs.
- `_make_hsut(name, inpatient_occupancy, **overrides)`: Factory to create or update a Healthcare Service Unit Type record with sensible defaults.

## Test Scenarios

### 1. test_custom_fields_installed
**Scenario:** Check all custom fields defined in `get_custom_fields()` exist as Custom Field records.
**Expected:** Every field in the definition map has a corresponding Custom Field document.

### 2. test_icu_sets_critical_care_flag
**Scenario:** Create an inpatient HSUT with `ipd_room_category="ICU"`.
**Expected:** `is_critical_care_unit` is 1.

### 3. test_general_clears_critical_care_flag
**Scenario:** Create an inpatient HSUT with `ipd_room_category="General"`.
**Expected:** `is_critical_care_unit` is 0.

### 4. test_isolation_sets_supports_isolation
**Scenario:** Create an inpatient HSUT with `ipd_room_category="Isolation"`.
**Expected:** `supports_isolation` is 1.

### 5. test_critical_care_suggests_nursing_intensity
**Scenario:** Create an inpatient HSUT with `ipd_room_category="MICU"` and no nursing_intensity.
**Expected:** `nursing_intensity` is auto-set to "Critical".

### 6. test_non_inpatient_type_no_category_required
**Scenario:** Create a non-inpatient HSUT (allow_appointments=1) without `ipd_room_category`.
**Expected:** Saves successfully, no validation error.

### 7. test_inpatient_requires_room_category
**Scenario:** Create an inpatient HSUT without setting `ipd_room_category`.
**Expected:** Raises `frappe.ValidationError`.

### 8. test_default_price_list_can_be_set
**Scenario:** Create an inpatient HSUT with `default_price_list` pointing to "Standard Selling".
**Expected:** Field persists the linked Price List name.

### 9. test_package_eligible_toggle
**Scenario:** Create an inpatient HSUT with `package_eligible=1`.
**Expected:** Field value is 1 after save.

### 10. test_all_critical_care_categories
**Scenario:** Loop through all categories in `CRITICAL_CARE_CATEGORIES` (ICU, CICU, MICU, NICU, PICU, SICU, HDU, Burns).
**Expected:** Each sets `is_critical_care_unit=1`.

### 11. test_non_critical_categories
**Scenario:** Loop through non-critical categories (General, Twin Sharing, Semi-Private, Private, Deluxe, Suite, Other).
**Expected:** Each keeps `is_critical_care_unit=0`.

### 12. test_standard_item_creation_unaffected
**Scenario:** Create an inpatient HSUT with `is_billable=1` and custom fields.
**Expected:** Saves successfully; if an Item is auto-created, it exists.

### 13. test_occupancy_class_persists
**Scenario:** Create an inpatient HSUT with `occupancy_class="Double"`.
**Expected:** Value persists after save.

### 14. test_nursing_intensity_manual_override
**Scenario:** Create an HDU room type with explicit `nursing_intensity="High"`.
**Expected:** Auto-suggest does not override; value remains "High".

### 15. test_isolation_flag_not_cleared_for_others
**Scenario:** Create a Private room type with `supports_isolation=1`.
**Expected:** Flag stays 1 (not cleared by non-Isolation category).

## Coverage Summary

| Category | Tests |
|----------|-------|
| Field existence | 1 |
| Critical care auto-flag | 4 (individual + bulk) |
| Isolation flag | 2 |
| Nursing intensity | 2 |
| Category validation | 2 |
| Tariff fields | 2 |
| Standard behaviour | 1 |
| Occupancy class | 1 |
| **Total** | **15** |

## Running Tests

```bash
cd /path/to/frappe-bench
bench --site <site> run-tests --app alcura_ipd_ext --module alcura_ipd_ext.tests.test_room_type_custom_fields
```

Or with pytest:

```bash
cd /path/to/frappe-bench/apps/alcura_ipd_ext
pytest alcura_ipd_ext/tests/test_room_type_custom_fields.py -v
```
