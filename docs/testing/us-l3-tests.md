# US-L3: Order TAT Report — Test Scenarios

## Test File

`alcura_ipd_ext/tests/test_order_tat_report.py`

## Order TAT Report Scenarios

### 1. TAT Calculated for Completed Orders
- Create a clinical order with `ordered_at` 1 hour ago and `completed_at` now
- TAT should be approximately 60 minutes

### 2. Report Returns Summary Metrics
- Create at least one completed order
- `execute()` should return 5-tuple with summary containing "Total Orders"

### 3. Department Column Present
- Verify `_get_columns()` includes `target_department`

### 4. SLA Target Column Present
- Verify `_get_columns()` includes `sla_target_minutes`

### 5. Chart Generated
- Create a completed order with TAT data
- Report should return a bar chart

### 6. Empty Report
- Query a date range with no orders
- Data, chart, and summary should be empty/None

## SLA Breach Report Scenarios

### 7. Department Column in Breach Report
- Verify `_get_columns()` includes `target_department`

### 8. Breach Report Returns Summary
- Create a breached order
- Report should return summary with "Breached Orders" label

### 9. Breach Report Chart
- Create a breached order
- Report should return a bar chart of type "bar"

## Pre-existing Coverage

The existing `test_order_sla_service.py` covers SLA milestone creation, breach detection, and the scheduler-based breach checking logic.
