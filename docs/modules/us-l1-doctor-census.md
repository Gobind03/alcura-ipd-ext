# US-L1: Doctor's Admitted Patient Census

## Purpose

Provide a doctor-centric dashboard of all admitted patients, designed for daily ward round preparation and real-time clinical oversight. The census surfaces key operational metrics at a glance so the doctor can prioritise patients and efficiently conduct rounds.

## Scope

Enhancement to the existing Doctor Census report (US-E5) to add pending tests, due medications, and critical alerts columns, plus a "View Round Summary" action button and report summary cards.

## Reused Standard DocTypes

- **Inpatient Record** — primary data source, filtered by `primary_practitioner` and `status = "Admitted"`
- **Patient** — linked for drilldown
- **Healthcare Practitioner** — report filter
- **Medical Department** — report filter
- **Patient Encounter** — round note creation target

## Reused Custom DocTypes

- **Hospital Ward** — ward filter
- **IPD Clinical Order** — pending test count via `custom_active_lab_orders` on IR
- **IPD MAR Entry** — due medication count via `custom_due_meds_count` on IR
- **IPD Chart Observation** — critical alerts via `custom_critical_alerts_count` on IR

## New Custom Fields (on Inpatient Record)

| Field | Type | Description |
|-------|------|-------------|
| `custom_due_meds_count` | Int | Count of today's due/scheduled MAR entries |
| `custom_critical_alerts_count` | Int | Count of active critical observations |

These fields are read-only, updated by scheduler tasks and service methods.

## Columns Added

| Column | Source | Description |
|--------|--------|-------------|
| Pending Tests | `custom_active_lab_orders` | Lab orders not yet completed |
| Due Meds | `custom_due_meds_count` | Today's due medication entries |
| Critical | `custom_critical_alerts_count` | Active critical observation count |

## Report Summary Cards

Displayed above the grid:
- Total Patients
- With Critical Alerts (red indicator)
- Overdue Charts (orange indicator)
- Pending Tests (blue indicator)

## Interactive Features

- **Start Round Note** — creates a Progress Note encounter for the selected patient
- **View Round Summary** — opens a dialog with full clinical snapshot (problems, vitals, labs, meds, fluid balance, notes)

## Permissions

| Role | Access |
|------|--------|
| Physician | Yes |
| Healthcare Administrator | Yes |

## Client-Side UX

- Color-coded pills for critical alerts (red), pending tests (blue), due meds (orange), allergy (red), overdue charts (red)
- Long-stay patients (>7 days) highlighted in red
- Round Summary dialog renders all subsystem data in a two-column layout

## Validation Logic

- Practitioner filter is required
- Service-level permission check on `Inpatient Record` read access

## Test Cases

See `docs/testing/us-l1-tests.md`

## Open Questions / Assumptions

- `custom_due_meds_count` and `custom_critical_alerts_count` are assumed to be maintained by existing scheduler tasks. If not yet updated by schedulers, the fields will default to 0 until the relevant tasks run.
- The report uses denormalised counts on the IR for performance. These are eventually consistent with the source data.
