# US-H2: High-Frequency ICU Observations

## Purpose

Enable ICU nurses to record minute/hourly clinical observations with
trend visualisation, missed-observation tracking, and dashboard feeds
for unstable patients.

## Scope

- Time-series trend API for single and multi-parameter graphs
- Expected vs actual observation schedule with missed-slot detection
- Severity classification for overdue charts (Warning/Escalation/Critical)
- ICU dashboard summary with shift-based entry counts
- Client-side trend chart components using frappe.Chart
- Performance indexes for high-frequency query patterns

## Reused Custom DocTypes

| DocType | Usage |
|---------|-------|
| IPD Bedside Chart | Query source; `missed_count` field added |
| IPD Chart Entry | Trend query source; `is_device_generated` added |
| IPD Chart Observation | Joined for parameter-level trends |

## New Custom DocTypes

None. This story extends existing charting infrastructure.

## Fields Added

### IPD Bedside Chart

| Field | Type | Notes |
|-------|------|-------|
| missed_count | Int | Read-only, incremented by scheduled task |

## New Service: `observation_trend_service.py`

| Function | Purpose |
|----------|---------|
| get_parameter_trend | Single-parameter time-series for graphing |
| get_multi_parameter_trend | Multi-parameter overlay |
| get_observation_schedule | Expected vs actual slots with missed detection |
| compute_missed_observations | Missed count and slot list |
| get_dashboard_summary | Per-chart summary for ICU dashboard |
| classify_overdue_severity | Warning / Escalation / Critical classification |

## New API Endpoints (charting.py)

| Endpoint | Method |
|----------|--------|
| get_observation_trend | GET |
| get_multi_parameter_trend | GET |
| get_observation_schedule | GET |
| get_dashboard_summary | GET |

## Client Components (icu_trend_chart.js)

| Class | Purpose |
|-------|---------|
| ICUTrendChart | Single-parameter line chart with critical bands |
| ICUMultiTrendChart | Multi-parameter overlay chart |
| ObservationScheduleGrid | Expected vs actual schedule table |

## Performance Indexes

Added via patch v0_0_8:
- `idx_ce_chart_datetime` on IPD Chart Entry (bedside_chart, entry_datetime)
- `idx_ce_ir_datetime` on IPD Chart Entry (inpatient_record, entry_datetime)
- `idx_co_parent_param` on IPD Chart Observation (parent, parameter_name)

## Enhanced Overdue Detection (tasks.py)

- ICU charts (frequency <= 60 min): 5-minute grace before alerting
- Standard charts: 15-minute grace (unchanged)
- Severity classification in notification subject
- `missed_count` incremented on each overdue check cycle

## Test Cases

See `tests/test_observation_trend_service.py`:
- Trend returns time-series data with correct values
- Date range and limit filters work
- Multi-parameter trend returns keyed data
- Schedule generates expected slots and matches actual entries
- Missed observations detected for charts with no entries
- Severity classification: Warning/Escalation/Critical/None
- Dashboard summary returns chart summaries

## Open Questions / Assumptions

- Grace period is proportional (25% of interval or 5 min minimum) for schedule matching
- Trend queries use raw SQL for performance on high-frequency charts
- `missed_count` is a running counter, not a window-based metric
