# US-N2: Incident Alert Report — Test Scenarios

## Test File

`alcura_ipd_ext/tests/test_incident_report.py`

## Service Tests (`TestIncidentReportService`)

| # | Scenario | Expectation |
|---|----------|-------------|
| 1 | Empty date range | Returns empty list |
| 2 | Fall-risk ToDo created | Appears in Fall Risk incidents |
| 3 | Missed MAR entry | Appears with severity = Medium |
| 4 | Breached SLA order (STAT) | Appears with severity = High |
| 5 | Ward filter | Only incidents from specified ward |
| 6 | Severity filter | Only matching severity rows returned |
| 7 | Incident summary | Type counts sum to total rows |

## Report Tests (`TestIncidentAlertReport`)

| # | Scenario | Expectation |
|---|----------|-------------|
| 1 | Empty data | 5-tuple with no chart/summary |
| 2 | Column presence | Key fieldnames present |
| 3 | Chart generated | Pie chart when data exists |

## Assumptions

- Test data is created and rolled back per test via `conftest.py` savepoint.
- Critical observation tests would require chart template + entry setup;
  tested via the charting service test suite.
- ToDo descriptions must match the `<!-- ref:NursingRisk:... -->` pattern
  used by `nursing_alert_service`.
