# Testing: US-H2 — High-Frequency ICU Observations

## Test File

`alcura_ipd_ext/tests/test_observation_trend_service.py`

## Test Scenarios

### Parameter Trend (TestParameterTrend)

| Scenario | Method | Expectation |
|----------|--------|-------------|
| Returns time-series | test_returns_time_series | 3 entries with correct values |
| Date range filter | test_respects_date_range | Only entries in range |
| Limit respected | test_respects_limit | Max 2 returned |

### Multi-Parameter Trend (TestMultiParameterTrend)

| Scenario | Method | Expectation |
|----------|--------|-------------|
| Keyed data returned | test_returns_keyed_data | Both Temperature and Pulse present |

### Observation Schedule (TestObservationSchedule)

| Scenario | Method | Expectation |
|----------|--------|-------------|
| Expected slots generated | test_generates_expected_slots | Slots with timestamps |
| Missed slots detected | test_identifies_missed_slots | missed_count > 0 |

### Overdue Severity (TestOverdueSeverity)

| Scenario | Method | Expectation |
|----------|--------|-------------|
| Warning (1x) | test_warning_severity | "Warning" |
| Escalation (2x) | test_escalation_severity | "Escalation" |
| Critical (3x+) | test_critical_severity | "Critical" |
| Not overdue | test_not_overdue | None |

### Dashboard Summary (TestDashboardSummary)

| Scenario | Method | Expectation |
|----------|--------|-------------|
| Chart summaries returned | test_returns_chart_summaries | At least 1 result |
