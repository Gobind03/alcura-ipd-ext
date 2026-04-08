# TPA Preauth Request

## Purpose

Tracks pre-authorization requests to third-party administrators (TPAs) and insurers. Captures diagnosis, treatment details, financial estimates, and approval outcomes.

## Module

Alcura IPD Extensions

## Naming

`PAR-.YYYY.-.#####` (e.g., PAR-2026-00001)

## Key Fields

| Field | Type | Required | Indexed | Notes |
|-------|------|----------|---------|-------|
| patient | Link (Patient) | Yes | Yes | |
| inpatient_record | Link (Inpatient Record) | No | Yes | |
| patient_payer_profile | Link (Patient Payer Profile) | Yes | Yes | |
| payer_type | Data (fetched) | No | Yes | From payer profile |
| insurance_payor | Link (Insurance Payor) | No | Yes | From payer profile |
| company | Link (Company) | Yes | Yes | |
| status | Select | Yes | Yes | See workflow states |
| primary_diagnosis | Small Text | Yes | No | |
| treating_practitioner | Link (Healthcare Practitioner) | No | Yes | |
| requested_amount | Currency | Yes | No | |
| approved_amount | Currency | No | No | Required on approval |
| preauth_reference_number | Data | No | No | TPA reference |
| valid_from / valid_to | Date | No | No | Approval validity |

## Child Tables

- **responses** → TPA Preauth Response (response_type, response_by, response_datetime, response_text, attachment)

## Audit Fields

submitted_by, submitted_on, approved_by, approved_on, rejected_by, rejected_on, closed_by, closed_on, last_status_change_by, last_status_change_on

## Status Transitions

| From | Allowed To |
|------|-----------|
| Draft | Submitted |
| Submitted | Query Raised, Approved, Partially Approved, Rejected |
| Query Raised | Resubmitted |
| Resubmitted | Query Raised, Approved, Partially Approved, Rejected |
| Approved | Closed |
| Partially Approved | Closed |
| Rejected | Closed, Submitted |
| Closed | (terminal) |
