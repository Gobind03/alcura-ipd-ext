# US-D2: Admission Checklist — Test Scenarios

## Test File

`alcura_ipd_ext/tests/test_admission_checklist_service.py`

## Test Cases

| # | Test | Description |
|---|------|-------------|
| 1 | `test_create_checklist_from_template` | Creates checklist with all template items as Pending entries |
| 2 | `test_duplicate_checklist_fails` | Cannot create two checklists for the same IR |
| 3 | `test_complete_item` | Completing a Pending item sets user and timestamp |
| 4 | `test_status_becomes_complete` | All mandatory items completed → status = Complete |
| 5 | `test_status_incomplete_with_mandatory_pending` | Status stays Incomplete with pending mandatory items |
| 6 | `test_waive_item_changes_status_to_overridden` | Waiving a mandatory item → Overridden status |
| 7 | `test_cannot_waive_non_overridable` | Waiving non-overridable item raises ValidationError |
| 8 | `test_waive_requires_reason` | Empty reason raises ValidationError |
| 9 | `test_double_complete_fails` | Cannot complete an already-completed item |
| 10 | `test_ir_checklist_link_set` | IR's custom_admission_checklist set after creation |
| 11 | `test_no_template_fails` | No active template → ValidationError |
| 12 | `test_template_duplicate_labels_fail` | Template with duplicate item labels fails validation |

## Coverage Areas

- **Service layer**: template selection, checklist creation, item lifecycle
- **Validation**: uniqueness, override rules, reason requirement, status checks
- **State machine**: Incomplete → Complete, Incomplete → Overridden
- **Data integrity**: IR back-link, audit fields
