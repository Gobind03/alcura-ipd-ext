# US-E1: Digital Intake Assessment Forms

## Purpose

Provide specialty-wise, role-specific digital intake assessment forms so that admission assessments are standardised and paperless. Nurses and doctors fill structured forms that link to the inpatient journey, including scored clinical scales (GCS, Pain, Fall Risk, Braden, Nutritional Screening).

## Scope

- Reuse standard Patient Assessment Template / Patient Assessment for scored clinical scales
- Custom IPD Intake Assessment Template with structured multi-section forms
- Per-admission assessment instance linked to Inpatient Record
- Role-based template selection (Nursing User vs Physician)
- Specialty-based template selection via Medical Department
- Template versioning for audit traceability
- Status-driven lifecycle (Draft → In Progress → Completed)
- Auto-creation of linked scored Patient Assessments
- Fixture data for 6 hospital specialties (Medicine, Surgery, ICU, Pediatrics, Obstetrics)
- Script report for tracking assessment completion

## Reused Standard DocTypes

| DocType | How Used |
|---------|----------|
| Patient Assessment Template | Scored clinical scales (GCS, Pain NRS, Morse, Braden, MUST); custom fields added for IPD context |
| Patient Assessment | Scored assessment instances per patient; custom fields link to IR and intake assessment |
| Patient Assessment Parameter | Parameter entries for each standard clinical scale |
| Medical Department | Specialty-based template selection |
| Inpatient Record | 1:N link to intake assessments via custom fields |
| Patient | Patient reference on assessment |
| User | Audit: completed_by |

## New Custom DocTypes

| DocType | Purpose |
|---------|---------|
| IPD Intake Assessment Template | Master template with structured form fields and scored assessment links |
| IPD Intake Template Field | Child table: section-grouped field definitions (label, type, options, mandatory, role visibility) |
| IPD Intake Scored Assessment | Child table: links to Patient Assessment Templates to include |
| IPD Intake Assessment | Per-admission assessment instance with responses |
| IPD Intake Assessment Response | Child table: captured response values per field |

See [doctypes/ipd-intake-assessment-template.md](../doctypes/ipd-intake-assessment-template.md) and [doctypes/ipd-intake-assessment.md](../doctypes/ipd-intake-assessment.md).

## Fields Added to Standard DocTypes

| DocType | Field | Type | Notes |
|---------|-------|------|-------|
| Patient Assessment Template | `custom_specialty` | Link → Medical Department | Specialty association |
| Patient Assessment Template | `custom_assessment_context` | Select | Intake / Monitoring / Discharge |
| Patient Assessment Template | `custom_ipd_sort_order` | Int | Display ordering |
| Patient Assessment Template | `custom_is_ipd_active` | Check | Active for IPD use |
| Patient Assessment | `custom_inpatient_record` | Link → Inpatient Record | IPD linkage (indexed) |
| Patient Assessment | `custom_intake_assessment` | Link → IPD Intake Assessment | Back-link to parent |
| Patient Assessment | `custom_assessment_context` | Data | Fetched from template |
| Inpatient Record | `custom_intake_assessment` | Link → IPD Intake Assessment | Read-only |
| Inpatient Record | `custom_intake_status` | Data | Fetched, read-only |

## Workflow States

| Status | Meaning |
|--------|---------|
| Draft | Assessment created from template, not yet started |
| In Progress | At least one field has been filled |
| Completed | All mandatory fields filled, assessment finalised |

## Permissions

| Component | Roles Required |
|-----------|---------------|
| Manage templates | Healthcare Administrator |
| View templates | Nursing User, Physician, IPD Admission Officer |
| Create/edit assessment | Nursing User, Physician, Healthcare Administrator |
| View assessment | Nursing User, Physician, IPD Admission Officer |
| Delete assessment | Healthcare Administrator only |

## Validation Logic

1. One assessment per Inpatient Record per template (duplicate check on IR + template name)
2. Template must have at least one form field or scored assessment
3. Template field labels must be unique within a section
4. Select fields must have options defined
5. Cannot modify a Completed assessment
6. Cannot complete when mandatory fields are empty
7. Cannot complete an already-completed assessment

## Notifications

- Timeline comment on IR when intake assessment is created
- Timeline comment on IR when assessment is completed

## Reporting Impact

- New report: IPD Intake Assessment Status (filters: company, specialty, status, date range, template)
- Pending assessments visible on Inpatient Record form via banner
- Linked scored assessments shown on IPD Intake Assessment form

## Test Cases

See [testing/us-e1-intake-assessment.md](../testing/us-e1-intake-assessment.md).

## Open Questions / Assumptions

1. Multiple intake assessments per IR are allowed (one nursing + one doctor, for example).
2. Template selection auto-matches on IR's `medical_department` field.
3. Scored Patient Assessments are created as standard docs and back-linked to the intake.
4. Fixture data provides example templates; hospitals customise post-install.
5. Assessment is not submittable — uses status field workflow for in-progress editing.
6. Amendment support deferred to a future version.
7. Role-based field visibility is enforced at the template selection level (separate templates for nurses vs doctors) rather than per-field hiding within a single form.
