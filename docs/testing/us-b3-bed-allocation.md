# US-B3: Bed Allocation — Test Scenarios

## Purpose

Test coverage for the bed allocation service including happy-path allocation, concurrent allocation, reservation consumption, validation failures, capacity rollup, HSU sync, movement log creation, and custom field updates.

## Test File

`alcura_ipd_ext/tests/test_bed_allocation_service.py`

## Test Framework

Frappe `IntegrationTestCase` with `tearDown` rollback pattern. Factory functions create test data (Company, Ward, Room, Bed, Patient, Inpatient Record) following the established pattern from existing tests.

## Test Scenarios

| # | Test Method | Category | What It Validates |
|---|-------------|----------|-------------------|
| 1 | `test_allocate_vacant_bed` | Happy path | Vacant bed allocated, IR transitions to Admitted, bed becomes Occupied, custom fields set |
| 2 | `test_allocate_with_reservation_consumes_it` | Reservation | Active reservation consumed during allocation, reservation status becomes Consumed |
| 3 | `test_double_allocation_fails` | Concurrency | Two allocations on same bed — second fails with ValidationError |
| 4 | `test_allocate_occupied_bed_fails` | Validation | Allocating an already-Occupied bed raises ValidationError |
| 5 | `test_allocate_inactive_bed_fails` | Validation | Allocating an inactive bed raises ValidationError |
| 6 | `test_allocate_company_mismatch_fails` | Validation | Bed company != IR company raises ValidationError |
| 7 | `test_allocate_wrong_ir_status_fails` | Validation | IR not in "Admission Scheduled" raises ValidationError |
| 8 | `test_capacity_updated_after_allocation` | Capacity | Room and ward occupied/available counts updated |
| 9 | `test_movement_log_created_on_allocation` | Audit trail | Bed Movement Log with type=Admission created correctly |
| 10 | `test_inpatient_occupancy_row_added` | Integration | Inpatient Occupancy child row added with correct HSU and check_in |
| 11 | `test_allocate_maintenance_hold_bed_fails` | Validation | Bed under maintenance hold raises ValidationError |

## Running Tests

```bash
# Frappe-style
bench run-tests --app alcura_ipd_ext --module alcura_ipd_ext.tests.test_bed_allocation_service

# pytest
cd apps/alcura_ipd_ext && python -m pytest alcura_ipd_ext/tests/test_bed_allocation_service.py -v
```

## Coverage Areas

- **Unit**: IR status validation, bed availability checks, company match
- **Integration**: Full allocation flow with bed status change, IR status change, occupancy row, movement log
- **Concurrency**: Double allocation prevention via FOR UPDATE locking
- **Permission**: API-level permission checks
- **Edge Cases**: Inactive bed, maintenance hold, company mismatch, wrong IR status

## Not Covered (future stories)

- True multi-process concurrent allocation testing (requires multi-process test harness)
- Browser-level UX testing of the bed picker dialog
- Payer eligibility enforcement during allocation
- Gender restriction enforcement during allocation
