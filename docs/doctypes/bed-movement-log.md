# Bed Movement Log

## Purpose

Immutable audit-trail record for every bed change in the IPD patient journey. Covers Admission, Transfer, and Discharge movements. Created by the allocation and transfer services; not intended for manual creation by users.

## Module

Alcura IPD Extensions

## Naming

`naming_series: BML-.#####` (e.g., BML-00001)

## Track Changes

Yes

## Is Submittable

No — records are immutable after creation (enforced via `on_update` validation).

## Fields

### Movement

| Fieldname | Type | Options | Required | Notes |
|-----------|------|---------|----------|-------|
| naming_series | Select | `BML-.#####` | Yes | Hidden |
| movement_type | Select | Admission, Transfer, Discharge | Yes | Indexed, in list view |
| movement_datetime | Datetime | | Yes | Indexed, default Now |
| reason | Small Text | | Conditional | Mandatory for Transfer |

### Patient

| Fieldname | Type | Options | Required | Notes |
|-----------|------|---------|----------|-------|
| inpatient_record | Link → Inpatient Record | | Yes | Indexed |
| patient | Link → Patient | | Yes | Indexed |
| patient_name | Data | | No | Fetched from patient, read-only, in list view |

### Source (From)

Blank for Admission movements.

| Fieldname | Type | Options | Required | Notes |
|-----------|------|---------|----------|-------|
| from_bed | Link → Hospital Bed | | Conditional | Required for Transfer/Discharge; indexed |
| from_room | Link → Hospital Room | | No | Fetched from from_bed, read-only |
| from_ward | Link → Hospital Ward | | No | Fetched from from_bed, read-only |
| from_service_unit | Link → Healthcare Service Unit | | No | Fetched from from_bed, read-only |

### Destination (To)

Blank for Discharge movements.

| Fieldname | Type | Options | Required | Notes |
|-----------|------|---------|----------|-------|
| to_bed | Link → Hospital Bed | | Conditional | Required for Admission/Transfer; indexed |
| to_room | Link → Hospital Room | | No | Fetched from to_bed, read-only |
| to_ward | Link → Hospital Ward | | No | Fetched from to_bed, read-only |
| to_service_unit | Link → Healthcare Service Unit | | No | Fetched from to_bed, read-only |

### Clinical

| Fieldname | Type | Options | Required | Notes |
|-----------|------|---------|----------|-------|
| ordered_by_practitioner | Link → Healthcare Practitioner | | No | |
| practitioner_name | Data | | No | Fetched, read-only |

### Housekeeping

| Fieldname | Type | Options | Required | Notes |
|-----------|------|---------|----------|-------|
| source_bed_action | Select | Mark Dirty, Mark Vacant, No Change | No | For Transfer/Discharge |

### Audit Trail

| Fieldname | Type | Options | Required | Notes |
|-----------|------|---------|----------|-------|
| performed_by | Link → User | | No | Auto-set on insert, read-only |
| performed_on | Datetime | | No | Auto-set on insert, read-only |
| consumed_reservation | Link → Bed Reservation | | No | Set when reservation is consumed during Admission |
| company | Link → Company | | Yes | Indexed |

## Indexes

- `movement_type` (search_index + in_standard_filter)
- `movement_datetime` (search_index)
- `inpatient_record` (search_index + in_standard_filter)
- `patient` (search_index + in_standard_filter)
- `from_bed` (search_index)
- `to_bed` (search_index)
- `company` (search_index + in_standard_filter)

## Permissions

| Role | Read | Write | Create | Delete |
|------|------|-------|--------|--------|
| Healthcare Administrator | Yes | Yes | Yes | Yes |
| Nursing User | Yes | No | Yes | No |
| Physician | Yes | No | No | No |

## Controller

`alcura_ipd_ext/alcura_ipd_ext/doctype/bed_movement_log/bed_movement_log.py`

### Lifecycle Hooks

- `before_insert`: Auto-sets `performed_by` and `performed_on`
- `validate`: Validates type-field coupling and reason requirement for transfers
- `on_update`: Enforces immutability — prevents modification after creation

### Validation Rules

1. **Admission**: `to_bed` is required
2. **Transfer**: Both `from_bed` and `to_bed` are required; `reason` is mandatory
3. **Discharge**: `from_bed` is required
4. **Immutability**: Existing records cannot be modified (on_update blocks save)

## Client Script

`alcura_ipd_ext/alcura_ipd_ext/doctype/bed_movement_log/bed_movement_log.js`

- Status indicator colors: Admission (green), Transfer (blue), Discharge (orange)
- Save disabled for existing records (read-only after creation)

## Business Logic

Bed Movement Log records are created exclusively by:
- `bed_allocation_service.allocate_bed_on_admission()` — type=Admission
- `bed_transfer_service.transfer_patient()` — type=Transfer
- Future: discharge service — type=Discharge

Records should not be created manually. The services use `flags.ignore_permissions = True` for creation and set all audit fields automatically.
