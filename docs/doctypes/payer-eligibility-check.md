# Payer Eligibility Check

## Purpose

Records the outcome of payer eligibility verification for a patient before IPD admission. Captures the verifier, date-time, status, approved amount, exclusions, conditions, and TPA pre-authorization reference.

## Module

Alcura IPD Extensions

## Naming

`PEC-.YYYY.-.#####` (auto-generated naming series)

## Key Properties

- Non-submittable
- Track changes enabled
- No rename allowed

## Fields

### Patient & Payer Section

| Fieldname | Type | Label | Required | Indexed | Notes |
|-----------|------|-------|----------|---------|-------|
| `patient` | Link (Patient) | Patient | Yes | Yes | |
| `patient_name` | Data | Patient Name | No | No | Fetched from patient |
| `patient_payer_profile` | Link (Patient Payer Profile) | Patient Payer Profile | Yes | Yes | |
| `payer_type` | Data | Payer Type | No | Yes | Fetched from profile |
| `inpatient_record` | Link (Inpatient Record) | Inpatient Record | No | Yes | Optional link to admission |
| `company` | Link (Company) | Company | Yes | Yes | |

### Verification Section

| Fieldname | Type | Label | Required | Indexed | Notes |
|-----------|------|-------|----------|---------|-------|
| `verification_status` | Select | Verification Status | Yes | Yes | Pending/Verified/Conditional/Rejected/Expired |
| `verified_by` | Link (User) | Verified By | No | No | Read-only, auto-set |
| `verification_datetime` | Datetime | Verification Date/Time | No | No | Read-only, auto-set |

### Approved Coverage Section

Visible only when status is Verified or Conditional.

| Fieldname | Type | Label | Notes |
|-----------|------|-------|-------|
| `approved_amount` | Currency | Approved Amount | |
| `approved_room_category` | Select | Approved Room Category | Same options as room category entitlement |
| `approved_duration_days` | Int | Approved Duration (Days) | |
| `exclusions` | Small Text | Exclusions | Treatments/procedures excluded |
| `conditions` | Small Text | Conditions | Conditions attached to approval |

### Reference & Validity Section

| Fieldname | Type | Label | Notes |
|-----------|------|-------|-------|
| `reference_number` | Data | Pre-Auth / Reference Number | TPA reference |
| `valid_from` | Date | Valid From | |
| `valid_to` | Date | Valid To | |

### Remarks Section

| Fieldname | Type | Label | Notes |
|-----------|------|-------|-------|
| `remarks` | Text Editor | Remarks | Collapsible |

### Audit Trail Section

| Fieldname | Type | Label | Notes |
|-----------|------|-------|-------|
| `submitted_by` | Link (User) | Submitted By | Read-only, set on insert |
| `submitted_on` | Datetime | Submitted On | Read-only, set on insert |
| `last_status_change_by` | Link (User) | Last Status Change By | Read-only |
| `last_status_change_on` | Datetime | Last Status Change On | Read-only |

## Status Lifecycle

| From | Allowed To |
|------|-----------|
| Pending | Verified, Conditional, Rejected |
| Verified | Expired |
| Conditional | Verified, Rejected, Expired |
| Rejected | Pending |
| Expired | Pending |

## Permissions

| Role | Read | Write | Create | Delete |
|------|------|-------|--------|--------|
| Healthcare Administrator | Y | Y | Y | Y |
| System Manager | Y | Y | Y | Y |
| TPA Desk User | Y | Y | Y | N |
| Healthcare Receptionist | Y | Y | Y | N |
| Nursing User | Y | N | N | N |
| Physician | Y | N | N | N |
| Accounts User | Y | N | N | N |

## Controller Logic

- `before_insert`: Sets `submitted_by`, `submitted_on`
- `validate`: Date range check, profile ownership check, status transition validation
- `on_update`: On status change — sets audit fields, adds timeline comments to Patient and Inpatient Record, sends notifications

## Client Script

- Status color indicators (Pending=orange, Verified=green, Conditional=blue, Rejected=red, Expired=grey)
- Action buttons for allowed status transitions
- Prompts for reference number and approved amount when marking Verified/Conditional
- Patient-filtered queries for profile and inpatient record links
- Auto-fetch of room category and sum insured from payer profile
