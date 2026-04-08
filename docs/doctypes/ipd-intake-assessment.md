# IPD Intake Assessment

## Purpose

Per-admission assessment instance that captures structured responses against an IPD Intake Assessment Template. Links to the Inpatient Record and may have associated scored Patient Assessments.

## Module

Alcura IPD Extensions

## Naming

`naming_series: IPD-IA-.YYYY.-`

## Fields

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| naming_series | Select | Yes | IPD-IA-.YYYY.- |
| patient | Link → Patient | Yes | Indexed |
| inpatient_record | Link → Inpatient Record | Yes | Indexed |
| template | Link → IPD Intake Assessment Template | Yes | Template used |
| template_version | Int | No | Snapshot of template version at creation |
| company | Link → Company | No | Standard filter |
| specialty | Link → Medical Department | No | Indexed |
| assessed_by | Link → Healthcare Practitioner | No | Practitioner performing assessment |
| assessment_datetime | Datetime | Yes | Defaults to now |
| status | Select | No | Draft / In Progress / Completed (indexed) |
| completed_by | Link → User | No | Read-only, set on completion |
| completed_on | Datetime | No | Read-only, set on completion |
| responses | Table → IPD Intake Assessment Response | No | Captured response values |
| amended_from | Link → IPD Intake Assessment | No | For amendment support |

## Child Table: IPD Intake Assessment Response

| Field | Type | Notes |
|-------|------|-------|
| section_label | Data | Section grouping (from template) |
| field_label | Data (required) | Field label (from template) |
| field_type | Data | Field type (from template, read-only) |
| text_value | Small Text | Response for Text/Small Text/Long Text/Select types |
| numeric_value | Float | Response for Int/Float/Rating types |
| check_value | Check | Response for Check type |
| is_mandatory | Check | Whether this field is mandatory (from template, read-only) |

## Workflow

```
Draft  ──[save with data]──→  In Progress  ──[complete]──→  Completed
```

- **Draft → In Progress**: Automatic on first save with any response data
- **In Progress → Completed**: Explicit action; validates all mandatory fields
- **Completed**: Immutable; cannot be modified

## Validations

1. Cannot modify a Completed assessment
2. Completion requires all mandatory response fields to have values
3. One assessment per IR per template (duplicate prevention)

## Audit Fields

- `completed_by`: User who marked the assessment as complete
- `completed_on`: Timestamp of completion
- `template_version`: Version of the template at creation time
- Track changes enabled for full amendment history

## Permissions

| Role | Access |
|------|--------|
| Healthcare Administrator | Full CRUD + Delete |
| Nursing User | Create, Read, Write |
| Physician | Create, Read, Write |
| IPD Admission Officer | Read only |

## Indexes

- `patient`
- `inpatient_record`
- `specialty`
- `status`

## Document Links

- Patient Assessment (via `custom_intake_assessment` back-link) — shows linked scored assessments in sidebar

## US-E2 Enhancements

On completion, the assessment triggers nursing risk flag recalculation on the linked Inpatient Record:

- Allergy data is extracted from "Known Allergies" and "Allergy Details" response fields
- Risk flags (`custom_allergy_alert`, `custom_allergy_summary`) are updated on the IR
- If scored Patient Assessments are also submitted, fall/pressure/nutrition risk levels are computed
- High-risk indicators generate ToDo alerts for nursing staff

See [modules/us-e2-nursing-admission-assessment.md](../modules/us-e2-nursing-admission-assessment.md).

## Related DocTypes

- IPD Intake Assessment Template (template source)
- Patient Assessment (scored assessments linked via custom fields)
- Inpatient Record (parent admission record)
- Patient (patient reference)
