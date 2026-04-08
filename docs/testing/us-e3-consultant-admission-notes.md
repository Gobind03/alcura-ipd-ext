# US-E3: Consultant Admission Notes — Test Scenarios

## Test File

`alcura_ipd_ext/tests/test_consultation_note_service.py`

## Test Class

`TestConsultationNoteService` (extends `frappe.tests.IntegrationTestCase`)

## Scenarios

### 1. Happy Path: Create Consultation Encounter

**Test:** `test_create_consultation_encounter_happy_path`

- Create an admitted Inpatient Record
- Call `create_consultation_encounter` with note type "Admission Note"
- Assert: encounter is created in draft status
- Assert: `custom_linked_inpatient_record` is set to the IR
- Assert: `custom_ipd_note_type` is "Admission Note"
- Assert: patient, company, practitioner match the IR

### 2. Allergy Pre-population

**Test:** `test_allergy_prepopulation`

- Create an IR with `custom_allergy_summary = "Penicillin, Sulfa drugs"` and `custom_allergy_alert = 1`
- Create consultation encounter
- Assert: `custom_allergies_text` on the encounter contains the allergy summary

### 3. History Pre-population from Intake

**Test:** `test_history_prepopulation_from_intake`

- Create an IR and a completed IPD Intake Assessment with Past Medical History and Past Surgical History responses
- Create consultation encounter
- Assert: `custom_past_history_summary` contains both history entries

### 4. Validation: Note Type Required

**Test:** `test_validation_note_type_required`

- Create an IR
- Construct a Patient Encounter with `custom_linked_inpatient_record` set but `custom_ipd_note_type` empty
- Call `validate_consultation_encounter`
- Assert: raises `frappe.ValidationError`

### 5. Validation: IR Status

**Test:** `test_validation_ir_status`

- Create an IR with status "Discharged"
- Attempt to create a consultation encounter
- Assert: raises `frappe.ValidationError`

### 6. Validation: Chief Complaint for Admission Note

**Test:** `test_validation_chief_complaint_required_for_admission_note`

- Create an IR
- Construct a Patient Encounter with note type "Admission Note" but empty `custom_chief_complaint_text`
- Call `validate_consultation_encounter`
- Assert: raises `frappe.ValidationError`

### 7. On-Submit Timeline Comment

**Test:** `test_on_submit_timeline_comment`

- Create an encounter linked to an IR
- Set chief complaint and note summary
- Call `on_submit_consultation_encounter`
- Assert: a Comment with type "Info" and content containing "submitted" exists on the IR

### 8. Duplicate Admission Note Allowed

**Test:** `test_duplicate_admission_note_allowed`

- Create two admission note encounters for the same IR
- Assert: both succeed without error
- Assert: the two encounters have different names

### 9. Clinical Context API

**Test:** `test_clinical_context_api`

- Create an IR with allergy data and fall risk
- Create a consultation encounter
- Call `get_ipd_clinical_context`
- Assert: returns allergy_alert, allergy_summary, risk flags
- Assert: recent_encounters contains the created encounter

### 10. Practitioner Fallback

**Test:** `test_practitioner_fallback_from_ir`

- Create an IR with a specific practitioner
- Create consultation encounter without specifying practitioner
- Assert: the encounter uses the IR's primary practitioner

### 11. Admission Scheduled IR Valid

**Test:** `test_admission_scheduled_ir_is_valid`

- Create an IR with status "Admission Scheduled"
- Create a consultation encounter
- Assert: succeeds without error

## Coverage Summary

| Area | Covered |
|------|---------|
| Encounter creation (happy path) | Yes |
| IPD field propagation | Yes |
| Allergy pre-population | Yes |
| History pre-population (intake) | Yes |
| Validation: note type required | Yes |
| Validation: IR status check | Yes |
| Validation: chief complaint (admission note) | Yes |
| Timeline comments | Yes |
| Duplicate admission note handling | Yes |
| Clinical context API | Yes |
| Practitioner fallback | Yes |
| Admission Scheduled IR | Yes |

## Known Gaps

- Browser-level E2E tests for IR buttons and encounter form UX
- Multi-user concurrency tests (not critical — encounters do not have race conditions like bed allocation)
- Report `execute()` function test (covered by manual report testing)
- Permission-based tests for Nursing User cannot-create (would require user role setup fixtures)
