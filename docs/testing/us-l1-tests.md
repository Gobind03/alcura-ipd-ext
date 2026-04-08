# US-L1: Doctor Census — Test Scenarios

## Test File

`alcura_ipd_ext/tests/test_doctor_census_report.py`

## Scenarios

### 1. Pending Tests Column
- Create an IR with `custom_active_lab_orders = 3`
- Census row should show `pending_tests == 3`

### 2. Due Medications Column
- Create an IR with `custom_due_meds_count = 5`
- Census row should show `due_meds == 5`

### 3. Critical Alerts Column
- Create an IR with `custom_critical_alerts_count = 2`
- Census row should show `critical_alerts == 2`

### 4. Zero Defaults
- Create a new IR with no custom field values
- All counter columns should return 0

### 5. Report Execute with Summary
- Create two IRs for the same practitioner, one with critical alerts, one with overdue charts
- `execute()` should return a 5-tuple
- `report_summary` should have 4 entries with correct labels

### 6. Empty Report
- Call `execute({})` without a practitioner
- Data should be empty, summary should be empty

### 7. Ward Filter
- Create an IR with a specific ward
- Census with matching ward filter should include the row
- Census with non-matching ward filter should exclude it

## Pre-existing Tests (US-E5)

The existing `test_round_sheet_service.py` covers:
- Census returns admitted patients only
- Census excludes discharged patients
- Census excludes other practitioners
- Census includes days_admitted
- Problem list CRUD
- Progress note creation
- Patient round summary structure
