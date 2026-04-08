# US-N3: Device Observation Exception — Test Scenarios

## Test File

`alcura_ipd_ext/tests/test_device_exception_report.py`

## Connectivity Failure Tests (`TestConnectivityFailures`)

| # | Scenario | Expectation |
|---|----------|-------------|
| 1 | Error-status device feed | Appears as Connectivity Failure |
| 2 | Device type filter | Only matching device type returned |
| 3 | Empty date range | Returns empty list |

## Missing Observation Tests (`TestMissingObservations`)

| # | Scenario | Expectation |
|---|----------|-------------|
| 1 | Device-sourced chart with no entries | Missing slots detected |

## Unacknowledged Abnormal Tests (`TestUnacknowledgedAbnormals`)

| # | Scenario | Expectation |
|---|----------|-------------|
| 1 | Critical device entry with no follow-up | Appears as unacknowledged |
| 2 | Critical device entry WITH manual follow-up | Excluded from results |

## Exception Summary Tests (`TestExceptionSummary`)

| # | Scenario | Expectation |
|---|----------|-------------|
| 1 | Mixed exception rows | Summary counts correct by type |

## Report Tests (`TestDeviceObservationExceptionReport`)

| # | Scenario | Expectation |
|---|----------|-------------|
| 1 | Empty data | 5-tuple with no chart/summary |
| 2 | Column presence | Key fieldnames present |
| 3 | Chart generated | Bar chart when data exists |

## Assumptions

- Device feeds and chart entries are created per test and rolled back.
- `is_critical` on chart observations may need to be set manually in
  tests since the chart template threshold validation runs in the
  controller, not during raw insert.
- Device Observation Mapping is required for device_type filtering
  on missing observation and unacknowledged abnormal tests.
