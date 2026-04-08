# US-K1: Bed Occupancy Dashboard

## Purpose

Provide operations managers with a live aggregate view of bed occupancy across wards and room types, along with KPIs for average length of stay and housekeeping turnaround, enabling proactive admission management and capacity planning.

## Scope

- Aggregate occupancy metrics by ward and room type
- Occupancy percentage with color-coded thresholds
- Average LOS for currently admitted patients
- Average bed turnaround from housekeeping tasks
- Critical care (ICU/HDU) occupancy subset
- Bar chart visualization
- Filterable by company, branch, ward, room type

## Reused Standard DocTypes

| DocType | Usage |
|---------|-------|
| Hospital Bed | Source for occupancy/status counts |
| Hospital Ward | Grouping dimension, location filters |
| Hospital Room | Join for bed-to-ward mapping |
| Healthcare Service Unit Type | Room type dimension |
| Inpatient Record | Average LOS computation (scheduled_date, status, custom_current_ward) |
| Bed Housekeeping Task | Turnaround metrics (turnaround_minutes, status, completed_on) |

## New Custom DocTypes

None.

## Fields Added

None (no custom fields added to standard doctypes).

## Workflow States

N/A — this is a read-only report.

## Permissions

| Role | Access |
|------|--------|
| Healthcare Administrator | Read |
| Nursing User | Read |
| Physician | Read |

## Validation Logic

- All bed counts use `is_active = 1` for beds, rooms, and wards
- Occupancy % = occupied / total * 100, rounded to 1 decimal
- LOS = DATEDIFF(reference_date, scheduled_date) + 1
- Turnaround uses only completed housekeeping tasks with non-null turnaround_minutes

## Notifications

None.

## Reporting Impact

- New report: **Bed Occupancy Dashboard**
- Added to IPD Desk and IPD Operations workspaces

## Test Cases

See `docs/testing/us-k1-tests.md`

## Assumptions

- LOS is calculated from `Inpatient Record.scheduled_date` (admission date) to today
- Turnaround averages use completed `Bed Housekeeping Task` records
- "Blocked" includes maintenance hold, infection block, dirty, and cleaning-in-progress beds
- Deaths are not separately tracked in this report (that is US-K3 ADT scope)
- Branch filter uses `Hospital Ward.branch` field

## Open Questions

- Should the dashboard auto-refresh on a timer? Currently uses manual refresh button.
- Should occupancy thresholds (70%, 90%) be configurable via IPD Bed Policy?
