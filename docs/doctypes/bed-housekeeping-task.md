# Bed Housekeeping Task

## Overview

Tracks individual bed cleaning jobs triggered by patient discharge, transfer, or manual request. Includes SLA monitoring, cleaning type classification, and turnaround time computation.

## Module

Alcura IPD Extensions

## Naming

`BHT-.#####` (e.g., BHT-00001)

## Key Fields

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| hospital_bed | Link (Hospital Bed) | ✓ | Indexed |
| hospital_room | Link (Hospital Room) | — | Fetched, indexed |
| hospital_ward | Link (Hospital Ward) | — | Fetched, indexed |
| status | Select | — | Pending / In Progress / Completed / Cancelled |
| trigger_event | Select | — | Discharge / Transfer / Manual |
| cleaning_type | Select | — | Standard / Deep Clean / Isolation Clean / Terminal Clean |
| requires_deep_clean | Check | — | Auto-set from bed/ward attributes |
| sla_target_minutes | Int | — | Computed from policy + multipliers |

## Timing Fields

- `created_on` — task creation time
- `started_on` — cleaning start time
- `completed_on` — cleaning completion time
- `turnaround_minutes` — computed: `(completed_on - created_on) / 60`

## SLA Fields

- `sla_target_minutes` — target from policy × multiplier
- `sla_breached` — flagged by scheduler when overdue

## Status Machine

- Pending → In Progress (start_task)
- In Progress → Completed (complete_task)
- Pending/In Progress → Cancelled (cancel_task)
- Completed, Cancelled → terminal states

## Cleaning Type Determination

| Condition | Type | SLA Multiplier |
|-----------|------|----------------|
| Default | Standard | 1.0x base |
| `Hospital Bed.infection_block = 1` | Isolation Clean | `isolation_clean_sla_multiplier` (default 3.0x) |
| Ward `supports_isolation = 1` | Isolation Clean | `isolation_clean_sla_multiplier` |

## Bed State Synchronization

- On `start_task`: `Hospital Bed.housekeeping_status = "In Progress"`
- On `complete_task`: `Hospital Bed.housekeeping_status = "Clean"`, HSU sync, capacity rollup

## Validations

- Only one active (Pending/In Progress) task per bed
- Status transitions enforced server-side

## Controller Methods (Whitelisted)

- `start_task()` — begins cleaning
- `complete_task()` — completes cleaning, updates bed
- `cancel_task()` — cancels task
