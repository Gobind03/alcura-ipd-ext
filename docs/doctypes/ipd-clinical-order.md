# DocType: IPD Clinical Order

## Overview

Unified doctype for all inpatient clinical orders — medications, lab tests, radiology investigations, and clinical procedures. Uses an `order_type` discriminator with type-specific field sections.

## Naming

`CO-.YYYY.-.#####` (e.g., CO-2026-00042)

## Status Lifecycle

```
Draft → Ordered → Acknowledged → In Progress → Completed
                                             → Cancelled
                → On Hold ←→ (resume to Ordered/Acknowledged)
```

### Valid Transitions

| From | To |
|------|----|
| Draft | Ordered, Cancelled |
| Ordered | Acknowledged, In Progress, Cancelled, On Hold |
| Acknowledged | In Progress, Completed, Cancelled, On Hold |
| In Progress | Completed, Cancelled, On Hold |
| On Hold | Ordered, Acknowledged, In Progress, Cancelled |
| Completed | (terminal — no transitions) |
| Cancelled | (terminal — no transitions) |

## Key Fields

### Common
- `patient` (Link to Patient, required, indexed)
- `inpatient_record` (Link to Inpatient Record, required, indexed)
- `order_type` (Select: Medication/Lab Test/Radiology/Procedure, required)
- `urgency` (Select: Routine/Urgent/STAT/Emergency, default Routine)
- `status` (Read-only, managed by controller)
- `ordering_practitioner` (Link to Healthcare Practitioner)
- `source_encounter` (Link to Patient Encounter)
- `target_department` (Link to Medical Department)
- `ward`, `room`, `bed` (auto-populated from IR on insert)

### SLA Tracking
- `current_sla_target_at` (Datetime, indexed)
- `is_sla_breached` (Check, indexed)
- `sla_breach_count` (Int)
- `sla_milestones` (Table: IPD Order SLA Milestone)

### Audit Trail
- `ordered_at/by`, `acknowledged_at/by`, `completed_at/by`, `cancelled_at/by`

## Permissions

| Role | Create | Read | Write | Delete |
|------|--------|------|-------|--------|
| Physician | Yes | Yes | Yes | No |
| Nursing User | No | Yes | No | No |
| Healthcare Administrator | Yes | Yes | Yes | Yes |
| Pharmacy User | No | Yes | Yes | No |
| Laboratory User | No | Yes | Yes | No |

## Controller Behavior

- **before_insert:** Auto-populates ward/room/bed from IR
- **validate:** Validates IR status, type-specific required fields, PRN reason, cancellation reason, hold reason
- **after_insert / on_update / on_trash:** Updates IR aggregate order counts
- **transition_to():** Enforces valid status transitions with audit timestamps
