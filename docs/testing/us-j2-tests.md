# US-J2: Nursing Discharge Tests

## Test Files

- `tests/test_nursing_discharge_service.py` — Service-level tests (pytest)
- `doctype/nursing_discharge_checklist/test_nursing_discharge_checklist.py` — DocType-level tests (IntegrationTestCase)

## Test Scenarios

### Service Tests (pytest)

#### TestNursingChecklistCreation
- Create with standard items — verifies 15 items, 9 mandatory, Pending status
- Reject duplicate checklist — prevents two checklists for same IR
- IR link set — verifies `custom_nursing_discharge_checklist` on IR

#### TestNursingChecklistItemCompletion
- Complete item — verifies Done status, audit fields, In Progress status
- Mark not applicable — verifies Not Applicable status
- Skip with reason — verifies Skipped status and recorded reason
- Skip without reason fails — expects error

#### TestNursingChecklistSignoff
- Signoff blocked with pending mandatory — expects error listing items
- Signoff succeeds when all mandatory done — verifies Completed status and audit
- Verify requires completed — expects ValidationError

### DocType Tests (IntegrationTestCase)

- Checklist has 15 standard items
- Status moves to In Progress on first completion
- Signoff fails with pending mandatory items
- Verify fails before signoff

## Test Data

Tests create ephemeral Company, Patient, and Inpatient Record fixtures.
