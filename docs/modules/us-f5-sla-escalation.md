# US-F5: Escalate Breached SLAs

## Purpose

Automatically escalate delayed orders to nursing supervisors and operations managers with configurable thresholds and notification routing.

## Scope

- Configurable SLA targets per order type and urgency
- Scheduler-driven breach detection every 5 minutes
- Escalation notifications to configured roles
- SLA Breach Report and Order TAT Report

## Configuration Doctype: IPD Order SLA Config

Each config record defines targets for a unique (order_type, urgency) combination:
- Multiple milestones with sequence, target minutes, and escalation role
- Active/inactive toggle for easy management

## Breach Detection Flow

1. Scheduler runs `check_order_sla_breaches()` every 5 minutes
2. Queries orders where `current_sla_target_at < now()` and not in terminal status
3. For each breached order:
   - Marks milestone rows as breached
   - Sets `is_sla_breached = 1` and increments `sla_breach_count`
   - Advances `current_sla_target_at` to next un-breached milestone
   - Sends escalation notification to configured role

## Escalation Notification

- **Type:** Notification Log (Alert) + realtime event
- **Recipients:** Users with the escalation role defined in the SLA config
- **Deduplication:** Checks for existing unread notifications before creating new ones
- **Subject:** Includes order type, order name, breached milestone, and patient name

## Reports

### Order TAT Report
- Filters: Date range, order type, urgency, ward, consultant, status
- Columns: Order, patient, type, urgency, ordered/acknowledged/completed timestamps, TAT, ack TAT, SLA breached flag

### SLA Breach Report
- Filters: Date range, order type, urgency, ward
- Columns: Order, patient, type, urgency, breached milestone, target time, delay minutes
- Groups breached orders by milestone

## Default SLA Targets (Seeded via Patch)

| Type | Urgency | Acknowledged | Next Milestone | Final Milestone |
|------|---------|-------------|----------------|-----------------|
| Medication | STAT | 10 min | 30 min (Dispensed) | — |
| Medication | Routine | 30 min | 120 min (Dispensed) | — |
| Lab Test | STAT | 10 min | 30 min (Sample) | 120 min (Result) |
| Lab Test | Routine | 60 min | 180 min (Sample) | 480 min (Result) |

## Test Cases

- SLA initialization creates correct milestones
- Missing config skips SLA gracefully
- Milestone advancement updates target
- Breach detection marks orders correctly
- Escalation notification sent to correct role
