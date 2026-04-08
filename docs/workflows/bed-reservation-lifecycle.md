# Bed Reservation Lifecycle

## Purpose

Documents the status-driven lifecycle of the Bed Reservation doctype. No Frappe Workflow (the DocType feature) is used — transitions are managed in Python for race safety and finer control.

## State Diagram

```
                    ┌─────────┐
                    │  Draft  │
                    └────┬────┘
                         │
              ┌──────────┼──────────┐
              ▼                     ▼
        ┌──────────┐         ┌───────────┐
        │  Active  │         │ Cancelled │ (terminal)
        └────┬─────┘         └───────────┘
             │
    ┌────────┼────────┐
    ▼        ▼        ▼
┌─────────┐ ┌──────────┐ ┌──────────┐
│ Expired │ │Cancelled │ │ Consumed │
│(terminal)│ │(terminal)│ │(terminal)│
└─────────┘ └──────────┘ └──────────┘
```

## Valid Transitions

| From | To | Trigger | Actor |
|------|----|---------|-------|
| Draft | Active | User clicks "Activate Reservation" | Nursing User, Healthcare Administrator |
| Draft | Cancelled | User clicks "Cancel Reservation" | Nursing User, Healthcare Administrator |
| Active | Expired | Scheduler job (`expire_bed_reservations`) | System (cron every 5 min) |
| Active | Cancelled | User clicks "Cancel Reservation" or "Override & Cancel" | Any authorized user; override requires Healthcare Administrator |
| Active | Consumed | Admission workflow calls `action_consume()` | Nursing User, Healthcare Administrator |

## Invalid Transitions (blocked by server)

- Draft → Expired
- Draft → Consumed
- Expired → any
- Cancelled → any
- Consumed → any

## Activation (Draft → Active)

### Specific Bed

1. Acquire row lock on Hospital Bed (`SELECT … FOR UPDATE`)
2. Verify bed is Vacant
3. Verify no other Active reservation exists for the same bed
4. Set `Hospital Bed.occupancy_status` = "Reserved"
5. Recompute room/ward capacity
6. Record `reserved_by`, `reserved_on`
7. Add timeline comment

### Room Type Hold

1. Count vacant beds of the requested type (accounting for buffer beds per policy)
2. Subtract count of existing active Room Type Hold reservations for the same type
3. Verify effective available > 0
4. Record `reserved_by`, `reserved_on`
5. Add timeline comment

## Cancellation (Active → Cancelled)

1. Record `cancelled_by`, `cancelled_on`, `cancellation_reason`
2. If Specific Bed: reset `Hospital Bed.occupancy_status` to "Vacant", recompute capacity
3. If override: verify Healthcare Administrator role, record `is_override`, `override_authorized_by`, `override_reason`
4. Add timeline comment

## Expiry (Active → Expired)

Triggered by scheduler job `alcura_ipd_ext.tasks.expire_bed_reservations` (cron `*/5 * * * *`).

1. Query all Active reservations where `reservation_end < NOW()`
2. For each, acquire row lock on the reservation
3. If Specific Bed: reset bed to Vacant, recompute capacity
4. Record `expired_on`
5. Add timeline comment
6. Send realtime notification to `reserved_by` user

## Consumption (Active → Consumed)

Called from the admission workflow when a patient is admitted to the reserved bed.

1. Verify `inpatient_record` is provided
2. Record `consumed_on`, `consumed_by_inpatient_record`
3. Add timeline comment

## Audit Fields

| Field | Set By | When |
|-------|--------|------|
| reserved_by | System (session user) | Activation |
| reserved_on | System (now) | Activation |
| cancelled_by | System (session user) | Cancellation |
| cancelled_on | System (now) | Cancellation |
| cancellation_reason | User input | Cancellation |
| is_override | System | Override cancellation |
| override_authorized_by | System (session user) | Override cancellation |
| override_reason | User input | Override cancellation |
| expired_on | System (now) | Expiry |
| consumed_on | System (now) | Consumption |
| consumed_by_inpatient_record | User/system input | Consumption |

## Race Safety

The critical section during activation of a Specific Bed reservation uses MariaDB row-level locking:

1. `SELECT occupancy_status FROM tabHospital Bed WHERE name = %(bed)s FOR UPDATE` — locks the bed row
2. Check `occupancy_status = 'Vacant'`
3. `SELECT name FROM tabBed Reservation WHERE hospital_bed = %(bed)s AND status = 'Active' FOR UPDATE` — locks any existing reservation
4. Check no existing active reservation
5. `UPDATE tabHospital Bed SET occupancy_status = 'Reserved'`

This prevents two concurrent transactions from both seeing the bed as Vacant and both succeeding.
