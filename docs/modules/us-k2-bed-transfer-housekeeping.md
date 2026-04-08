# US-K2: Bed Transfer and Housekeeping Report

## Purpose

Provide hospital administrators with a combined view of bed transfers, blocked beds, and housekeeping turnaround times so that capacity bottlenecks are visible and actionable.

## Scope

- Transfer log listing with consultant, reason, and ward breakdown
- Currently blocked beds with reason (maintenance hold, infection block)
- Housekeeping TAT aggregate and per-ward/cleaning-type breakdown
- SLA breach tracking
- Date range, ward, consultant, and branch filtering

## Reused Standard DocTypes

| DocType | Usage |
|---------|-------|
| Bed Movement Log | Transfer and discharge movement entries |
| Hospital Bed | Current blocked bed snapshot |
| Bed Housekeeping Task | TAT and SLA breach metrics |
| Hospital Ward | Ward filter and grouping |
| Healthcare Practitioner | Consultant filter |

## New Custom DocTypes

None.

## Fields Added

None.

## Workflow States

N/A — read-only report.

## Permissions

| Role | Access |
|------|--------|
| Healthcare Administrator | Read |
| Nursing User | Read |
| Physician | Read |

## Validation Logic

- Transfer data filtered by movement_datetime within date range
- Ward filter matches from_ward OR to_ward (captures both sides of transfer)
- Blocked beds are a current snapshot (not historical)
- TAT only includes completed tasks with non-null turnaround_minutes
- SLA breach % = sla_breached_count / total_tasks * 100

## Notifications

None.

## Reporting Impact

- New report: **Bed Transfer and Housekeeping**
- Added to IPD Desk and IPD Operations workspaces

## Test Cases

See `docs/testing/us-k2-tests.md`

## Assumptions

- Blocked beds are a real-time snapshot, not historical
- Branch filter uses Hospital Ward.branch via subquery
- Movement types shown default to Transfer + Discharge (Admission excluded by default)
- Housekeeping tasks created_on is used for date filtering (not completed_on)

## Open Questions

- Should the blocked beds section show duration (days blocked) rather than just "since" timestamp?
- Should housekeeping TAT filter by completed_on rather than created_on for stricter period accuracy?
