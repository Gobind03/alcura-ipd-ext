# US-E1: Intake Assessment — Test Scenarios

## Test File

`alcura_ipd_ext/tests/test_intake_assessment_service.py`

## Test Cases

| # | Test | Description |
|---|------|-------------|
| 1 | `test_select_template_exact_specialty` | Template matching exact specialty is returned |
| 2 | `test_select_template_fallback_to_both` | Falls back to target_role=Both when exact role not found |
| 3 | `test_select_template_returns_none` | Returns None when no active template exists |
| 4 | `test_select_template_inactive_skipped` | Inactive templates are not returned |
| 5 | `test_create_assessment_from_template` | Creates assessment with response rows from template fields |
| 6 | `test_create_assessment_auto_selects_template` | Auto-selects template based on IR medical department |
| 7 | `test_create_assessment_links_to_ir` | IR's custom_intake_assessment set after creation |
| 8 | `test_duplicate_assessment_fails` | Cannot create two assessments for same IR + template |
| 9 | `test_different_templates_allowed` | Different templates for same IR are allowed |
| 10 | `test_no_template_fails` | No active template → ValidationError |
| 11 | `test_save_responses` | Saves response values and transitions to In Progress |
| 12 | `test_save_responses_completed_fails` | Cannot save to a completed assessment |
| 13 | `test_status_draft_to_in_progress` | Status transitions from Draft to In Progress |
| 14 | `test_complete_assessment_success` | Completes when mandatory fields are filled |
| 15 | `test_complete_assessment_missing_mandatory_fails` | Cannot complete with empty mandatory fields |
| 16 | `test_complete_already_completed_fails` | Cannot complete an already-completed assessment |
| 17 | `test_scored_assessments_created` | Scored Patient Assessments auto-created and linked |
| 18 | `test_pending_scored_assessments` | get_pending_scored_assessments returns unsubmitted PAs |
| 19 | `test_template_version_snapshot` | Assessment stores template version at creation |
| 20 | `test_get_assessments_for_ir` | Returns all assessments for an IR |
| 21 | `test_template_requires_content` | Template with no fields/scored fails validation |
| 22 | `test_template_duplicate_field_labels_fail` | Duplicate labels in same section fail |
| 23 | `test_template_select_without_options_fails` | Select without options fails validation |

## Coverage Areas

- **Service layer**: template selection, assessment creation, response saving, completion
- **Validation**: uniqueness, mandatory enforcement, status checks, template structure
- **State machine**: Draft → In Progress → Completed
- **Data integrity**: IR back-link, template version snapshot, audit fields
- **Scored assessment integration**: auto-creation, pending status tracking
- **Template validation**: content requirement, duplicate labels, select options
