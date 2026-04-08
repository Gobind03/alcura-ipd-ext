# US-N1: Nursing Workload by Ward — Test Scenarios

## Test File

`alcura_ipd_ext/tests/test_nursing_workload_report.py`

## Service Tests (`TestNursingWorkloadService`)

| # | Scenario | Expectation |
|---|----------|-------------|
| 1 | No active wards for company | Returns empty list |
| 2 | Two wards with patients | Census counted correctly per ward |
| 3 | High-acuity patient (fall High) | `high_acuity_count` = 1 |
| 4 | Low-risk patient | Not counted in high acuity |
| 5 | Missed MAR entry | `overdue_mar_count` incremented |
| 6 | Workload score with census + acuity | Score >= expected minimum |
| 7 | Ward filter applied | Only specified ward returned |
| 8 | Totals computed | `patient_census` sums across wards |

## Report Tests (`TestNursingWorkloadReport`)

| # | Scenario | Expectation |
|---|----------|-------------|
| 1 | Empty data | 5-tuple with empty data, no chart, no summary |
| 2 | Column presence | Key fieldnames present |
| 3 | Chart generated | Stacked bar chart when data exists |

## Concurrency

Not applicable (report is read-only).

## Assumptions

- Test wards and patients are created per test and rolled back.
- Overdue chart detection is tested separately in `test_charting_service.py`.
- Protocol step counting relies on fixtures from protocol bundle tests.
