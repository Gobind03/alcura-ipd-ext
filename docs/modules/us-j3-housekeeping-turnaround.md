# US-J3: Vacate Bed and Trigger Housekeeping Turnaround

## Purpose

When a patient is discharged or transferred, the bed transitions from Occupied → Dirty → Cleaning → Available. This story tracks the housekeeping turnaround with SLA monitoring, cleaning type classification, and operations dashboard visibility.

## Scope

- Bed state management on discharge/transfer
- Housekeeping task creation and lifecycle
- SLA monitoring with breach detection and notifications
- Cleaning type determination (Standard, Deep Clean, Isolation Clean, Terminal Clean)
- Operations reporting (Housekeeping TAT Report)
- Hospital Bed form housekeeping action buttons

## Reused Standard DocTypes / Existing Infrastructure

- **Hospital Bed** — `housekeeping_status`, `occupancy_status`, `infection_block` fields
- **IPD Bed Policy** — `auto_mark_dirty_on_discharge`, `cleaning_turnaround_sla_minutes`
- **Bed Movement Log** — `movement_type = "Discharge"`, `source_bed_action`
- **Inpatient Record** — bed field clearing on vacate

## New Custom DocTypes

- **Bed Housekeeping Task** — tracks individual cleaning jobs

## IPD Bed Policy Extensions

- `deep_clean_sla_multiplier` (Float, default 2.0)
- `isolation_clean_sla_multiplier` (Float, default 3.0)

## Housekeeping Task Workflow

| State | Entry Action | Bed Status |
|-------|-------------|------------|
| Pending | Task created on bed vacate | Dirty |
| In Progress | Housekeeping starts cleaning | In Progress |
| Completed | Cleaning finished | Clean |
| Cancelled | Task cancelled | Unchanged |

## Cleaning Type Determination

| Condition | Cleaning Type | SLA Multiplier |
|-----------|--------------|----------------|
| Default | Standard | 1.0x |
| Bed has `infection_block` flag | Isolation Clean | 3.0x |
| Ward has `supports_isolation` flag | Isolation Clean | 3.0x |

## Discharge Orchestrator (`discharge_service.py`)

The `process_bed_vacate()` function coordinates:
1. Validate IR and discharge advice status
2. Lock bed with `SELECT ... FOR UPDATE`
3. Set bed `occupancy_status = Vacant`
4. Apply housekeeping action from policy
5. Create `Bed Movement Log` (type: Discharge)
6. Create `Bed Housekeeping Task` (if dirty)
7. Close Inpatient Occupancy entry
8. Clear IR bed fields
9. Sync HSU occupancy
10. Recompute ward capacity rollup
11. Complete discharge advice
12. Add timeline comments
13. Send notifications

## SLA Monitoring

- Scheduler runs every 15 minutes (`check_housekeeping_sla_breaches`)
- Tasks exceeding SLA target are flagged with `sla_breached = 1`
- Breach notifications sent to Healthcare Administrator and Nursing User roles

## Permissions

| Role | Create | Read | Write | Delete |
|------|--------|------|-------|--------|
| Healthcare Administrator | ✓ | ✓ | ✓ | ✓ |
| Nursing User | ✓ | ✓ | ✓ | — |
| IPD Admission Officer | — | ✓ | — | — |

## Files

| File | Purpose |
|------|---------|
| `doctype/bed_housekeeping_task/bed_housekeeping_task.json` | Schema |
| `doctype/bed_housekeeping_task/bed_housekeeping_task.py` | Controller |
| `doctype/bed_housekeeping_task/bed_housekeeping_task.js` | Client scripts |
| `services/housekeeping_service.py` | Housekeeping lifecycle |
| `services/discharge_service.py` | Discharge orchestrator |
| `report/housekeeping_tat_report/` | TAT Report (script report) |
| `doctype/hospital_bed/hospital_bed.js` | Housekeeping action buttons |
| `doctype/ipd_bed_policy/ipd_bed_policy.json` | SLA multiplier fields |
| `tasks.py` | Scheduler SLA breach check |

## Open Questions / Assumptions

- Housekeeping task assignment to specific users/teams is optional
- Only one active housekeeping task per bed at any time
- Deep clean can be manually triggered by creating a task from the list view
- Terminal Clean uses the same SLA multiplier as Deep Clean
