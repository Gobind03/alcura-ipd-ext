# US-C3: Payer Eligibility Check — Test Scenarios

## Test File

`alcura_ipd_ext/tests/test_eligibility_service.py`

Co-located stub: `alcura_ipd_ext/alcura_ipd_ext/doctype/payer_eligibility_check/test_payer_eligibility_check.py`

## Test Classes and Scenarios

### TestPayerEligibilityCheckCreation

| Test | Scenario | Expected |
|------|----------|----------|
| `test_create_pending_check` | Create a check with defaults | Status is Pending, submitted_by and submitted_on are set |
| `test_create_check_with_inpatient_record` | Create without inpatient_record | Allowed, field is empty |
| `test_payer_type_fetched_from_profile` | Create check for Cash profile | payer_type auto-fetched as "Cash" |

### TestStatusTransitions

| Test | Scenario | Expected |
|------|----------|----------|
| `test_pending_to_verified` | Change Pending → Verified | Succeeds; verified_by and verification_datetime set |
| `test_pending_to_conditional` | Change Pending → Conditional | Succeeds |
| `test_pending_to_rejected` | Change Pending → Rejected | Succeeds |
| `test_verified_to_expired` | Change Verified → Expired | Succeeds |
| `test_rejected_to_pending` | Change Rejected → Pending | Succeeds (re-verification) |
| `test_expired_to_pending` | Change Expired → Pending | Succeeds (re-verification) |
| `test_invalid_transition_throws` | Change Verified → Rejected | Throws ValidationError |
| `test_pending_to_expired_invalid` | Change Pending → Expired | Throws ValidationError |

### TestAuditFields

| Test | Scenario | Expected |
|------|----------|----------|
| `test_submitted_by_set_on_insert` | Insert new check | submitted_by = current user, submitted_on set |
| `test_verified_by_set_on_verification` | Transition to Verified | verified_by = current user, verification_datetime set |
| `test_last_status_change_updated` | Any status transition | last_status_change_by/on updated |

### TestEligibilityService

| Test | Scenario | Expected |
|------|----------|----------|
| `test_get_latest_returns_verified` | Verified check exists | Returns the check |
| `test_get_latest_returns_conditional` | Conditional check exists | Returns the check |
| `test_get_latest_returns_none_for_pending` | Only Pending check | Returns None |
| `test_get_latest_returns_none_for_rejected` | Only Rejected check | Returns None |
| `test_get_latest_ignores_expired_by_date` | Check with past valid_to | Returns None |
| `test_get_latest_returns_none_when_none_exist` | No checks for patient | Returns None |

### TestAdmissionEligibilityCheck

| Test | Scenario | Expected |
|------|----------|----------|
| `test_ignore_enforcement_always_eligible` | Policy set to Ignore | eligible=True, status=Skipped |
| `test_cash_payer_always_eligible` | Cash payer, Strict policy | eligible=True, status=Cash |
| `test_no_profile_treated_as_cash` | No payer profile on IR | eligible=True, status=No Profile |
| `test_strict_blocks_without_eligibility` | Non-Cash payer, Strict, no check | eligible=False |
| `test_advisory_allows_without_eligibility` | Non-Cash payer, Advisory, no check | eligible=True, status=Not Verified |
| `test_verified_eligibility_passes` | Verified check exists, Strict | eligible=True, eligibility_check set |

### TestDateValidation

| Test | Scenario | Expected |
|------|----------|----------|
| `test_valid_from_after_valid_to_throws` | valid_from > valid_to | Throws ValidationError |
| `test_valid_range_ok` | valid_from < valid_to | Succeeds |
| `test_no_dates_ok` | No dates provided | Succeeds |

### TestPatientProfileCrossValidation

| Test | Scenario | Expected |
|------|----------|----------|
| `test_mismatched_patient_throws` | Profile belongs to different patient | Throws ValidationError |
| `test_matching_patient_ok` | Profile belongs to same patient | Succeeds |

## Running Tests

```bash
cd /path/to/frappe-bench
bench --site test_site run-tests --app alcura_ipd_ext --module alcura_ipd_ext.tests.test_eligibility_service
```

Or with pytest:

```bash
cd apps/alcura_ipd_ext
pytest alcura_ipd_ext/tests/test_eligibility_service.py -v
```
