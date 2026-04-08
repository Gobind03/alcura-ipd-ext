# US-E3: Record Consultant Admission Notes

## Purpose

Enable doctors to document structured consultant admission notes (provisional diagnosis, history, examination, plan, and orders) during the inpatient stay, with clinical context from the admission journey, allergy/risk alerts, and integration with standard order entry.

## Scope

- Extend standard Patient Encounter with IPD clinical documentation fields
- Link encounters to Inpatient Records for chronological note tracking
- Pre-populate allergy and history data from IR and intake assessments
- Show clinical context banner (allergies, risks, bed/ward) on encounter forms
- Provide "Record Admission Note" / "Record Progress Note" actions from IR
- Support note types: Admission Note, Progress Note, Procedure Note, Consultation Note, Discharge Summary
- Script report for IPD consultation note tracking
- Dashboard override on IR to show linked encounters
- Server-side validation for IPD-specific encounter constraints
- Timeline comments on IR when notes are submitted

## Reused Standard DocTypes

| DocType | How Used |
|---------|----------|
| Patient Encounter | Base document for consultant notes; extended with custom fields for IPD clinical sections |
| Inpatient Record | Linked via `custom_linked_inpatient_record`; source for allergy/risk context |
| Patient | Patient reference on encounter |
| Healthcare Practitioner | Practitioner on encounter; fallback from IR `primary_practitioner` |
| Medical Department | Department carried from IR to encounter |
| IPD Intake Assessment | Source for pre-populating history data |
| IPD Intake Assessment Response | History field values extracted for pre-population |

## New Custom DocTypes

None. This story extends existing doctypes via custom fields and hooks only.

## Fields Added to Standard DocTypes

### Patient Encounter

| Fieldname | Type | Label | Notes |
|-----------|------|-------|-------|
| `custom_ipd_consultation_section` | Section Break | IPD Consultation | Collapsible |
| `custom_linked_inpatient_record` | Link -> Inpatient Record | Inpatient Record | Indexed; separate from US-D1 `custom_ipd_inpatient_record` |
| `custom_ipd_note_type` | Select | Note Type | Admission Note / Progress Note / Procedure Note / Consultation Note / Discharge Summary |
| `custom_column_break_consult_1` | Column Break | | |
| `custom_ipd_note_summary` | Small Text | Note Summary | For list view and dashboard display |
| `custom_clinical_history_section` | Section Break | Clinical History | Visible when note type is set |
| `custom_chief_complaint_text` | Small Text | Chief Complaint | Required for Admission Notes |
| `custom_history_of_present_illness` | Text Editor | History of Present Illness | |
| `custom_column_break_history_1` | Column Break | | |
| `custom_past_history_summary` | Small Text | Past History | Combined med/surg/family/social; pre-populated from intake |
| `custom_allergies_text` | Small Text | Known Allergies | Pre-populated from IR allergy data |
| `custom_examination_section` | Section Break | Examination | Visible when note type is set |
| `custom_general_examination` | Text Editor | General Examination | |
| `custom_column_break_exam_1` | Column Break | | |
| `custom_systemic_examination` | Text Editor | Systemic Examination | |
| `custom_assessment_plan_section` | Section Break | Assessment and Plan | Visible when note type is set |
| `custom_provisional_diagnosis_text` | Small Text | Provisional Diagnosis | Narrative; ICD codes go in standard `diagnosis` child table |
| `custom_column_break_plan_1` | Column Break | | |
| `custom_plan_of_care` | Text Editor | Plan of Care | |

## Workflow States

No formal Frappe Workflow. The standard Patient Encounter `docstatus` flow applies:
- Draft (0): Encounter created, doctor fills in clinical sections and orders
- Submitted (1): Notes finalised, orders become active
- Cancelled (2): Standard Frappe cancellation with amendment

Note types are informational labels, not workflow states.

## Permissions

| Component | Roles Required |
|-----------|---------------|
| Create IPD encounter | Physician, Healthcare Administrator |
| View IPD encounters | Physician, Nursing User, Healthcare Administrator |
| Submit IPD encounter | Physician, Healthcare Administrator |
| Record Admission Note button (on IR) | Physician, Healthcare Administrator (via PE create permission) |
| IPD Consultation Notes report | Physician, Nursing User, Healthcare Administrator |

No new roles are created. Permissions are enforced via existing Patient Encounter role permissions and explicit `frappe.has_permission` checks in the API layer.

## Validation Logic

1. If `custom_linked_inpatient_record` is set, `custom_ipd_note_type` must be set
2. Linked Inpatient Record must be in "Admitted" or "Admission Scheduled" status
3. `practitioner` must be set for IPD consultation notes
4. `custom_chief_complaint_text` is required when note type is "Admission Note"
5. Standard Patient Encounter validations (patient, company, etc.) also apply

## Notifications

| Trigger | Action |
|---------|--------|
| Encounter created | Timeline comment on IR: "{Note Type} started by {practitioner}" |
| Encounter submitted | Timeline comment on IR: "{Note Type} submitted by {practitioner} — {summary}" |
| Encounter submitted | `frappe.publish_realtime("ipd_note_submitted", ...)` for nurse station awareness |

## Reporting Impact

- New report: **IPD Consultation Notes** — filters by company, patient, practitioner, department, note type, ward, date range
- Patient Encounter list can be filtered by `custom_ipd_note_type` (standard filter)
- Inpatient Record dashboard shows encounter count badge via dashboard override
- Patient Encounter link on IR dashboard shows "Clinical Notes" group

## Test Cases

See [testing/us-e3-consultant-admission-notes.md](../testing/us-e3-consultant-admission-notes.md).

## Open Questions / Assumptions

1. Multiple encounters per admission are allowed and expected (admission note, daily progress notes, procedure notes, discharge summary).
2. `custom_linked_inpatient_record` is separate from `custom_ipd_inpatient_record` (US-D1) — the former marks encounters created *during* admission, the latter marks the encounter that *ordered* admission.
3. Pre-population of history data looks for standard field labels from the intake assessment fixtures (`_COMMON_DOCTOR_FIELDS`): "Past Medical History", "Past Surgical History", "Drug History", "Family History", "Social History".
4. Order entry uses standard Patient Encounter child tables (drug_prescription, lab_test_prescription, procedure_prescription) — no custom order mechanism.
5. Clinical documentation sections use `depends_on` to only show when `custom_ipd_note_type` is set, keeping the form clean for non-IPD encounters.
6. The "Record Admission Note" button is hidden on the IR form once at least one Admission Note encounter exists for that IR.
7. Progress Notes can be created multiple times without restriction.
8. The report joins Patient Encounter with Inpatient Record to display bed/ward context at the time of query (not historical).
