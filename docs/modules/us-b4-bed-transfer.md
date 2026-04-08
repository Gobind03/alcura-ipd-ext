# US-B4: Transfer Patient Between Rooms/Wards

## Purpose

Enable nursing supervisors to transfer a patient from one bed to another (within or across wards) without losing the audit trail, so clinical and operational needs can be handled with full traceability and billing integration readiness.

## Scope

- Server-side transfer service with deadlock-free dual bed locking
- Policy-driven source bed housekeeping handling
- Inpatient Occupancy management (mark old as left, add new)
- Bed Movement Log audit trail (type=Transfer)
- Destination eligibility validation
- Client-side transfer dialog on Inpatient Record form
- Capacity rollup for both source and destination rooms/wards

## Reused Standard DocTypes

| DocType | How Used |
|---------|----------|
| Patient | Patient reference on timeline comments |
| Inpatient Record | Status validation (must be Admitted), occupancy row management |
| Inpatient Occupancy | Old row marked left, new row added |
| Healthcare Service Unit | Leaf node for destination bed |
| Healthcare Practitioner | Optional ordering practitioner reference |

## Reused Custom DocTypes

| DocType | How Used |
|---------|---------|
| Hospital Bed | Source and destination beds — occupancy status changes |
| Hospital Room | Room reference for capacity rollup |
| Hospital Ward | Ward reference for capacity rollup |
| IPD Bed Policy | `auto_mark_dirty_on_discharge` determines default source bed action |
| Bed Movement Log | Audit record created with type=Transfer |

## New Custom DocTypes

None. US-B4 reuses the Bed Movement Log created in US-B3.

## Fields Added to Standard DocTypes

None beyond those added in US-B3. The `custom_current_bed`, `custom_current_room`, `custom_current_ward`, and `custom_last_movement_on` fields are updated on each transfer.

## Workflow States

Not applicable — transfer is a one-shot operation. The Inpatient Record remains in "Admitted" status throughout.

## Permissions

| Component | Roles Required |
|-----------|---------------|
| `transfer_patient` API | Write on Inpatient Record + Read on Hospital Bed |
| Bed Movement Log creation | Created by service with `ignore_permissions` |

## Validation Logic

1. **IR status**: Must be "Admitted"
2. **Source bed match**: `from_bed` must match `custom_current_bed` on the IR
3. **Source bed occupied**: Source bed `occupancy_status` must be "Occupied"
4. **Destination bed vacant**: `occupancy_status` must be "Vacant"
5. **Destination active**: `is_active` must be true
6. **No maintenance hold**: Destination `maintenance_hold` must be false
7. **No infection block**: Destination `infection_block` must be false
8. **Company match**: Destination bed company must match IR company
9. **HSU linkage**: Destination bed must have a linked Healthcare Service Unit
10. **Not same bed**: Source and destination cannot be the same
11. **Reason required**: Transfer reason is mandatory
12. **Deadlock prevention**: Beds locked in alphabetical name order

## Notifications

- Timeline comment on Inpatient Record with source/destination bed details and reason
- Timeline comment on Patient record for cross-reference

## Reporting Impact

- **Live Bed Board**: Source bed appears as Vacant (or Dirty), destination as Occupied
- **Bed Movement Log list**: New Transfer entry with from/to beds and reason
- **Inpatient Record**: Custom fields updated to reflect new bed location

## Architecture

### Service Layer: `services/bed_transfer_service.py`

| Function | Purpose |
|----------|---------|
| `transfer_patient(ir, from_bed, to_bed, reason, ...)` | Main entry point — full transactional transfer |
| `_validate_ir_for_transfer(ir_doc, from_bed)` | Status + current bed check |
| `_lock_beds_ordered(from_bed, to_bed)` | Deadlock-free dual FOR UPDATE locking |
| `_validate_source_bed(from_data, ir_doc)` | Source is Occupied |
| `_validate_destination_bed(to_data, ir_doc)` | Destination eligibility |
| `_resolve_source_bed_action(explicit, policy)` | Determine housekeeping action |
| `_apply_source_bed_action(bed, action)` | Mark Dirty / Mark Vacant / No Change |
| `_update_inpatient_occupancies(ir_doc, from, to)` | Mark old left, add new |
| `_create_movement_log(...)` | Audit trail |

### API Layer: `api/admission.py`

| Endpoint | Method |
|----------|--------|
| `alcura_ipd_ext.api.admission.transfer_patient` | Whitelisted — derives from_bed from IR, delegates to service |

### Client Script: `public/js/inpatient_record.js`

- "Transfer Bed" button on Inpatient Record form (visible when status is "Admitted")
- Transfer dialog showing current bed info, destination bed picker, reason input, and source bed action selector

## Test Cases

See [docs/testing/us-b4-bed-transfer.md](../testing/us-b4-bed-transfer.md).

## Open Questions / Assumptions

1. **Deadlock-free locking**: Beds are always locked in alphabetical name order. If two concurrent transfers try A→B and B→A, both will acquire locks in the same order (A first, then B), preventing deadlocks.
2. **Source bed action defaults**: The default action comes from `IPD Bed Policy.auto_mark_dirty_on_discharge`. If enabled, source beds are marked Dirty; otherwise they stay Clean. The user can override per-transfer.
3. **Billing integration readiness**: The Inpatient Occupancy rows with `check_in` and `check_out` timestamps provide the foundation for differential room rent billing. The actual billing is a future story.
4. **Cross-ward transfers**: Fully supported. Both source and destination rooms/wards get capacity recalculated.
5. **No approval workflow yet**: Transfers are immediate. A future story may add an approval step for cross-department transfers requiring physician sign-off.
