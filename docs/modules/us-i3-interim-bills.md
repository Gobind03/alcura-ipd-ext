# US-I3: Generate Interim Bills During Stay

## Purpose

Enable billing executives to generate interim billing snapshots during active IPD stays, showing approved vs non-approved vs patient-pay amounts, deposits, and balance.

## Scope

- Compute room charges from bed movement history and tariff mappings
- Aggregate clinical order charges by category
- Apply payer billing rules for split computation
- Show deposits and balance due
- Expose as Script Report and print format

## Reused Standard DocTypes

- Inpatient Record, Patient, Sales Invoice, Payment Entry, Item, Item Price

## Reused Custom DocTypes

- Bed Movement Log, Hospital Room, Room Tariff Mapping
- IPD Clinical Order
- Patient Payer Profile, TPA Preauth Request
- Payer Billing Rule Set (US-I2)

## New Artifacts

- **Service**: `interim_bill_service.py`
- **Report**: IPD Interim Bill (Script Report)
- **Print Format**: IPD Interim Bill (Jinja)
- **API**: `billing.get_interim_bill`

No new DocTypes created — interim bill is a computed snapshot.

## Report Columns

Category, Description, Qty, Rate, Gross Amount, Payer Amount, Patient Amount, Excluded, Rule Applied

## Summary Section

Gross Total, Payer Total, Patient Total, Deductible Applied, Preauth Approved, Preauth Overshoot, Deposits, Balance Due

## Permissions

Accessible to: Healthcare Administrator, TPA Desk User, Accounts User, Physician, Nursing User

## Test Cases

See `docs/testing/us-i3-interim-bills.md`

## Assumptions

- Room charges computed from bed movement log entries and tariff service
- Clinical order charges use item standard selling rate from Item Price
- Deposits sourced from Payment Entry (Receive type) for patient customer
- Interim bill is not posted as a financial document; it is purely informational
