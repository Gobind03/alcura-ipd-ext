# IPD Interim Bill Report

## Purpose

Generates a real-time interim bill for an active inpatient record showing all charges, payer splits, deposits, and balance due.

## Type

Script Report + Jinja Print Format

## Reference DocType

Inpatient Record

## Filters

- Inpatient Record (mandatory)
- As of Date (defaults to today)

## Columns

Category, Description, Qty, Rate, Gross Amount, Payer Amount, Patient Amount, Excluded, Rule Applied

## Message Bar

Shows summary totals: Gross, Payer, Patient, Deductible, Preauth, Deposits, Balance

## Print Format

Printable/exportable via the IPD Interim Bill print format on Inpatient Record.

## Access Roles

Healthcare Administrator, TPA Desk User, Accounts User, Physician, Nursing User
