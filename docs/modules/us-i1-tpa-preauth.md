# US-I1: Initiate Pre-Authorization Workflow

## Purpose

Enable TPA coordinators to raise pre-authorization requests linked to inpatient admissions and major procedures, ensuring payer approvals are documented before high-value care.

## Scope

- Create TPA Preauth Request from admission or procedure context
- Full lifecycle management: Draft through Closed
- Communication trail with attachments
- Audit fields for every status change
- Notifications to TPA desk and physician roles

## Reused Standard DocTypes

- Patient
- Healthcare Practitioner
- Medical Department
- Healthcare Service Unit Type
- Inpatient Record
- Insurance Payor
- Patient Insurance Policy

## Reused Custom DocTypes

- Patient Payer Profile
- IPD Clinical Order (integration trigger)
- Payer Eligibility Check (complementary, not replaced)

## New Custom DocTypes

- **TPA Preauth Request** — main lifecycle document
- **TPA Preauth Response** — child table for query/response trail

## Fields Added

### Custom fields on Inpatient Record

| Field | Type | Purpose |
|-------|------|---------|
| custom_preauth_request | Link (TPA Preauth Request) | Primary preauth reference |
| custom_preauth_status | Data (fetched) | Display current preauth status |

## Workflow States

```
Draft → Submitted → Query Raised → Resubmitted → Approved / Partially Approved / Rejected → Closed
```

- Rejected can also transition back to Submitted (resubmission)
- Query Raised / Resubmitted can cycle

## Permissions

| Role | Create | Read | Write | Delete |
|------|--------|------|-------|--------|
| Healthcare Administrator | Yes | Yes | Yes | Yes |
| System Manager | Yes | Yes | Yes | Yes |
| TPA Desk User | Yes | Yes | Yes | No |
| Physician | No | Yes | No | No |
| Nursing User | No | Yes | No | No |
| Accounts User | No | Yes | No | No |

## Validation Logic

- Patient on payer profile must match patient on preauth
- Valid From must be before Valid To
- Approved Amount is mandatory when transitioning to Approved/Partially Approved
- Status transitions are enforced server-side via transition map

## Notifications

- Query Raised → notify TPA Desk User role
- Approved / Partially Approved / Rejected → notify Physician role
- Timeline comments posted to Patient and Inpatient Record on every status change

## Reporting Impact

- New report: TPA Preauth Status (filters by status, payer, practitioner, date range)
- Feeds TPA Desk workspace

## Test Cases

See `docs/testing/us-i1-tpa-preauth.md`

## Open Questions / Assumptions

- Insurance Payor doctype is assumed to exist in Marley Health
- Preauth reference number is manually entered (no API integration to external TPA systems in this iteration)
- Multiple preauth requests per admission are supported (e.g., admission + subsequent procedure)
