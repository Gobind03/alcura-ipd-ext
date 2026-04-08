# Payer Eligibility Check — Status Lifecycle

## Overview

The Payer Eligibility Check uses an explicit `verification_status` field (not a Frappe Workflow DocType) to manage its lifecycle. Status transitions are enforced server-side in the controller.

## States

| Status | Description | Color |
|--------|-------------|-------|
| **Pending** | Check created, awaiting verification from TPA/payer | Orange |
| **Verified** | Payer has confirmed coverage — admission can proceed | Green |
| **Conditional** | Coverage approved with conditions (co-pay, sub-limits, exclusions) | Blue |
| **Rejected** | Payer has denied coverage | Red |
| **Expired** | Previously verified check is no longer valid | Grey |

## Transition Diagram

```
                ┌──────────────────┐
                │     Pending      │
                └──────┬───────────┘
                       │
        ┌──────────────┼───────────────┐
        ▼              ▼               ▼
  ┌──────────┐  ┌─────────────┐  ┌──────────┐
  │ Verified │  │ Conditional │  │ Rejected │
  └────┬─────┘  └──┬──────┬───┘  └────┬─────┘
       │           │      │           │
       │     ┌─────┘      │           │
       │     ▼            ▼           ▼
       │  Verified    Rejected     Pending
       │                          (re-verify)
       ▼
  ┌──────────┐
  │ Expired  │───────► Pending
  └──────────┘        (re-verify)
```

## Transition Rules

| From | To | Who | When |
|------|----|-----|------|
| Pending | Verified | TPA Desk User, Healthcare Administrator | TPA confirms coverage |
| Pending | Conditional | TPA Desk User, Healthcare Administrator | Coverage approved with conditions |
| Pending | Rejected | TPA Desk User, Healthcare Administrator | Coverage denied |
| Conditional | Verified | TPA Desk User, Healthcare Administrator | Conditions met, full approval |
| Conditional | Rejected | TPA Desk User, Healthcare Administrator | Conditions cannot be met |
| Conditional | Expired | TPA Desk User, Healthcare Administrator | Conditional approval expired |
| Verified | Expired | TPA Desk User, Healthcare Administrator | Approval validity lapsed |
| Rejected | Pending | TPA Desk User, Healthcare Administrator | Re-submission for verification |
| Expired | Pending | TPA Desk User, Healthcare Administrator | Re-submission for verification |

## Side Effects on Transition

### Any status change
- `last_status_change_by` and `last_status_change_on` updated
- Timeline comment added to linked Patient
- Timeline comment added to linked Inpatient Record (if set)

### Transition to Verified / Conditional / Rejected
- `verified_by` and `verification_datetime` set

### Transition to Rejected
- In-app notification sent to Healthcare Receptionist and TPA Desk User roles

### Transition to Expired
- In-app notification sent to TPA Desk User role

## Admission Integration

The `enforce_eligibility_verification` setting on IPD Bed Policy controls how eligibility checks affect the admission flow:

| Level | Behavior |
|-------|----------|
| **Strict** | Admission blocked if no Verified/Conditional check exists for non-Cash payers |
| **Advisory** | Warning shown but admission allowed |
| **Ignore** | No eligibility check performed |

Cash payers and admissions without a payer profile are always allowed regardless of enforcement level.
