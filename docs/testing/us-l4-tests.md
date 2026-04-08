# US-L4: ICU Protocol Compliance — Test Scenarios

## Test File

`alcura_ipd_ext/tests/test_protocol_compliance_report.py`

## Scenarios

### 1. Patient Name Included
- Create an active bundle linked to an IR
- Report data should include `patient_name` column with a non-empty value

### 2. Delayed Steps Counted
- Create an active bundle with a step completed after its `due_at`
- Report should show `delayed_steps >= 1` and `missed_steps >= 1`

### 3. Step Detail Drilldown
- Call `get_step_detail(active_bundle)` for a bundle with 3 steps
- Should return 3 step rows with `step_name`, `status`, `delay_minutes`
- At least one step should have `delay_minutes > 0`

### 4. Report Summary
- Create an active bundle with 80% compliance
- Report should return summary with "Total Bundles" and "Avg Compliance" labels

### 5. Chart Generated
- Create an active bundle
- Report should return a bar chart by category

### 6. Category Filter
- Create a "Sepsis" category bundle
- Category filter "Sepsis" should include the bundle
- Category filter "Ventilator" should exclude it

### 7. Empty Report
- Query a date range with no bundles
- Data, chart, and summary should be empty/None

## Pre-existing Coverage

The existing `test_protocol_bundle_service.py` covers:
- Bundle activation and step tracker creation
- Step completion and compliance score calculation
- Bundle discontinuation
- Scheduler-based compliance checking
