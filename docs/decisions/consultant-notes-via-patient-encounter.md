# ADR: Consultant Admission Notes via Patient Encounter

## Status

Accepted

## Context

US-E3 requires structured consultant admission notes capturing provisional diagnosis, history, examination, plan, and orders, linked to the inpatient stay. The standard Healthcare module provides:

- **Patient Encounter**: submittable document with child tables for diagnosis (ICD-coded), drug prescriptions, lab tests, procedures, and therapies. Has `encounter_comment` free-text field but no structured clinical documentation sections.
- **Clinical Note** (not present in Marley Health): no standard doctype for IPD clinical notes.
- **IPD Intake Assessment** (US-E1 custom): structured multi-section intake forms with doctor fields (HPI, examination, diagnosis, plan) — but designed as a one-time admission intake, not for ongoing encounter-based documentation.

IPD consultant notes require:
- Structured clinical sections (Chief Complaint, HPI, Past History, Examination, Assessment & Plan)
- Order entry integration (medications, labs, procedures)
- Chronological encounter-based documentation (admission note, progress notes, discharge summary)
- Patient timeline integration
- Link to the Inpatient Record
- Audit trail (submittable, owner/modifier tracked)

## Decision

**Extend the standard Patient Encounter with custom fields for IPD clinical documentation.**

1. **Reuse** Patient Encounter as the base document. It already provides:
   - Submittable workflow with audit trail (`docstatus`, `owner`, `modified_by`, `creation`)
   - Child tables for diagnosis, drug prescriptions, lab tests, procedures, therapies
   - Patient timeline integration (encounters appear automatically)
   - Links to Patient, Healthcare Practitioner, Medical Department
   - Company-scoped multi-tenancy

2. **Add custom fields** for:
   - IPD context: `custom_ipd_note_type` (Admission Note / Progress Note / etc.) and `custom_linked_inpatient_record` (Link to IR)
   - Clinical documentation sections: Chief Complaint, HPI, Past History, Allergies, General Examination, Systemic Examination, Provisional Diagnosis, Plan of Care, Note Summary
   - All clinical sections use `depends_on` to show only when the encounter is an IPD note

3. **Separate from US-D1 linking**: The existing `custom_ipd_inpatient_record` field marks the encounter that *ordered* admission (one-to-one). The new `custom_linked_inpatient_record` field marks encounters created *during* the admission (many-to-one). These serve different purposes and should remain separate fields.

## Alternatives Considered

### A. Create a custom "IPD Consultant Note" doctype

Rejected because:
- Would duplicate Patient Encounter's prescription child tables (drug, lab, procedure)
- Would need to replicate the submittable workflow and audit trail
- Would not appear automatically in the patient timeline
- Would not integrate with standard Healthcare reports and features
- Violates the "reuse standard doctypes first" constraint

### B. Use IPD Intake Assessment for consultant notes

Rejected because:
- Intake Assessment is designed for one-time structured intake, not ongoing encounters
- It uses a response-based model (label/value pairs) rather than named fields
- It does not have order entry child tables
- Creating multiple intake assessments per admission would conflate intake with clinical documentation

### C. Override Patient Encounter class to add methods

Rejected because:
- `override_doctype_class` is invasive and risks conflicts with other apps
- Custom fields + `doc_events` hooks achieve the same result with better isolation
- Consistent with the existing app pattern (US-D1 uses custom fields + doc_events)

## Consequences

**Positive:**
- Full reuse of Patient Encounter's order entry pipeline (prescriptions, lab orders, procedures)
- Automatic patient timeline integration
- Submittable workflow with complete audit trail
- Consistent with existing app patterns (US-D1)
- Clean app isolation via custom fields and hooks
- Multiple note types per admission without new doctypes

**Negative:**
- ~18 custom fields added to Patient Encounter (mitigated by `depends_on` visibility control)
- Clinical documentation sections are not visible for non-IPD encounters (by design)
- Patient Encounter list may show both OPD and IPD encounters — mitigated by `custom_ipd_note_type` filter

## Related Documents

- [modules/us-e3-consultant-admission-notes.md](../modules/us-e3-consultant-admission-notes.md)
- [modules/us-d1-admission-order.md](../modules/us-d1-admission-order.md)
- [decisions/intake-assessment-vs-standard-pat.md](intake-assessment-vs-standard-pat.md)
