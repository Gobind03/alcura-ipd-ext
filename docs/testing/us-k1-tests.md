# Testing: US-K1 Bed Occupancy Dashboard

## Test File

`alcura_ipd_ext/tests/test_occupancy_metrics_service.py`

## Test Class

`TestOccupancyMetricsService`

## Test Scenarios

### 1. Ward Occupancy Aggregation

| Test | Description | Expected |
|------|-------------|----------|
| `test_ward_occupancy_counts` | Mixed bed statuses (occupied, reserved, maintenance, vacant) | Correct per-ward counts for each status category |
| `test_ward_occupancy_percentage` | 2 of 5 beds occupied | occupancy_pct = 40.0 |
| `test_ward_filter_narrows_result` | Two wards, filter by one | Only filtered ward in results |
| `test_empty_ward_returns_empty` | Non-existent ward | Empty list returned |

### 2. Room Type Grouping

| Test | Description | Expected |
|------|-------------|----------|
| `test_room_type_grouping` | Beds in two room types, one occupied | Correct counts per room type |

### 3. Critical Care Summary

| Test | Description | Expected |
|------|-------------|----------|
| `test_critical_care_summary` | ICU ward with beds | total >= 2, non-ICU excluded |
| `test_critical_care_empty` | Non-existent ward | total = 0, occupancy_pct = 0.0 |

### 4. Average LOS

| Test | Description | Expected |
|------|-------------|----------|
| `test_avg_los_computation` | Two patients admitted 5 and 10 days ago | avg_los = 8.0 |
| `test_avg_los_empty` | No admitted patients | Empty dict |

### 5. Bed Turnaround

| Test | Description | Expected |
|------|-------------|----------|
| `test_bed_turnaround_avg` | Two tasks with 30 and 60 min turnaround | avg = 45.0 |
| `test_bed_turnaround_empty` | No completed tasks | Empty dict |

### 6. Overall Summary

| Test | Description | Expected |
|------|-------------|----------|
| `test_overall_summary_counts` | 3 beds: 1 occupied, 1 dirty, 1 clean | total=3, occupied=1, blocked=1, available=1, occupancy_pct=33.3 |

### 7. Report Execute

| Test | Description | Expected |
|------|-------------|----------|
| `test_report_execute_ward_view` | Ward grouping | Columns include 'ward' and 'occupancy_pct'; summary is list |
| `test_report_execute_room_type_view` | Room Type grouping | Columns include 'room_type', not 'ward' |
| `test_report_chart_returned` | Data available | Chart with type 'bar' returned |
| `test_report_empty_data_no_chart` | No data | Chart is None |

## Fixtures

Tests use factory functions to create isolated ward/room/bed/IR/housekeeping-task records. All tests use `frappe.db.rollback()` in tearDown for isolation.

## Coverage

- Service layer: `occupancy_metrics_service.py` (all public functions)
- Report layer: `bed_occupancy_dashboard.py` (execute entry point)
- Filters: ward, company, room type
- Edge cases: empty results, zero-division protection
