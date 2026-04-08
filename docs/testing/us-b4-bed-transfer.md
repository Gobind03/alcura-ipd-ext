# US-B4: Bed Transfer — Test Scenarios

## Purpose

Test coverage for the bed transfer service including happy-path transfers, policy-driven source bed handling, concurrent transfers, validation failures, capacity rollup, movement log creation, and Inpatient Occupancy management.

## Test File

`alcura_ipd_ext/tests/test_bed_transfer_service.py`

## Test Framework

Frappe `IntegrationTestCase` with `tearDown` rollback pattern. Uses the allocation service to set up admitted patients before testing transfers.

## Test Scenarios

| # | Test Method | Category | What It Validates |
|---|-------------|----------|-------------------|
| 1 | `test_transfer_between_beds` | Happy path | Source released, dest occupied, IR custom fields updated |
| 2 | `test_transfer_marks_source_dirty` | Policy | Source bed housekeeping_status becomes Dirty with "Mark Dirty" action |
| 3 | `test_transfer_marks_source_vacant_clean` | Policy | Source bed stays Clean with "Mark Vacant" action |
| 4 | `test_double_transfer_to_same_dest_fails` | Concurrency | Two transfers to same destination — second fails |
| 5 | `test_transfer_discharged_patient_fails` | Validation | Transfer after discharge raises ValidationError |
| 6 | `test_transfer_to_occupied_bed_fails` | Validation | Transfer to occupied bed raises ValidationError |
| 7 | `test_transfer_to_maintenance_hold_fails` | Validation | Transfer to maintenance-hold bed raises ValidationError |
| 8 | `test_transfer_wrong_from_bed_fails` | Validation | Mismatched from_bed raises ValidationError |
| 9 | `test_transfer_same_bed_fails` | Validation | Source = destination raises ValidationError |
| 10 | `test_capacity_updated_for_both_rooms` | Capacity | Both source and destination room/ward counts updated |
| 11 | `test_movement_log_created_on_transfer` | Audit trail | Bed Movement Log with type=Transfer, from/to populated |
| 12 | `test_inpatient_occupancy_rows_updated` | Integration | Old occupancy marked left with check_out, new one created |
| 13 | `test_transfer_without_reason_fails` | Validation | Empty reason raises ValidationError |

## Running Tests

```bash
# Frappe-style
bench run-tests --app alcura_ipd_ext --module alcura_ipd_ext.tests.test_bed_transfer_service

# pytest
cd apps/alcura_ipd_ext && python -m pytest alcura_ipd_ext/tests/test_bed_transfer_service.py -v
```

## Coverage Areas

- **Unit**: IR status validation, bed availability checks, source bed action resolution
- **Integration**: Full transfer flow with dual bed status changes, IR occupancy row management, movement log, capacity rollup
- **Concurrency**: Double transfer prevention via FOR UPDATE locking
- **Policy**: Source bed housekeeping action variants (Mark Dirty, Mark Vacant, No Change)
- **Edge Cases**: Same bed, wrong from_bed, discharged patient, maintenance hold

## Not Covered (future stories)

- True multi-process concurrent deadlock testing (requires multi-process test harness)
- Cross-transfer (A→B and B→A simultaneously) testing
- Gender restriction enforcement on destination bed
- Browser-level UX testing of the transfer dialog
- Approval workflow for cross-department transfers
