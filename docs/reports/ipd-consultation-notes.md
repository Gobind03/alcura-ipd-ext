# Report: IPD Consultation Notes

## Purpose

Provide operational visibility into consultant clinical documentation across admitted patients, enabling tracking of note completeness, practitioner activity, and ward-level documentation status.

## Report Type

Script Report (ref doctype: Patient Encounter)

## Location

`alcura_ipd_ext/alcura_ipd_ext/report/ipd_consultation_notes/`

## Filters

| Filter | Type | Options | Default |
|--------|------|---------|---------|
| Company | Link -> Company | | User default company |
| Patient | Link -> Patient | | |
| Practitioner | Link -> Healthcare Practitioner | | |
| Department | Link -> Medical Department | | |
| Note Type | Select | Admission Note / Progress Note / Procedure Note / Consultation Note / Discharge Summary | |
| Ward | Link -> Hospital Ward | | |
| From Date | Date | | |
| To Date | Date | | |

## Columns

| Column | Type | Width | Notes |
|--------|------|-------|-------|
| Encounter | Link -> Patient Encounter | 140 | |
| Date | Date | 100 | |
| Patient | Link -> Patient | 120 | |
| Patient Name | Data | 160 | |
| Practitioner | Data | 150 | Practitioner name |
| Note Type | Data | 130 | Color-coded pill badges |
| Chief Complaint | Data | 200 | |
| Provisional Diagnosis | Data | 200 | |
| Inpatient Record | Link -> Inpatient Record | 140 | |
| Ward | Data | 100 | From IR `custom_current_ward` |
| Room | Data | 100 | From IR `custom_current_room` |
| Bed | Data | 100 | From IR `custom_current_bed` |
| Status | Data | 80 | Draft / Submitted |

## Query Design

Uses Frappe Query Builder to join `Patient Encounter` with `Inpatient Record` on `custom_linked_inpatient_record`. Filters on `custom_ipd_note_type IS NOT NULL` and `docstatus != 2` (excludes cancelled). Ordered by encounter date descending.

## Formatting

- Note Type: color-coded indicator pills (Admission Note: blue, Progress Note: green, Procedure Note: orange, Consultation Note: purple, Discharge Summary: grey)
- Status: Draft (orange pill), Submitted (blue pill)

## Permissions

| Role | Access |
|------|--------|
| Healthcare Administrator | Full access |
| Physician | Full access |
| Nursing User | Read access |

## Workspace

Listed under "Reports" card in the IPD Desk workspace.

## Related

- [modules/us-e3-consultant-admission-notes.md](../modules/us-e3-consultant-admission-notes.md)
