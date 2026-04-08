# Testing: US-K2 Bed Transfer and Housekeeping Report

## Test File

`alcura_ipd_ext/tests/test_bed_transfer_housekeeping_report.py`

## Test Class

`TestBedTransferHousekeepingReport`

## Test Scenarios

### 1. Transfer Listing

| Test | Description | Expected |
|------|-------------|----------|
| `test_transfer_listing_within_date_range` | Transfers inside and outside date range | Only in-range transfers appear |
| `test_ward_filter_on_transfers` | Transfer from ward A to ward B, filter by A | Transfer found (matches from_ward) |
| `test_transfer_count` | Mix of Transfer and Admission BMLs | Count returns only transfers |

### 2. Blocked Beds

| Test | Description | Expected |
|------|-------------|----------|
| `test_blocked_beds_snapshot` | 2 blocked (maint + infection), 1 clean | Correct 2 beds returned |
| `test_blocked_beds_reason_labels` | Maintenance only vs both flags | Correct reason strings |
| `test_no_blocked_beds` | Clean ward | Empty list |

### 3. Housekeeping TAT

| Test | Description | Expected |
|------|-------------|----------|
| `test_housekeeping_summary_counts` | 2 completed + 1 pending, 1 breached | total=3, completed=2, pending=1, breached=1 |
| `test_housekeeping_avg_tat` | Tasks with 20 and 40 min TAT | avg_tat = 30.0 |
| `test_housekeeping_sla_breach_pct` | 2 of 4 breached | 50.0% |
| `test_housekeeping_by_ward_grouping` | Standard + Deep Clean in same ward | Both types in results |

### 4. Report Execute

| Test | Description | Expected |
|------|-------------|----------|
| `test_report_execute_returns_structure` | Valid filters with data | Returns columns, data, message HTML, 4 summary cards |
| `test_report_empty_filters` | No filters | Graceful handling, valid structure returned |

## Fixtures

Tests use factory functions to create isolated ward/room/bed/BML/housekeeping-task records. All tests use `frappe.db.rollback()` in tearDown.

## Coverage

- Transfer data query with date, ward, consultant filters
- Blocked bed snapshot (current state, not historical)
- Housekeeping summary aggregation
- Housekeeping by ward/cleaning-type grouping
- SLA breach percentage
- Report execute entry point
