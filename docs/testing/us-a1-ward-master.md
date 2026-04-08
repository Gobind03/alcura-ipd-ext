# Testing: US-A1 Ward Master

## Test File

`alcura_ipd_ext/alcura_ipd_ext/doctype/hospital_ward/test_hospital_ward.py`

## Test Framework

Frappe `IntegrationTestCase` with `frappe.db.rollback()` in `tearDown` for test isolation.

## Helper Functions

- `_get_or_create_company(abbr, name)`: Ensures a Company record exists for testing.
- `_get_or_create_second_company(abbr, name)`: Creates a second company for cross-company tests.
- `_make_ward(ward_code, company, **overrides)`: Factory function to create a Hospital Ward with sensible defaults.

## Test Scenarios

### 1. test_create_ward
**Scenario:** Create a valid Hospital Ward with minimum required fields.
**Expected:** Document saves, has a name, ward_name is set, is_active defaults to 1.

### 2. test_autoname_format
**Scenario:** Create a ward for a company with abbreviation "TST".
**Expected:** Document name is `TST-ICU01`.

### 3. test_ward_code_uppercased
**Scenario:** Create a ward with lowercase ward_code "gen02".
**Expected:** ward_code is normalised to "GEN02" after save.

### 4. test_ward_code_unique_per_company
**Scenario:** Create two wards with the same ward_code in the same company.
**Expected:** Second insert raises `frappe.ValidationError`.

### 5. test_ward_code_same_code_different_company
**Scenario:** Create wards with the same ward_code in two different companies.
**Expected:** Both inserts succeed; document names differ.

### 6. test_ward_code_format_validation_rejects_spaces
**Scenario:** Create a ward with ward_code "GW 01".
**Expected:** Raises `frappe.ValidationError`.

### 7. test_ward_code_format_validation_rejects_special_chars
**Scenario:** Create a ward with ward_code "GW@01".
**Expected:** Raises `frappe.ValidationError`.

### 8. test_ward_code_allows_hyphens
**Scenario:** Create a ward with ward_code "ICU-A1".
**Expected:** Saves successfully.

### 9. test_auto_critical_care_flag_icu
**Scenario:** Create a ward with ward_classification "ICU".
**Expected:** `is_critical_care` is 1.

### 10. test_auto_critical_care_flag_micu
**Scenario:** Create a ward with ward_classification "MICU".
**Expected:** `is_critical_care` is 1.

### 11. test_auto_critical_care_flag_hdu
**Scenario:** Create a ward with ward_classification "HDU".
**Expected:** `is_critical_care` is 1.

### 12. test_auto_critical_care_flag_general
**Scenario:** Create a ward with ward_classification "General".
**Expected:** `is_critical_care` is 0.

### 13. test_auto_critical_care_flag_private
**Scenario:** Create a ward with ward_classification "Private".
**Expected:** `is_critical_care` is 0.

### 14. test_available_beds_computed
**Scenario:** Create a ward with total_beds=10, occupied_beds=3.
**Expected:** `available_beds` is 7.

### 15. test_available_beds_zero_when_full
**Scenario:** Create a ward with total_beds=5, occupied_beds=5.
**Expected:** `available_beds` is 0.

### 16. test_available_beds_defaults_to_zero
**Scenario:** Create a ward with no bed counts set.
**Expected:** `available_beds` is 0.

### 17. test_deactivation_allowed_when_no_beds
**Scenario:** Create a ward, set is_active=0, save.
**Expected:** Saves successfully with is_active=0.

### 18. test_hsu_must_be_group
**Scenario:** Link a non-group Healthcare Service Unit to a ward.
**Expected:** Raises `frappe.ValidationError`.

### 19. test_company_abbreviation_required
**Scenario:** Attempt to create a ward for a company that does not exist (and thus has no abbreviation).
**Expected:** Raises an exception during autoname.

## Coverage Summary

| Category | Tests |
|----------|-------|
| CRUD basics | 1 |
| Naming / autoname | 2 |
| Ward code validation | 3 |
| Uniqueness | 2 |
| Critical care flag | 5 |
| Capacity computation | 3 |
| Deactivation | 1 |
| HSU linkage | 1 |
| Company validation | 1 |
| **Total** | **19** |

## Running Tests

```bash
cd /path/to/frappe-bench
bench --site <site> run-tests --app alcura_ipd_ext --doctype "Hospital Ward"
```

Or with pytest (if the bench pytest plugin is configured):

```bash
cd /path/to/frappe-bench/apps/alcura_ipd_ext
pytest alcura_ipd_ext/alcura_ipd_ext/doctype/hospital_ward/test_hospital_ward.py -v
```
