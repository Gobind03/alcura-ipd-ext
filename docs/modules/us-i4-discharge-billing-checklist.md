# US-I4: Discharge Billing Checklist

## Purpose

Provide a final checklist before discharge billing so that no pending service or TPA formality is missed before invoice generation.

## Scope

- Auto-derived checks from live system data
- Manual clearance and waiver with reasons
- Authorized override with audit trail
- Integration with discharge flow

## Reused Standard DocTypes

- Inpatient Record, Patient, Patient Encounter, Payment Entry

## Reused Custom DocTypes

- IPD Clinical Order, IPD Lab Sample, Bed Movement Log, TPA Preauth Request

## New Custom DocTypes

- **Discharge Billing Checklist** — one per Inpatient Record
- **Discharge Checklist Item** — child table for individual checks

## Standard Checks

| Check | Category | Auto-Derived |
|-------|----------|-------------|
| Pending Medication Orders | Clinical | Yes |
| Pending Lab Samples | Clinical | Yes |
| Unposted Procedures | Clinical | Yes |
| Room Rent Closed | Financial | Yes |
| Final Consultant Visit | Clinical | No |
| Discharge Summary Signed | Clinical | Yes |
| TPA Preauth Status | TPA | Yes |
| Deposit Adjustment | Financial | No |

## Workflow States

Pending → In Progress → Cleared / Overridden

## Override

- Requires explicit authorization with reason
- Records override_by, override_datetime, override_reason
- Tracked in audit trail and change log

## Permissions

| Role | Create | Read | Write | Delete |
|------|--------|------|-------|--------|
| Healthcare Administrator | Yes | Yes | Yes | Yes |
| Accounts User | Yes | Yes | Yes | No |
| TPA Desk User | No | Yes | Yes | No |
| Nursing User | No | Yes | No | No |
| Physician | No | Yes | No | No |

## Test Cases

See `docs/testing/us-i4-discharge-billing-checklist.md`
