# US-L2: Progress Notes and Chart Completion Report

## Purpose

Enable medical administrators to identify admitted patients with missing or overdue clinical documentation, improving documentation compliance rates across the hospital.

## Scope

New Documentation Compliance report and supporting service that checks five documentation categories per admitted patient and produces a per-patient compliance score.

## Reused Standard DocTypes

- **Inpatient Record** — primary data source; filtered by status and location
- **Patient Encounter** — checked for admission notes, progress notes, discharge summaries via `custom_ipd_note_type`
- **Healthcare Practitioner** — filter and display

## Reused Custom DocTypes

- **IPD Intake Assessment** — intake completion status via `custom_intake_status` on IR
- **IPD Bedside Chart** — nursing chart currency via `custom_overdue_charts_count` on IR
- **Hospital Ward** — ward filter

## New Custom DocTypes

None.

## Fields Used

All fields are pre-existing custom fields on Inpatient Record:
- `custom_last_progress_note_date`
- `custom_overdue_charts_count`
- `custom_intake_status`
- `custom_current_ward`, `custom_current_bed`

## Documentation Checks

| Check | Source | Pass Condition |
|-------|--------|----------------|
| Admission Note | Patient Encounter (submitted, type=Admission Note) | At least one exists |
| Daily Progress Note | Patient Encounter (submitted, type=Progress Note) | Latest note within 24 hours |
| Intake Assessment | IR `custom_intake_status` | Status is "Completed" |
| Nursing Charts | IR `custom_overdue_charts_count` | Count is 0 |
| Discharge Summary | Patient Encounter (submitted, type=Discharge Summary) | Required only for Discharge Initiated/In Progress status |

## Compliance Score

Percentage of applicable checks that pass. Discharge summary check is excluded for patients still in Admitted status.

## Report Design

- ref_doctype: Inpatient Record
- Type: Script Report with chart
- Chart: Bar chart showing patient distribution across compliance buckets (100%, 75-99%, 50-74%, <50%)

## Filters

| Filter | Type | Default |
|--------|------|---------|
| Company | Link | User default |
| Ward | Link (Hospital Ward) | -- |
| Practitioner | Link (Healthcare Practitioner) | -- |
| Department | Link (Medical Department) | -- |
| Status | Select | Admitted |

## Report Summary Cards

- Total Patients
- Avg Compliance (color-coded)
- Missing Adm Note
- Overdue Progress Notes
- Missing Intake
- Charts Overdue

## Permissions

| Role | Access |
|------|--------|
| Healthcare Administrator | Yes |
| Nursing User | Yes |

## Client-Side UX

- Color-coded compliance scores: red <50%, orange 50-74%, green >=75%
- MISSING/PENDING/OVERDUE pills on boolean columns for quick visual scanning

## Validation Logic

All compliance logic is server-side in `documentation_compliance_service.py`. Client-side formatting is for display only.

## Performance

- Uses batch SQL queries to avoid N+1 patterns
- Admission note and progress note checks use GROUP BY queries
- Practitioner name resolution is batched

## Notifications

None (this is a pull report for administrative review).

## Test Cases

See `docs/testing/us-l2-tests.md`

## Open Questions / Assumptions

- Progress note gap threshold of >1 day is hardcoded. Consider making this configurable via a settings doctype if requirements vary by department.
- Discharge summary check only applies when IR status is "Discharge Initiated" or "Discharge in Progress". If hospitals need it checked earlier, the status list can be extended.
