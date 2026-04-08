# Test Plan: US-F1 through US-F5

## Test Files

| File | Coverage |
|------|----------|
| `tests/test_clinical_order_service.py` | Order creation, validation, status transitions, PE integration, IR counts |
| `tests/test_order_sla_service.py` | SLA initialization, milestone advancement, breach detection |
| `tests/test_order_notification_service.py` | Notification creation, deduplication |
| `tests/test_department_queue.py` | Queue filtering, SLA color bands, empty queues |

## Test Categories

### Order Creation (test_clinical_order_service.py)

- `TestMedicationOrderCreation`
  - Create medication order with all fields
  - STAT order auto-sets urgency
  - PRN requires reason validation
  - Medication name required validation

- `TestLabOrderCreation`
  - Create lab order with template and sample type
  - Lab test name required validation

- `TestProcedureOrderCreation`
  - Create procedure order with body site
  - Create radiology order with urgent urgency

### Status Transitions (test_clinical_order_service.py)

- `TestStatusTransitions`
  - Valid: Ordered → Acknowledged
  - Valid: Acknowledged → Completed (full lifecycle)
  - Invalid: Ordered → Completed (skipping Acknowledged for direct)
  - Cannot transition from terminal status (Completed)
  - Cancellation requires reason
  - Cancel with reason succeeds
  - Hold and resume flow

### IR Counts (test_clinical_order_service.py)

- `TestIROrderCounts`
  - Counts update on order creation

### Validation (test_clinical_order_service.py)

- `TestRejectOnDischargedIR`
  - Order rejected for discharged IR

### SLA (test_order_sla_service.py)

- `TestSLAInitialization`
  - Milestones created from config
  - No config skips SLA gracefully

- `TestSLAAdvancement`
  - Milestone advances SLA target

- `TestBreachDetection`
  - Breach detected when target in past

### Notifications (test_order_notification_service.py)

- `TestOrderNotifications`
  - Notification created on order
  - Deduplication of Administrator

- `TestSLABreachNotification`
  - Breach notification structure

### Queue (test_department_queue.py)

- `TestPharmacyQueue` — returns medication orders, SLA colors, empty queue
- `TestLabQueue` — returns lab orders
- `TestNurseStationQueue` — returns all types
- `TestSLAColorBands` — grey when no target, red when breached

## Running Tests

```bash
cd apps/alcura_ipd_ext
pytest alcura_ipd_ext/tests/test_clinical_order_service.py -v
pytest alcura_ipd_ext/tests/test_order_sla_service.py -v
pytest alcura_ipd_ext/tests/test_order_notification_service.py -v
pytest alcura_ipd_ext/tests/test_department_queue.py -v
```
