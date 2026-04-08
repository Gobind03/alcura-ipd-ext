# US-B2: Reserve a Bed Before Patient Reaches Hospital

## Purpose

Enable bed management users to reserve a specific bed or hold capacity by room type for a scheduled admission, so the room is held for the intended patient until they arrive or the reservation expires.

## Scope

- New `Bed Reservation` doctype with full lifecycle (Draft / Active / Expired / Cancelled / Consumed)
- Two reservation modes: **Specific Bed** (locks a named bed) and **Room Type Hold** (intent-based capacity hold)
- Race-safe activation using `SELECT … FOR UPDATE` row locks on Hospital Bed
- Scheduler-based auto-expiry (every 5 minutes via `hooks.py` cron)
- Override mechanism requiring Healthcare Administrator role with mandatory audit trail
- Integration with Live Bed Board (reserved beds excluded from available count)

## Reused Standard DocTypes

| DocType | How Used |
|---------|----------|
| Patient | Optional link — patient may not exist at reservation time |
| Healthcare Practitioner | Consulting practitioner reference |
| Healthcare Service Unit Type | Room type dimension for Room Type Hold |
| Customer | Provisional payer for TPA/Corporate reservations |
| Inpatient Record | Link recorded when reservation is consumed by admission |

## Reused Custom DocTypes

| DocType | How Used |
|---------|----------|
| Hospital Bed | Target of Specific Bed reservations; `occupancy_status` extended with "Reserved" |
| Hospital Ward | Ward filter for reservations |
| Hospital Room | Room filter for Specific Bed reservations |
| IPD Bed Policy | Provides `reservation_timeout_minutes` default (120 min) |

## New Custom DocTypes

| DocType | Purpose |
|---------|---------|
| Bed Reservation | Manages bed hold lifecycle with audit trail |

See [docs/doctypes/bed-reservation.md](../doctypes/bed-reservation.md) for full schema.

## Fields Added to Existing DocTypes

| DocType | Field | Change |
|---------|-------|--------|
| Hospital Bed | `occupancy_status` | Added "Reserved" option (was Vacant/Occupied, now Vacant/Occupied/Reserved) |

## Workflow States

See [docs/workflows/bed-reservation-lifecycle.md](../workflows/bed-reservation-lifecycle.md).

| State | Description |
|-------|-------------|
| Draft | Created but not yet holding a bed |
| Active | Bed is held (Specific Bed: bed marked Reserved; Room Type Hold: capacity intent recorded) |
| Expired | Auto-transitioned by scheduler when reservation_end passes |
| Cancelled | Manually cancelled by user or overridden by Healthcare Administrator |
| Consumed | Reservation fulfilled — patient admitted to the reserved bed |

## Permissions

| Role | Create | Read | Write | Delete |
|------|--------|------|-------|--------|
| Healthcare Administrator | Yes | Yes | Yes | Yes |
| Nursing User | Yes | Yes | Yes | No |
| Physician | No | Yes | No | No |

Override cancellation requires Healthcare Administrator role.

## Validation Logic

1. **Type-field coupling**: Specific Bed requires `hospital_bed`; Room Type Hold requires `service_unit_type`
2. **Bed must be Vacant**: Race-safe check with `FOR UPDATE` row lock on activation
3. **No double reservation**: At most one Active reservation per bed
4. **Room type capacity**: At least one available bed of the type must exist (net of existing holds)
5. **Company match**: Bed company must equal reservation company
6. **Valid transitions only**: Draft→Active, Draft→Cancelled, Active→Expired/Cancelled/Consumed
7. **Cancel requires reason**: `cancellation_reason` mandatory
8. **Override requires role and reason**: Healthcare Administrator + `override_reason` mandatory
9. **Consume requires inpatient record**: `consumed_by_inpatient_record` mandatory

## Notifications

- Timeline comment on Bed Reservation for every lifecycle event
- Timeline comment on linked Patient (if set) on activate/cancel/consume
- Realtime event `bed_reservation_expired` pushed to `reserved_by` user on expiry

## Reporting Impact

- **Live Bed Board**: Summary now includes `reserved` count. Reserved beds shown as "Reserved" (purple) when `show_unavailable` filter is active. Excluded from available list by default.
- **Bed Reservation List**: Filterable by status, ward, room type, patient, company

## Test Cases

See [docs/testing/us-b2-bed-reservation.md](../testing/us-b2-bed-reservation.md).

## Open Questions / Assumptions

1. **Room Type Hold is intent-only**: It does not lock any specific bed. The actual bed is allocated at admission time. It only validates that capacity exists.
2. **No Frappe Workflow doctype used**: Status transitions are managed in Python for race safety and finer control.
3. **Scheduler granularity**: Expiry job runs every 5 minutes. Sub-minute precision is not required.
4. **Consuming a reservation is explicit**: It must be called from the admission workflow (future story). The reservation does not auto-consume.
5. **Default timeout from policy**: Each reservation copies the timeout from IPD Bed Policy at creation time but can be adjusted per-reservation.
