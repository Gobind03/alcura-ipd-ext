# Testing: US-C2 Patient Payer Profile

## Test Files

- `alcura_ipd_ext/tests/test_patient_payer_profile.py` — Integration tests
- `alcura_ipd_ext/alcura_ipd_ext/doctype/patient_payer_profile/test_patient_payer_profile.py` — Co-located unit tests

## Test Scenarios

### 1. Profile Creation by Payer Type

| # | Scenario | Expected |
|---|----------|----------|
| 1.1 | Create Cash profile | Success, no payer fields required |
| 1.2 | Create Corporate profile with customer | Success |
| 1.3 | Create Insurance TPA profile with insurance_payor | Success |
| 1.4 | Create PSU profile with customer | Success |
| 1.5 | Create Government Scheme profile with scheme_name | Success |

### 2. Date Validation

| # | Scenario | Expected |
|---|----------|----------|
| 2.1 | valid_from > valid_to | ValidationError thrown |
| 2.2 | valid_from ≤ valid_to | Success |
| 2.3 | valid_from = valid_to (same day) | Success |
| 2.4 | Open-ended (no valid_to) | Success |

### 3. Mandatory Field Enforcement

| # | Scenario | Expected |
|---|----------|----------|
| 3.1 | Insurance TPA without insurance_payor | ValidationError: "Insurance Payor is required" |
| 3.2 | Corporate without payer (Customer) | ValidationError: "Payer (Customer) is required" |
| 3.3 | PSU without payer (Customer) | ValidationError: "Payer (Customer) is required" |
| 3.4 | Government Scheme without customer | Success (customer not required) |
| 3.5 | Cash with no extra fields | Success |

### 4. Duplicate Active Profile Detection

| # | Scenario | Expected |
|---|----------|----------|
| 4.1 | Two active Cash profiles for same patient | Warning (not blocking) |
| 4.2 | One active + one inactive for same patient | No warning |

### 5. Profile Deactivation

| # | Scenario | Expected |
|---|----------|----------|
| 5.1 | Set is_active = 0 | Profile excluded from active queries |
| 5.2 | Re-activate profile | Profile included in active queries |

### 6. Insurance Policy Cross-validation

| # | Scenario | Expected |
|---|----------|----------|
| 6.1 | Policy belongs to different patient | ValidationError: "Patient Mismatch" |
| 6.2 | Policy has different insurance_payor | ValidationError: "Payor Mismatch" |
| 6.3 | Policy matches patient and payor | Success |

### 7. Migration Patch

| # | Scenario | Expected |
|---|----------|----------|
| 7.1 | Room Tariff Mapping with payer_type="TPA" | After patch: "Insurance TPA" |
| 7.2 | Bed Reservation with payer_type="TPA" | After patch: "Insurance TPA" |

### 8. Tariff Service

| # | Scenario | Expected |
|---|----------|----------|
| 8.1 | resolve_tariff_for_profile with invalid profile | Returns None |
| 8.2 | resolve_tariff with "Insurance TPA" payer_type | Falls back to Cash if no TPA mapping exists |

### 9. Fetch Behavior

| # | Scenario | Expected |
|---|----------|----------|
| 9.1 | Insert profile | patient_name fetched from Patient |
| 9.2 | Select insurance_payor | tpa_name fetched from Insurance Payor |

## Running Tests

```bash
# From the bench directory
cd frappe-bench
bench --site <site> run-tests --app alcura_ipd_ext --module alcura_ipd_ext.tests.test_patient_payer_profile

# Co-located unit tests
bench --site <site> run-tests --app alcura_ipd_ext --doctype "Patient Payer Profile"
```

## Coverage Notes

- Permission tests rely on the TPA Desk User role being created during install
- Insurance policy cross-validation tests require existing Insurance Payor and Patient Insurance Policy data; tests skip if unavailable
- Migration patch test creates a record with the old "TPA" value directly via SQL to simulate pre-migration state
