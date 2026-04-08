# IPD Dispense Entry

## Overview

Tracks each medication dispense event (partial or full) against an IPD Clinical Order. Supports substitution tracking, batch/warehouse auditing, and return workflows.

## Module

Alcura IPD Extensions

## Naming

Auto-named via series: `DISP-.#####`

## Key Fields

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| clinical_order | Link (IPD Clinical Order) | Yes | Source order |
| patient | Link (Patient) | Yes | Auto-fetched from order |
| inpatient_record | Link (Inpatient Record) | Yes | Auto-fetched |
| medication_item | Link (Item) | No | Item code (original or substitute) |
| medication_name | Data | Yes | Display name |
| dispensed_qty | Float | Yes | Must be > 0 |
| dispense_type | Select (Full/Partial) | Yes | |
| status | Select (Dispensed/Returned) | Yes | Default: Dispensed |
| batch_no | Data | No | Stock batch |
| warehouse | Link (Warehouse) | No | Source warehouse |
| is_substitution | Check | No | Flags substituted items |
| original_item | Link (Item) | When substitution | Original prescribed item |
| substitution_reason | Small Text | When substitution | |
| substitution_approved_by | Link (User) | When substitution | Doctor approval |
| dispensed_by | Link (User) | Auto | Current user |
| dispensed_at | Datetime | Auto | Current timestamp |

## Validations

- `dispensed_qty` must be > 0
- Cannot dispense against Cancelled or Draft orders
- Substitution requires `substitution_reason` and `substitution_approved_by`

## Permissions

- **Pharmacy User**: Create, Read, Write
- **Nursing User**: Read only
- **Physician**: Read only
- **Healthcare Administrator**: Full access

## Events

- **after_insert**: Updates parent order's `dispense_status` and `total_dispensed_qty`
- **on_update** (status change): Recalculates order dispense aggregates
- **on_trash**: Recalculates order dispense aggregates

## Related

- `alcura_ipd_ext.services.pharmacy_dispense_service`
- `alcura_ipd_ext.api.pharmacy`
