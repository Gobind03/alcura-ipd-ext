# TPA Claim Pack Lifecycle

## States

1. **Draft** — pack created, documents being assembled
2. **In Review** — internal review before submission
3. **Submitted** — sent to TPA/insurer
4. **Acknowledged** — TPA has acknowledged receipt
5. **Settled** — payment received
6. **Disputed** — TPA has raised objections

## Audit Trail

- prepared_by / prepared_on — set on creation
- reviewed_by / reviewed_on — set when moved to In Review
- submitted_by_user / submitted_on_datetime — set when marked Submitted
- Timeline comments posted on Inpatient Record

## Document Availability

- Each document row has `is_available` flag
- "Refresh Availability" button checks for file attachments
- Missing mandatory documents trigger warning on submission

## Settlement

- settlement_amount, settlement_date, settlement_reference
- disallowance_amount, disallowance_reason (for Disputed status)
