# Discharge Billing Checklist

## Purpose

Tracks discharge readiness checks. One per Inpatient Record (unique constraint). Supports auto-derived and manual checks with override capability.

## Module

Alcura IPD Extensions

## Naming

`DBC-.YYYY.-.#####`

## Key Fields

| Field | Type | Required | Indexed | Notes |
|-------|------|----------|---------|-------|
| inpatient_record | Link (Inpatient Record) | Yes | Yes (unique) | |
| patient | Link (Patient) | Yes | Yes | |
| company | Link (Company) | Yes | Yes | |
| status | Select | Yes | Yes | Pending/In Progress/Cleared/Overridden |
| override_authorized | Check | No | No | |
| override_by | Link (User) | No | No | |
| override_reason | Small Text | No | No | Required when overriding |

## Child Table: items (Discharge Checklist Item)

| Field | Type | Notes |
|-------|------|-------|
| check_name | Data | e.g., "Pending Medication Orders" |
| check_category | Select | Clinical/Financial/TPA/Administrative |
| check_status | Select | Pending/Cleared/Waived/Not Applicable |
| auto_derived | Check | Whether status is computed automatically |
| detail | Small Text | e.g., "3 pending medication orders" |
| cleared_by | Link (User) | |
| cleared_on | Datetime | |
| waiver_reason | Small Text | Required when status is Waived |
