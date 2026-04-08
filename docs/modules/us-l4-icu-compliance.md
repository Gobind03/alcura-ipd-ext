# US-L4: ICU Protocol Compliance Report

## Purpose

Enable critical care heads to monitor protocol adherence across ICU, CICU, MICU and other intensive care units. The report surfaces bundle compliance scores, missed and delayed steps, and supports drilldown to individual step-level detail for quality review.

## Scope

Enhancement to the existing Protocol Compliance Report to add:
- ICU unit type filtering (via Healthcare Service Unit Type's `ipd_room_category`)
- Protocol category filter
- Patient name column
- Delayed step count column
- Step-level detail drilldown dialog
- Summary metrics (avg compliance, full compliance count, total missed, delayed)
- Compliance bar chart by protocol category

## Reused Standard DocTypes

- **Healthcare Service Unit Type** — `ipd_room_category` custom field used for unit type filtering

## Reused Custom DocTypes

- **Monitoring Protocol Bundle** — protocol definition with category
- **Active Protocol Bundle** — per-patient activated bundles with compliance score
- **Protocol Step Tracker** — child table tracking individual step status, timing
- **Hospital Ward** — ward filtering, linked to service unit type
- **Inpatient Record** — patient location and name lookup

## New Custom DocTypes

None.

## New Columns

| Column | Source | Description |
|--------|--------|-------------|
| Patient Name | Inpatient Record `patient_name` | Patient display name |
| Delayed | Protocol Step Tracker | Count of steps completed after `due_at` |

## New Filters

| Filter | Type | Description |
|--------|------|-------------|
| Category | Select | Protocol bundle category (ICU, Sepsis, Ventilator, etc.) |
| Unit Type | Select | Healthcare Service Unit Type's IPD Room Category (ICU, CICU, MICU, etc.) |

## Step Detail Drilldown

Clicking the list icon on any Active Bundle row opens a dialog showing all Protocol Step Tracker rows with:
- Step name, type, sequence, mandatory flag
- Status (color-coded: green=Completed, red=Missed, yellow=Pending)
- Due at, Completed at
- Delay (minutes) — computed from `completed_at - due_at`
- Notes

The `get_step_detail()` function is exposed as a whitelisted report method.

## Summary Metrics

- Total Bundles
- Avg Compliance (color-coded: red <80%, orange <95%, green otherwise)
- Full Compliance (bundles with 100% score)
- Total Missed Steps (red indicator when >0)
- Delayed Steps (orange indicator when >0)

## Chart

Bar chart showing average compliance percentage by protocol category.

## Permissions

| Role | Access |
|------|--------|
| Healthcare Administrator | Yes |
| ICU Administrator | Yes |
| Physician | Yes |

## Performance

- Batch SQL queries for IR data (ward, patient_name) and step counts
- Ward-by-unit-type lookup uses JOIN against Healthcare Service Unit Type
- Step counts aggregated in single GROUP BY query per batch

## Validation Logic

All compliance scoring and step counting is server-side. The category and unit_type filters are applied via SQL conditions or post-query filtering (for unit type, since it requires a JOIN to the ward's service unit type).

## Notifications

The existing `check_protocol_compliance` scheduler task (runs every 15 minutes) handles protocol step status updates and compliance score recalculation.

## Test Cases

See `docs/testing/us-l4-tests.md`

## Open Questions / Assumptions

- The `unit_type` filter relies on the `ipd_room_category` custom field on `Healthcare Service Unit Type` and the `service_unit_type` field on `Hospital Ward`. If wards are not configured with service unit types, this filter will return no results.
- Protocol category options in the filter are hardcoded. If new categories are added to `Monitoring Protocol Bundle`, the filter options should be updated.
- Delayed step counting considers any step completed after its `due_at` time as delayed, regardless of how large the delay is.
