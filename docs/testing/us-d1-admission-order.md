# US-D1: Admission Order — Test Scenarios

## Test File

`alcura_ipd_ext/tests/test_admission_order_service.py`

## Test Cases

| # | Test | Description |
|---|------|-------------|
| 1 | `test_create_admission_from_encounter` | Happy path: creates IR with all custom fields, back-links encounter |
| 2 | `test_requested_ward_is_set` | Requested ward is populated on the IR when provided |
| 3 | `test_expected_discharge_calculated` | Expected discharge = today + LOS days |
| 4 | `test_duplicate_admission_from_encounter_fails` | Cannot order admission twice from the same encounter |
| 5 | `test_draft_encounter_fails` | Cannot order from a draft (unsubmitted) encounter |
| 6 | `test_default_priority_is_routine` | Priority defaults to "Routine" when not specified |
| 7 | `test_practitioner_carried_over` | Encounter practitioner → IR primary_practitioner |
| 8 | `test_payer_profile_carried_from_patient` | Patient's default payer profile → IR custom_patient_payer_profile |
| 9 | `test_timeline_comment_on_ir` | Timeline comment with priority info added to IR |

## Coverage Areas

- **Service layer**: `admission_order_service.create_admission_from_encounter()`
- **Validation**: docstatus check, duplicate prevention, patient presence
- **Data propagation**: custom field values, practitioner, department, payer profile
- **Audit trail**: timeline comments on IR, encounter, patient
