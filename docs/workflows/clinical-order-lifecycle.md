# Clinical Order Lifecycle Workflow

## Overview

Every IPD Clinical Order follows a standard lifecycle from creation to completion or cancellation. The lifecycle is enforced server-side with strict transition rules.

## States

| State | Description |
|-------|-------------|
| **Draft** | Order created but not yet placed |
| **Ordered** | Order placed, awaiting department acknowledgment |
| **Acknowledged** | Target department has accepted the order |
| **In Progress** | Order is being executed (dispensing, sample collection, etc.) |
| **Completed** | Order fully executed |
| **Cancelled** | Order cancelled (requires reason) |
| **On Hold** | Order temporarily suspended (requires reason) |

## Transition Rules

```
Draft ──→ Ordered ──→ Acknowledged ──→ In Progress ──→ Completed
  │          │              │               │
  │          │              │               ├──→ Cancelled
  │          │              │               └──→ On Hold
  │          │              ├──→ Completed
  │          │              ├──→ Cancelled
  │          │              └──→ On Hold
  │          ├──→ In Progress
  │          ├──→ Cancelled
  │          └──→ On Hold
  └──→ Cancelled

On Hold ──→ Ordered / Acknowledged / In Progress / Cancelled
```

## Audit Fields

Each transition records:
- **Timestamp:** When the transition occurred (`ordered_at`, `acknowledged_at`, etc.)
- **User:** Who performed the transition (`ordered_by`, `acknowledged_by`, etc.)
- **SLA Milestone:** Matching milestone row updated with `actual_at` and `recorded_by`

## SLA Integration

1. **On "Ordered":** SLA milestones initialized from config, `current_sla_target_at` set to first milestone target
2. **On milestone completion:** `current_sla_target_at` advances to next pending milestone
3. **On breach:** `is_sla_breached` flag set, `sla_breach_count` incremented, escalation notification sent

## Notification Events

| Event | Recipients |
|-------|-----------|
| Order Created | Target department role + Nursing User |
| Order Acknowledged | Ordering practitioner |
| Order Completed | Ordering practitioner + Nursing User |
| SLA Breach | Escalation role from SLA config |

## Hold/Resume

- **Hold:** Requires `hold_reason`. Order paused; SLA continues running.
- **Resume:** Clears `hold_reason`, returns to last active state (Ordered or Acknowledged).
