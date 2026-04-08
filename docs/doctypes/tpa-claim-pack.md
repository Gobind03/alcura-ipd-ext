# TPA Claim Pack

## Purpose

Tracks the bundling and submission of claim documents to TPA/insurers for settlement.

## Module

Alcura IPD Extensions

## Naming

`TCP-.YYYY.-.#####`

## Key Fields

| Field | Type | Required | Indexed | Notes |
|-------|------|----------|---------|-------|
| inpatient_record | Link (Inpatient Record) | Yes | Yes | |
| patient | Link (Patient) | Yes | Yes | |
| patient_payer_profile | Link (Patient Payer Profile) | No | Yes | |
| insurance_payor | Link (Insurance Payor) | No | Yes | |
| company | Link (Company) | Yes | Yes | |
| status | Select | Yes | Yes | Draft/In Review/Submitted/Acknowledged/Settled/Disputed |
| tpa_preauth_request | Link (TPA Preauth Request) | No | No | |
| final_invoice | Link (Sales Invoice) | No | No | |
| submission_date | Date | No | No | |
| settlement_amount | Currency | No | No | |
| disallowance_amount | Currency | No | No | |

## Child Table: documents (TPA Claim Pack Document)

| Field | Type | Notes |
|-------|------|-------|
| document_type | Select | Final Bill / Bill Break-Up / Discharge Summary / etc. |
| description | Data | |
| is_mandatory | Check | |
| is_available | Check | Auto-updated on refresh |
| file_attachment | Attach | |
| remarks | Small Text | |

## Status Transitions

| From | Allowed To |
|------|-----------|
| Draft | In Review |
| In Review | Submitted, Draft |
| Submitted | Acknowledged, Disputed |
| Acknowledged | Settled, Disputed |
| Settled | (terminal) |
| Disputed | Submitted |
