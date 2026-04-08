# US-E5: Doctor Progress Notes and Round Sheets

## Purpose

Enable consultants to efficiently document daily progress notes during ward rounds, with real-time access to active problems, pending labs, due medications, vital signs, alerts, and fluid balance alongside the note entry form. Provide a doctor census view for practitioner-centric patient management.

## Scope

- Add an IPD Problem List Item doctype for tracking evolving clinical problems per admission
- Build a patient round summary data layer aggregating vitals, labs, meds, problems, and alerts
- Create a Doctor Census script report showing all admitted patients for a practitioner
- Show a Patient Round Summary panel on the Patient Encounter form during Progress Note entry
- Add problem list management actions to the Inpatient Record form
- Add "Round Note" shortcut on the Inpatient Record form for fast daily note entry
- Pre-populate progress notes with active problems snapshot
- Update IR with last progress note date and active problem count

## Reused Standard DocTypes

| DocType | How Used |
|---------|----------|
| Patient Encounter | Base document for progress notes (via US-E3 custom fields); extended with US-E5 progress-note-specific fields |
| Inpatient Record | Source for patient location, allergies, risks; extended with problem count and last note date fields |
| Patient | Patient reference |
| Healthcare Practitioner | Practitioner reference for census filtering and problem attribution |
| Medical Department | Department filter on census report |
| Lab Test | Read-only query to detect pending lab tests from encounter prescriptions |
| Lab Prescription | Child table of Patient Encounter queried for pending lab tests |

## New Custom DocTypes

| DocType | Purpose |
|---------|---------|
| IPD Problem List Item | Non-submittable document tracking active clinical problems per admission with severity, ICD code, onset date, and resolution audit trail |

## Fields Added to Standard DocTypes

### Patient Encounter (US-E5 additions)

| Fieldname | Type | Label | Notes |
|-----------|------|-------|-------|
| `custom_progress_note_section` | Section Break | Progress Note Context | Visible only for Progress Notes |
| `custom_active_problems_text` | Small Text | Active Problems | Read-only; snapshot of active problems at note creation |
| `custom_column_break_progress_1` | Column Break | | |
| `custom_overnight_events` | Small Text | Overnight / Interval Events | Events since last round |

### Inpatient Record (US-E5 additions)

| Fieldname | Type | Label | Notes |
|-----------|------|-------|-------|
| `custom_problem_list_section` | Section Break | Problem List & Round Notes | Collapsible |
| `custom_active_problems_count` | Int | Active Problems | Read-only; updated by Problem List Item controller |
| `custom_column_break_problems_1` | Column Break | | |
| `custom_last_progress_note_date` | Date | Last Progress Note | Read-only; updated when progress note is created |

## Workflow States

No formal Frappe Workflow. Problem List Items use a simple status field:
- **Active**: Problem is current and requires attention
- **Monitoring**: Problem is being watched but not actively treated
- **Resolved**: Problem has been addressed; resolution notes and timestamp recorded

Progress Notes follow the standard Patient Encounter docstatus flow (Draft → Submitted → Cancelled).

## Permissions

| Component | Roles Required |
|-----------|---------------|
| Create/Edit IPD Problem List Item | Physician, Healthcare Administrator |
| Read IPD Problem List Item | Physician, Nursing User, Healthcare Administrator |
| Delete IPD Problem List Item | Physician, Healthcare Administrator |
| Doctor Census report | Physician, Healthcare Administrator |
| Round Note creation | Physician, Healthcare Administrator (via PE create permission) |
| Patient Round Summary API | Any role with Inpatient Record read access |

## Validation Logic

1. IPD Problem List Item can only be created/modified when the linked Inpatient Record is in "Admitted" or "Admission Scheduled" status
2. `added_on` is auto-set on insert; `resolved_on` and `resolved_by` are auto-set when status changes to Resolved
3. Re-activating a resolved problem clears the resolution fields
4. Sequence numbers auto-increment for new problems
5. Progress note creation validates the IR status via the existing US-E3 validation pipeline

## Notifications

| Trigger | Action |
|---------|--------|
| Progress Note created | Timeline comment on IR (via US-E3 pipeline) |
| Progress Note submitted | Realtime event `ipd_note_submitted` (via US-E3 pipeline) |
| Problem added/resolved | IR `custom_active_problems_count` updated |
| Progress Note created | IR `custom_last_progress_note_date` updated |

## Reporting Impact

- New report: **Doctor Census** — practitioner-centric view of all admitted patients with summary metrics (problems, days admitted, last note, vitals, overdue charts, allergies)
- Existing report: **IPD Consultation Notes** — Progress Notes appear with note_type filter
- Inpatient Record dashboard shows problem count and last note date
- Problem List Item has its own list view filtered by IR

## Test Cases

See [testing/us-e5-doctor-progress-notes.md](../testing/us-e5-doctor-progress-notes.md).

## Open Questions / Assumptions

1. Problem list is per-admission (per Inpatient Record), not per-patient globally. A new admission starts with a fresh problem list.
2. `custom_active_problems_text` on Patient Encounter is a denormalized snapshot for documentation purposes; the source of truth is IPD Problem List Item.
3. "Pending lab tests" are detected by checking `lab_test_prescription` child rows on submitted encounters linked to the IR, then verifying whether a corresponding submitted Lab Test exists.
4. "Due medications" are MAR entries with `administration_status` in ("Scheduled", "Due", "") for today.
5. The round summary panel is an HTML section injected into the Patient Encounter form, not a sidebar, for tablet-friendliness.
6. Multiple progress notes per day per admission are allowed.
7. The Doctor Census report is the primary "round sheet" view; doctors filter by their name to see all their patients.
8. Problem severity values (Mild/Moderate/Severe) are intentionally simple; ICD coding is optional.
