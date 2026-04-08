# Testing: US-E5 — Doctor Progress Notes and Round Sheets

## Test Files

- `alcura_ipd_ext/tests/test_round_sheet_service.py` — Service-layer integration tests
- `alcura_ipd_ext/alcura_ipd_ext/doctype/ipd_problem_list_item/test_ipd_problem_list_item.py` — DocType controller tests

## Test Scenarios

### Doctor Census

| # | Scenario | Expected Result |
|---|----------|----------------|
| 1 | Census for practitioner with admitted patients | Returns all admitted patients for that practitioner |
| 2 | Census excludes discharged patients | Only Admitted status IRs appear |
| 3 | Census excludes other practitioners' patients | Only the specified practitioner's patients appear |
| 4 | Census includes days_admitted calculation | Computed as today - admission_date + 1 |

### Problem List CRUD

| # | Scenario | Expected Result |
|---|----------|----------------|
| 5 | Add problem to admitted IR | IPD Problem List Item created with Active status, auto-set added_on |
| 6 | Resolve active problem | Status changes to Resolved; resolved_on and resolved_by auto-set |
| 7 | Resolve already-resolved problem | Throws error |
| 8 | Get active problems | Returns Active and Monitoring items, excludes Resolved |
| 9 | IR problem count auto-updates on add/resolve | custom_active_problems_count reflects current active count |
| 10 | Sequence number auto-increments | Each new problem gets a higher sequence_number |

### Problem List Validation

| # | Scenario | Expected Result |
|---|----------|----------------|
| 11 | Add problem to discharged IR | Raises ValidationError |
| 12 | Re-activating resolved problem clears resolution fields | resolved_on and resolved_by become None |
| 13 | IR count updated on problem delete | Count decreases appropriately |

### Progress Note Encounter

| # | Scenario | Expected Result |
|---|----------|----------------|
| 14 | Create progress note with problems | Encounter created with Progress Note type; custom_active_problems_text populated |
| 15 | Progress note updates IR last note date | custom_last_progress_note_date set to today |
| 16 | Progress note without problems | Works normally; custom_active_problems_text is empty |

### Patient Round Summary

| # | Scenario | Expected Result |
|---|----------|----------------|
| 17 | Summary for admitted patient | Returns all data sections (patient, location, alerts, problems, vitals, labs, meds, balance, notes) |
| 18 | Summary for non-existent IR | Raises DoesNotExistError |

### Pending Lab Tests

| # | Scenario | Expected Result |
|---|----------|----------------|
| 19 | No prescriptions | Returns empty list |

### DocType Controller

| # | Scenario | Expected Result |
|---|----------|----------------|
| 20 | Auto-set added_on on insert | added_on is not None after insert |
| 21 | Default status is Active | New problem has status Active |
| 22 | Resolved fields set on resolve | resolved_on is set when status changes to Resolved |
| 23 | Resolved fields cleared on reactivate | resolved_on/by become None when status changes from Resolved |
| 24 | Validation rejects discharged IR | ValidationError raised |
| 25 | IR count updated on insert | custom_active_problems_count incremented |
| 26 | IR count updated on trash | custom_active_problems_count decremented |

## Coverage Notes

- Tests use `IntegrationTestCase` with `frappe.db.rollback()` for isolation
- Factory functions create minimal test data (Company, Patient, Practitioner, Inpatient Record)
- All tests run as Administrator for simplicity; permission-specific tests use the standard permission framework
- No external service dependencies; all data is created in-test
