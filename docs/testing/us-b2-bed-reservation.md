# US-B2: Bed Reservation — Test Scenarios

## Purpose

Test coverage for the Bed Reservation feature including creation, activation, cancellation, expiry, consumption, override, race safety, status transitions, and bed board integration.

## Test File

`alcura_ipd_ext/alcura_ipd_ext/doctype/bed_reservation/test_bed_reservation.py`

## Test Framework

Frappe `IntegrationTestCase` with `tearDown` rollback pattern. Factory functions create test data (Company, Ward, Room, Bed, Reservation) following the established pattern from `test_hospital_bed.py`.

## Test Scenarios

| # | Test Method | Category | What It Validates |
|---|-------------|----------|-------------------|
| 1 | `test_create_specific_bed_reservation` | Creation | Draft creation with all required fields; auto-computed end time; room/ward inherited from bed |
| 2 | `test_activate_specific_bed_sets_bed_reserved` | Activation | Activate flips bed occupancy_status to "Reserved"; sets reserved_by and reserved_on |
| 3 | `test_activate_room_type_hold` | Activation | Room Type Hold activates without changing any specific bed status |
| 4 | `test_cannot_activate_on_occupied_bed` | Validation | Activation fails with ValidationError when bed is Occupied |
| 5 | `test_cannot_activate_on_already_reserved_bed` | Validation | Activation fails when bed is already Reserved |
| 6 | `test_cannot_double_reserve_same_bed` | Race Safety | Two reservations on same bed — second activation fails |
| 7 | `test_cancel_reservation_resets_bed` | Cancellation | Cancel sets bed back to Vacant; records audit fields |
| 8 | `test_cancel_requires_reason` | Validation | Cancellation without reason throws ValidationError |
| 9 | `test_expire_reservation_resets_bed` | Expiry | Scheduler job resets bed to Vacant; records expired_on |
| 10 | `test_expire_skips_non_overdue` | Expiry | Scheduler ignores reservations not yet past end time |
| 11 | `test_consume_reservation` | Consumption | Consuming links to Inpatient Record; sets consumed_on |
| 12 | `test_consume_requires_inpatient_record` | Validation | Consuming without inpatient record throws ValidationError |
| 13 | `test_override_requires_admin_role` | Permissions | Non-admin (Nursing User) cannot override |
| 14 | `test_override_records_audit_trail` | Override | Override sets is_override, override_authorized_by, override_reason |
| 15 | `test_invalid_status_transition` | State Machine | Draft→Consumed, Draft→Expired, Expired→Active all throw ValidationError |
| 16 | `test_auto_computed_reservation_end` | Computation | End = start + timeout_minutes |
| 17 | `test_company_mismatch_blocked` | Validation | Bed company != reservation company throws ValidationError |
| 18 | `test_capacity_rollup_after_expiry` | Integration | Ward/room available_beds counts correct after expiry releases bed |
| 19 | `test_bed_board_shows_reserved_count` | Integration | `get_bed_board_summary` returns `reserved` count |
| 20 | `test_reserved_bed_excluded_from_available` | Integration | `get_available_beds` does not include reserved beds |

## Running Tests

```bash
# Frappe-style (discovers doctype tests)
bench run-tests --app alcura_ipd_ext --doctype "Bed Reservation"

# pytest (if testpaths configured to include doctype tests)
cd apps/alcura_ipd_ext && python -m pytest alcura_ipd_ext/alcura_ipd_ext/doctype/bed_reservation/test_bed_reservation.py -v
```

## Coverage Areas

- **Unit**: Status transition validation, reservation end computation
- **Integration**: Bed status changes, capacity rollup, bed board summary/available queries
- **Permission**: Override requires Healthcare Administrator role
- **Edge Cases**: Double reservation, company mismatch, expired vs non-expired, empty reason

## Not Covered (future stories)

- True concurrent thread-level race testing (requires multi-process test harness)
- Full admission flow consuming a reservation (depends on admission story)
- Realtime notification delivery assertion
- Browser-level UX testing of action buttons
