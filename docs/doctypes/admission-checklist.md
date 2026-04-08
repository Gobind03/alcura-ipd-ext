# Admission Checklist

## Purpose

Per-admission checklist instance linked 1:1 to an Inpatient Record. Created from a template; tracks completion/waiver of each item with full audit trail.

## Fields

| Fieldname | Type | Notes |
|-----------|------|-------|
| `naming_series` | Select | ACL-.YYYY.-.##### |
| `inpatient_record` | Link → Inpatient Record | Required, unique |
| `patient` | Link → Patient | Required |
| `patient_name` | Data | Fetched |
| `template_used` | Link → Admission Checklist Template | Read-only |
| `status` | Select | Incomplete/Complete/Overridden; read-only |
| `company` | Link → Company | |
| `checklist_entries` | Table → Admission Checklist Entry | |
| `completed_by` | Link → User | Read-only; set when status becomes Complete/Overridden |
| `completed_on` | Datetime | Read-only |
| `notes` | Small Text | |

## Child Table: Admission Checklist Entry

| Fieldname | Type | Notes |
|-----------|------|-------|
| `item_label` | Data | Read-only, from template |
| `category` | Select | Read-only |
| `is_mandatory` | Check | Read-only |
| `status` | Select | Pending/Completed/Waived |
| `completed_by` | Link → User | Read-only |
| `completed_on` | Datetime | Read-only |
| `override_by` | Link → User | Read-only; for Waived items |
| `override_reason` | Small Text | Required when Waived |
| `evidence` | Attach | Optional supporting document |

## Status Computation

- **Incomplete**: at least one mandatory entry is Pending
- **Complete**: all mandatory entries are Completed (none Waived)
- **Overridden**: all mandatory entries are Completed or Waived (at least one Waived)

## Permissions

- Healthcare Administrator: full access
- IPD Admission Officer: create, read, write
- Nursing User: read, write

## Indexes

- `inpatient_record` (unique + search index)
- `patient` (search index)
- `status` (search index)

## Module

Alcura IPD Extensions
