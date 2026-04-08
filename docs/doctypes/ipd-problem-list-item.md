# DocType: IPD Problem List Item

## Purpose

Tracks active clinical problems per inpatient admission. Enables doctors to maintain an evolving problem list during rounds, with severity grading, ICD coding, and resolution audit trail.

## Module

Alcura IPD Extensions

## Naming

Auto-named via naming series `IPP-.#####`.

## Key Fields

| Fieldname | Type | Required | Indexed | Notes |
|-----------|------|----------|---------|-------|
| patient | Link → Patient | Yes | Yes | Auto-populated from IR |
| inpatient_record | Link → Inpatient Record | Yes | Yes | Admission this problem belongs to |
| company | Link → Company | Yes | No | Auto-populated from IR |
| status | Select | No | Yes | Active / Resolved / Monitoring (default: Active) |
| severity | Select | No | No | Mild / Moderate / Severe |
| sequence_number | Int | No | No | Priority ordering (lower = higher priority) |
| problem_description | Small Text | Yes | No | Free-text problem description |
| onset_date | Date | No | No | When the problem started |
| icd_code | Data | No | No | Optional ICD-10 code |
| added_by | Link → Healthcare Practitioner | No | No | Read-only; auto-set on insert |
| added_on | Datetime | No | No | Read-only; auto-set on insert |
| resolved_by | Link → Healthcare Practitioner | No | No | Read-only; set when resolved |
| resolved_on | Datetime | No | No | Read-only; set when resolved |
| resolution_notes | Small Text | No | No | Visible when status is Resolved |

## Permissions

| Role | Read | Write | Create | Delete |
|------|------|-------|--------|--------|
| Physician | Yes | Yes | Yes | Yes |
| Nursing User | Yes | No | No | No |
| Healthcare Administrator | Yes | Yes | Yes | Yes |

## Controller Behavior

- **before_insert**: Sets `added_on` to now, resolves `added_by` from session user's linked practitioner
- **validate**: Checks IR is in Admitted/Admission Scheduled status; handles resolution field lifecycle
- **after_insert / on_update / on_trash**: Updates `custom_active_problems_count` on the linked Inpatient Record

## Client Script

- "Resolve" button shown on Active problems, opens dialog for resolution notes
- Setting `inpatient_record` auto-fetches `patient` and `company`

## Relationships

- Belongs to: Inpatient Record (many-to-one)
- Referenced by: Patient Encounter `custom_active_problems_text` (snapshot)
- Feeds: Doctor Census report, Patient Round Summary API

## Sorting

Default sort: `sequence_number ASC` (lower numbers = higher priority).
