# Discharge Journey Workflow

## Overview

The discharge journey coordinates three interconnected workflows that take a patient from discharge advice through clinical closure to bed availability.

## Flow Diagram

```
Doctor raises                  Nursing acknowledges
Discharge Advice  ──────────►  and starts checklist
   (US-J1)                        (US-J2)
       │                              │
       ▼                              ▼
  Billing Checklist           Nursing Checklist
  starts (existing)           15 items completed
       │                              │
       └──────────┬───────────────────┘
                  ▼
            Bed Vacated (US-J3)
                  │
                  ├── Movement Log created
                  ├── Bed marked Dirty
                  ├── Housekeeping Task created
                  ├── IR bed fields cleared
                  └── Capacity rollup updated
                  │
                  ▼
         Housekeeping Cleaning
                  │
                  ├── Start Cleaning (status: In Progress)
                  └── Complete Cleaning (status: Clean, bed Available)
```

## Status Machines

### Discharge Advice (IPD Discharge Advice)

```
Draft → Advised → Acknowledged → Completed
                                      ↓
Draft → Cancelled   Advised → Cancelled
```

### Nursing Checklist (Nursing Discharge Checklist)

```
Pending → In Progress → Completed (via signoff)
                                 → Verified (optional)
```

### Housekeeping Task (Bed Housekeeping Task)

```
Pending → In Progress → Completed
          → Cancelled
```

### Bed Status (Hospital Bed.housekeeping_status)

```
Clean → Dirty (on discharge) → In Progress (cleaning started) → Clean (cleaning completed)
```

## Integration Points

1. **Discharge Advice → Nursing Checklist**: Nursing checklist can be created after advice is raised, linked via `discharge_advice` field
2. **Discharge Advice → Billing Checklist**: Billing checklist exists independently but is checked in aggregate status
3. **Bed Vacate → Housekeeping Task**: Automatically created when bed is vacated with `auto_mark_dirty_on_discharge` policy
4. **Housekeeping Task → Bed Status**: Task completion transitions bed from Dirty/In Progress to Clean
5. **All → Inpatient Record**: Combined discharge status banner on IR form

## Aggregate Discharge Status

The `get_discharge_status` API returns a unified view:

```json
{
  "advice": {"name": "DDA-2026-00001", "status": "Acknowledged"},
  "billing_checklist": {"name": "DBC-2026-00001", "status": "Cleared"},
  "nursing_checklist": {"name": "NDC-2026-00001", "status": "Completed"},
  "ready_to_vacate": true
}
```

`ready_to_vacate` is `true` when:
- Advice is Acknowledged or Completed
- Billing checklist is Cleared or Overridden
- Nursing checklist is Completed

## Notifications

| Event | Recipients | Method |
|-------|-----------|--------|
| Advice submitted | Nursing, Billing, Pharmacy, TPA (non-cash) | In-app + realtime |
| Advice acknowledged | Advising consultant | In-app |
| Bed vacated | Admission officers, Nursing | In-app + realtime |
| Housekeeping SLA breach | Healthcare Admin, Nursing | In-app (alert) |

## Scheduler

- `check_housekeeping_sla_breaches()` runs every 15 minutes
- Flags overdue tasks and sends breach notifications
