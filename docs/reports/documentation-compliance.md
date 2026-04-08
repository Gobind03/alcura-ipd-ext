# Report: Documentation Compliance

## Purpose

Identifies admitted patients with missing or overdue clinical documentation. Shows documentation completeness per patient with a computed compliance score, enabling medical administrators to drive documentation quality improvement.

## Type

Script Report with chart

## Reference DocType

Inpatient Record

## Filters

| Filter | Type | Required | Default |
|--------|------|----------|---------|
| Company | Link (Company) | No | User default |
| Ward | Link (Hospital Ward) | No | All |
| Practitioner | Link (Healthcare Practitioner) | No | All |
| Department | Link (Medical Department) | No | All |
| Status | Select | No | Admitted |

## Columns

| Column | Type | Width | Notes |
|--------|------|-------|-------|
| Inpatient Record | Link | 140 | Links to IR form |
| Patient | Link | 120 | Links to Patient form |
| Patient Name | Data | 150 | -- |
| Ward | Data | 100 | Current ward |
| Bed | Data | 80 | Current bed |
| Doctor | Data | 140 | Practitioner name |
| Days | Int | 60 | Days since admission |
| Adm Note | Check | 80 | Red MISSING pill when absent |
| Note Gap (d) | Int | 90 | Days since last progress note; red pill when >1 |
| Intake | Check | 70 | Orange PENDING pill when incomplete |
| Charts OK | Check | 80 | Red OVERDUE pill when charts are overdue |
| Overdue | Int | 70 | Overdue chart count; red pill when >0 |
| Disch Summary | Check | 100 | Red MISSING pill when applicable but absent |
| Score % | Percent | 90 | Color-coded: red <50%, orange 50-74%, green >=75% |

## Chart

Bar chart showing patient count by compliance bucket: 100%, 75-99%, 50-74%, <50%.

## Report Summary

- Total Patients
- Avg Compliance (color-coded indicator)
- Missing Adm Note
- Overdue Progress Notes
- Missing Intake
- Charts Overdue

## Data Source

Uses `documentation_compliance_service.get_documentation_compliance()` which queries Inpatient Record and batches checks against Patient Encounter and IR custom fields.

## Access

- Healthcare Administrator
- Nursing User
