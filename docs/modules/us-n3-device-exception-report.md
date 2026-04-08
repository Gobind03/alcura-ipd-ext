# US-N3: Device Connectivity and Observation Exception Report

## Purpose

Enable ICU operations managers to identify and close monitoring gaps
by showing device feed failures, missing observation intervals, and
unacknowledged abnormal readings in a single consolidated report.

## Scope

Single Script Report with supporting service module. Read-only; no
new doctypes or custom fields.

## Reused Standard Doctypes

- **Inpatient Record** — links device feeds and charts to admissions
- **Patient** — patient identity

## Reused Custom Doctypes

- **Device Observation Feed** — connectivity failure detection (`status = Error`)
- **Device Observation Mapping** — maps device types to chart templates
- **IPD Bedside Chart** — observation schedule basis; `source_profile` indicates
  device-sourced charts
- **IPD Chart Entry** / **IPD Chart Observation** — critical observation detection
  (`is_device_generated = 1`, `is_critical = 1`)
- **Hospital Ward** — ward filter

## New Custom Doctypes

None.

## Fields Added

None.

## Service Design

`services/device_exception_service.py` provides:

- `get_exceptions(from_date, to_date, ...)` — returns unified exception rows
- `get_exception_summary(rows)` — count by exception type

### Exception Definitions

1. **Connectivity Failure**: `Device Observation Feed.status = 'Error'`
   within the date range.

2. **Missing Observation**: An expected observation slot (per chart
   `frequency_minutes`) with no actual `IPD Chart Entry` within a
   grace window (25% of interval or 5 minutes, whichever is larger).
   Only applies to active charts with `source_profile` set (device-sourced).

3. **Unacknowledged Abnormal**: A device-generated chart entry
   (`is_device_generated = 1`) containing a critical observation
   (`is_critical = 1`) that was NOT followed by a manual chart entry
   (`is_device_generated = 0`) on the same chart within 30 minutes.

### Acknowledgement Window

Configurable via `_ACK_WINDOW_MINUTES` constant (default: 30). A
follow-up manual entry on the same bedside chart within this window
counts as acknowledgement.

## Workflow States

N/A (report only).

## Permissions

- Healthcare Administrator
- ICU Administrator
- Nursing User

## Validation Logic

None (read-only report).

## Notifications

None (device feed errors and critical alerts have their own
notification flows via `device_feed_service` and `tasks.check_overdue_charts`).

## Reporting Impact

New report: **Device Observation Exception** in IPD Operations workspace.

## Test Cases

See `docs/testing/us-n3-device-exception-report.md`.

## Open Questions / Assumptions

- Missing observation detection only targets charts with `source_profile`
  set, avoiding false positives on manually-charted templates.
- The 30-minute acknowledgement window is a code constant and not yet
  configurable via settings.
- Device type filtering uses `Device Observation Mapping` to associate
  chart templates with device types.
- Each query is limited to 500 rows for performance.
