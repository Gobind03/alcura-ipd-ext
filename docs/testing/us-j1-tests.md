# US-J1: Discharge Advice Tests

## Test Files

- `tests/test_discharge_advice_service.py` — Service-level tests (pytest)
- `doctype/ipd_discharge_advice/test_ipd_discharge_advice.py` — DocType-level tests (IntegrationTestCase)

## Test Scenarios

### Service Tests (pytest)

#### TestDischargeAdviceCreation
- Create discharge advice for admitted patient — verifies Advised status, audit fields
- Reject for non-admitted patient — expects ValidationError
- Reject duplicate active advice — prevents two active advices for same IR

#### TestDischargeAdviceTransitions
- Acknowledge from Advised — verifies Acknowledged status and audit
- Complete from Acknowledged — verifies Completed status and actual datetime
- Cancel with reason — verifies Cancelled status and recorded reason
- Cancel without reason fails — expects error

#### TestDischargeStatus
- Aggregate status with no advice — returns None/False
- Aggregate status with advice — returns correct structure

### DocType Tests (IntegrationTestCase)

- submit_advice transitions to Advised
- Cannot transition from Completed (terminal state)
- Cancellation requires reason
- Cannot create for non-admitted IR

## Test Data

Tests create ephemeral Company, Patient, Healthcare Practitioner, and Inpatient Record fixtures. Database rollback ensures isolation via `conftest.py` savepoint mechanism.
