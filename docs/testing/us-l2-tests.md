# US-L2: Documentation Compliance — Test Scenarios

## Test File

`alcura_ipd_ext/tests/test_documentation_compliance_service.py`

## Scenarios

### 1. Empty Result
- Query with a nonexistent company
- Should return empty list

### 2. New Admission Has Low Compliance
- Create a new IR with no documentation
- Compliance score should be <50%

### 3. Admission Note Detection
- Create an IR and submit a Patient Encounter with `custom_ipd_note_type = "Admission Note"`
- `has_admission_note` should be 1

### 4. Progress Note Gap - Today
- Submit a Progress Note encounter dated today
- `progress_note_gap` should be 0

### 5. Progress Note Gap - Aged
- Create an IR with admission 3 days ago, no progress notes
- `progress_note_gap` should equal `days_admitted`

### 6. Intake Complete Flag
- Set `custom_intake_status = "Completed"` on IR
- `intake_complete` should be 1

### 7. Overdue Charts Flag
- Set `custom_overdue_charts_count = 3`
- `nursing_charts_ok` should be 0, `overdue_charts` should be 3

### 8. Discharge Summary Not Applicable
- IR with status "Admitted" (not discharge-initiated)
- `has_discharge_summary` should be None

### 9. Compliance Score - All Passing
- Row with all checks passing
- Score should be 100%

### 10. Compliance Score - Partial
- Row with 2 of 4 checks passing
- Score should be 50%

### 11. Report Execute Returns Chart
- Call `execute()` with a practitioner filter
- Should return 5-tuple with chart config of type "bar" and 6 summary entries
