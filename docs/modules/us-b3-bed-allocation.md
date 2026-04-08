# US-B3: Allocate Bed During Admission

## Purpose

Enable IPD admission officers to assign a vacant bed while admitting the patient, so the inpatient stay begins with a traceable, race-safe room allocation linked to the Inpatient Record.

## Scope

- Server-side bed allocation service with transaction-safe locking
- Integration with standard Inpatient Record admission flow
- Bed Reservation consumption (when applicable)
- Bed Movement Log audit trail creation
- Custom fields on Inpatient Record for O(1) location lookup
- Client-side bed picker dialog on Inpatient Record form
- Capacity rollup propagation to room and ward

## Reused Standard DocTypes

| DocType | How Used |
|---------|----------|
| Patient | Patient reference on Inpatient Record |
| Healthcare Practitioner | Future: consulting practitioner reference |
| Inpatient Record | Primary target — status transition from Admission Scheduled to Admitted |
| Inpatient Occupancy | Child table row added to IR linking patient to HSU |
| Healthcare Service Unit | Leaf node representing bed in standard HSU tree |

## Reused Custom DocTypes

| DocType | How Used |
|---------|---------|
| Hospital Bed | Target of allocation; occupancy_status flipped to Occupied |
| Hospital Room | Room reference propagated to IR custom fields |
| Hospital Ward | Ward reference propagated to IR custom fields |
| Bed Reservation | Optionally consumed during allocation |
| IPD Bed Policy | Policy settings for availability filtering |

## New Custom DocTypes

| DocType | Purpose |
|---------|---------|
| Bed Movement Log | Immutable audit record of every bed change (Admission, Transfer, Discharge) |

See [docs/doctypes/bed-movement-log.md](../doctypes/bed-movement-log.md) for full schema.

## Fields Added to Standard DocTypes

| DocType | Field | Type | Notes |
|---------|-------|------|-------|
| Inpatient Record | `custom_current_bed` | Link → Hospital Bed | Read-only, indexed |
| Inpatient Record | `custom_current_room` | Link → Hospital Room | Read-only |
| Inpatient Record | `custom_current_ward` | Link → Hospital Ward | Read-only, indexed |
| Inpatient Record | `custom_admitted_by_user` | Link → User | Read-only |
| Inpatient Record | `custom_last_movement_on` | Datetime | Read-only |

## Workflow States

Not applicable — allocation is a one-shot operation that transitions the IR from "Admission Scheduled" to "Admitted". No intermediate workflow states.

## Permissions

| Component | Roles Required |
|-----------|---------------|
| `allocate_bed` API | Write on Inpatient Record + Read on Hospital Bed |
| `get_available_beds_for_admission` API | Read on Hospital Bed |
| Bed Movement Log creation | Created by service with `ignore_permissions` |

## Validation Logic

1. **IR status check**: Inpatient Record must be in "Admission Scheduled" status
2. **Bed existence**: Hospital Bed must exist
3. **Bed active**: Hospital Bed `is_active` must be true
4. **Bed available**: `occupancy_status` must be "Vacant" (or "Reserved" when a matching reservation is provided)
5. **No maintenance hold**: `maintenance_hold` must be false
6. **No infection block**: `infection_block` must be false
7. **Company match**: Bed company must match IR company
8. **HSU linkage**: Bed must have a linked Healthcare Service Unit
9. **Reservation match**: If reservation is provided and bed is Reserved, the reservation must reference this bed
10. **Race safety**: `SELECT … FOR UPDATE` row lock on Hospital Bed prevents double allocation

## Notifications

- Timeline comment on Inpatient Record with bed/room/ward details
- Timeline comment on Patient record for cross-reference

## Reporting Impact

- **Live Bed Board**: Allocated bed appears as "Occupied" in the bed board
- **Bed Movement Log list**: New Admission entry visible with full audit trail
- **Inpatient Record**: Custom fields show current bed, room, ward

## Architecture

### Service Layer: `services/bed_allocation_service.py`

| Function | Purpose |
|----------|---------|
| `allocate_bed_on_admission(ir, bed, reservation)` | Main entry point — full transactional allocation |
| `_validate_ir_for_admission(ir_doc)` | Status check |
| `_lock_and_validate_bed(bed, ir_doc, reservation)` | FOR UPDATE lock + validation |
| `_mark_bed_occupied(bed)` | Flip occupancy status |
| `_add_inpatient_occupancy(ir_doc, bed_data)` | Add child row to IR |
| `_update_ir_status(ir_doc, bed_data)` | Set Admitted + custom fields |
| `_create_movement_log(ir_doc, bed_data, reservation)` | Audit trail |
| `_consume_reservation(reservation, ir)` | Delegate to reservation service |

### API Layer: `api/admission.py`

| Endpoint | Method |
|----------|--------|
| `alcura_ipd_ext.api.admission.allocate_bed` | Whitelisted — wraps `allocate_bed_on_admission()` |
| `alcura_ipd_ext.api.admission.get_available_beds_for_admission` | Whitelisted — wraps bed availability service |
| `alcura_ipd_ext.api.admission.get_active_reservation_for_patient` | Whitelisted — find active reservation for patient |

### Client Script: `public/js/inpatient_record.js`

- "Allocate Bed" button on Inpatient Record form (visible when status is "Admission Scheduled")
- Bed picker dialog with ward/room type filters and available bed table
- Auto-populates active reservation if found for the patient

## Test Cases

See [docs/testing/us-b3-bed-allocation.md](../testing/us-b3-bed-allocation.md).

## Open Questions / Assumptions

1. **Inpatient Occupancy child table**: The allocation service adds a row to the standard `inpatient_occupancies` child table using the bed's linked HSU. This bridges our custom bed infrastructure with the standard admission pipeline.
2. **HSU sync**: The existing `doc_events` hook on Healthcare Service Unit propagates occupancy changes bidirectionally. The allocation service explicitly syncs HSU after marking the bed occupied.
3. **Reservation consumption is optional**: Walk-in admissions without a prior reservation are fully supported.
4. **IR `admitted_datetime`**: Set to `now()` at allocation time. The standard field is reused rather than creating a custom one.
5. **Custom fields use `custom_` prefix**: Following Frappe 16 convention for custom fields on standard doctypes.
