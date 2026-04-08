# DocType: Hospital Ward

## Overview

**Module:** Alcura IPD Extensions
**Type:** Master (non-submittable)
**Track Changes:** Yes
**Naming Rule:** `{company_abbr}-{ward_code}` (e.g. `ALC-ICU01`)

Hospital Ward is the operational ward master for IPD workflows. It captures the identity, location, clinical classification, and healthcare linkage of each ward within a hospital. It composes on top of the standard Healthcare Service Unit tree without replacing it.

## Fields

### Ward Identity

| Fieldname | Type | Required | Indexed | Notes |
|-----------|------|----------|---------|-------|
| `ward_code` | Data | Yes | Via name | Alphanumeric + hyphens, unique per company, auto-uppercased |
| `ward_name` | Data | Yes | - | Human-readable label, shown as title field |
| `company` | Link (Company) | Yes | Yes | Defaults from user session |

### Location

| Fieldname | Type | Required | Notes |
|-----------|------|----------|-------|
| `branch` | Data | No | Free-text hospital branch / campus |
| `building` | Data | No | Building name or code |
| `floor` | Data | No | Floor identifier |
| `nursing_station` | Data | No | Assigned nursing station |

### Clinical Configuration

| Fieldname | Type | Required | Notes |
|-----------|------|----------|-------|
| `medical_department` | Link (Medical Department) | No | Specialty served by this ward |
| `ward_classification` | Select | Yes | General, Semi-Private, Private, Deluxe, Suite, ICU, CICU, MICU, NICU, PICU, SICU, HDU, Burns, Isolation, Other |
| `gender_restriction` | Select | No | No Restriction (default), Male Only, Female Only |
| `is_critical_care` | Check | No | Read-only; auto-set from ward_classification |
| `supports_isolation` | Check | No | Manual flag for isolation-capable wards |

### Healthcare Linkage

| Fieldname | Type | Required | Notes |
|-----------|------|----------|-------|
| `healthcare_service_unit` | Link (Healthcare Service Unit) | No | Must be a group node (is_group=1) |
| `healthcare_service_unit_type` | Link (Healthcare Service Unit Type) | No | Classification reference |

### Capacity (read-only)

| Fieldname | Type | Notes |
|-----------|------|-------|
| `total_beds` | Int | Populated by Room/Bed master (future) |
| `occupied_beds` | Int | Updated by admission workflows (future) |
| `available_beds` | Int | Computed: total_beds - occupied_beds |

### Status

| Fieldname | Type | Default | Notes |
|-----------|------|---------|-------|
| `is_active` | Check | 1 | Deactivation will be protected when beds are linked (future) |

### Notes

| Fieldname | Type | Notes |
|-----------|------|-------|
| `description` | Small Text | Free-form notes |

## Permissions

| Role | Read | Write | Create | Delete | Export | Report |
|------|------|-------|--------|--------|--------|--------|
| Healthcare Administrator | Yes | Yes | Yes | Yes | Yes | Yes |
| Nursing User | Yes | No | No | No | Yes | Yes |
| Physician | Yes | No | No | No | Yes | Yes |

## Server-Side Logic

### `autoname`
Builds the document name as `{company_abbr}-{ward_code}`. Throws if the company has no abbreviation.

### `validate`
1. Validates `ward_code` format (regex `^[A-Za-z0-9][A-Za-z0-9\-]*$`)
2. Validates `ward_code` uniqueness per company with row-level locking
3. Sets `is_critical_care` based on `ward_classification`
4. Validates linked Healthcare Service Unit is a group node
5. Computes `available_beds`

### `before_save`
Normalises `ward_code` to uppercase.

### `on_trash`
Placeholder for deletion protection when Room/Bed doctypes are created.

## Client-Side Logic

- `ward_code` is auto-uppercased on change
- `healthcare_service_unit` query is filtered to `is_group=1` and matching `company`
- `is_critical_care` is set on `ward_classification` change for instant feedback
- Capacity fields are locked read-only
- Changing `company` clears `healthcare_service_unit`

## List View

- Columns: ward_code, ward_name, ward_classification, medical_department, is_active
- Sort: ward_name ASC
- Search fields: ward_code, ward_name, ward_classification, medical_department

## Workspace

Available under **IPD Setup** workspace with a shortcut to the Hospital Ward list view.

## Future Enhancements

- Link from Room/Bed master for automatic capacity rollup
- Deactivation protection when active beds exist
- Nursing Station as a linked master
- Branch as a linked master (if HRMS Branch or a custom doctype is preferred)
- Ward-wise occupancy dashboard report
