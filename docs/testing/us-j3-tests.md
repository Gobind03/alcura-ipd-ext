# US-J3: Housekeeping & Discharge Tests

## Test Files

- `tests/test_housekeeping_service.py` — Housekeeping service tests (pytest)
- `tests/test_discharge_service.py` — Discharge orchestrator tests (pytest)
- `doctype/bed_housekeeping_task/test_bed_housekeeping_task.py` — DocType-level tests (IntegrationTestCase)

## Test Scenarios

### Housekeeping Service Tests

#### TestHousekeepingTaskCreation
- Create standard task — verifies Pending status, SLA > 0
- Infection bed gets isolation clean — verifies cleaning type and higher SLA
- No duplicate active task — prevents two active tasks for same bed

#### TestHousekeepingTransitions
- Start cleaning — verifies In Progress status, bed housekeeping_status sync
- Complete cleaning — verifies Completed status, bed housekeeping_status = Clean, TAT
- Cancel task — verifies Cancelled status
- Invalid transition fails — e.g., start after complete

#### TestHousekeepingSLA
- Breach detection — backdate task, verify sla_breached flag set
- No breach within SLA — verify newly created task not breached

### Discharge Orchestrator Tests

#### TestBedVacate
- Vacate with acknowledged advice — full flow: bed vacant, IR fields cleared
- Vacate creates housekeeping task — verifies task linked to bed
- Vacate without advice still works — edge case for emergency discharge
- Vacate non-admitted fails — expects ValidationError
- Creates movement log — verifies Discharge type, correct from_bed

### DocType Tests (IntegrationTestCase)

- Start and complete cycle — full Pending → In Progress → Completed
- Invalid transition from completed — expects ValidationError
- Turnaround computation — backdate and verify TAT ≥ 29 minutes

## Test Data

Tests create ephemeral Company, Hospital Ward, Hospital Room, Hospital Bed, Patient, Healthcare Practitioner, and Inpatient Record fixtures. Bed fixtures are created with specific occupancy/housekeeping states.
