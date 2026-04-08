# US-I5: TPA Final Submission Pack

## Purpose

Enable TPA desk users to bundle all final claim documents digitally so that settlement turnaround is improved.

## Scope

- Auto-populated document checklist per claim
- Document availability tracking
- Status lifecycle: Draft through Settled/Disputed
- Submission and settlement recording
- Pending document indicators

## Reused Standard DocTypes

- Sales Invoice (final bill reference), Inpatient Record, Patient

## Reused Custom DocTypes

- Patient Payer Profile, TPA Preauth Request, Insurance Payor

## New Custom DocTypes

- **TPA Claim Pack** — main claim submission document
- **TPA Claim Pack Document** — child table for individual documents

## Standard Document Types

| Document | Mandatory |
|----------|-----------|
| Final Bill | Yes |
| Bill Break-Up | Yes |
| Discharge Summary | Yes |
| Investigation Report | No |
| Operative Notes | No |
| Implant Sticker | No |
| Pharmacy Summary | No |
| Preauth Approval | Yes |
| Consent Form | Yes |
| ID Proof | Yes |

## Workflow States

Draft → In Review → Submitted → Acknowledged → Settled
Draft → In Review → Submitted → Disputed → Submitted (resubmit cycle)

## Permissions

| Role | Create | Read | Write | Delete |
|------|--------|------|-------|--------|
| Healthcare Administrator | Yes | Yes | Yes | Yes |
| System Manager | Yes | Yes | Yes | Yes |
| TPA Desk User | Yes | Yes | Yes | No |
| Accounts User | No | Yes | No | No |

## Reporting

TPA Claim Pack Status report with filters by status, insurance payor, date range, company.

## Test Cases

See `docs/testing/us-i5-tpa-claim-pack.md`
