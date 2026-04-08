# DocType: Hospital Room

## Overview

**Module:** Alcura IPD Extensions
**Type:** Master (non-submittable)
**Track Changes:** Yes
**Naming Rule:** `{hospital_ward_name}-{room_number}` (e.g., `TST-GW01-101`)

Hospital Room models a physical room within a hospital ward. It groups Hospital Bed records and carries room-type classification, floor/wing information, and capacity counters. Each room optionally bridges to a Healthcare Service Unit group node in the facility tree.

## Fields

### Room Identity

| Fieldname | Type | Required | Notes |
|-----------|------|----------|-------|
| `room_number` | Data | Yes | Alphanumeric + hyphens, unique per ward, auto-uppercased |
| `room_name` | Data | No | Human-readable label (title field) |
| `hospital_ward` | Link (Hospital Ward) | Yes | Parent ward; indexed |
| `company` | Link (Company) | Yes | Fetched from ward; read-only; indexed |

### Classification

| Fieldname | Type | Required | Notes |
|-----------|------|----------|-------|
| `service_unit_type` | Link (Healthcare Service Unit Type) | Yes | Must have `inpatient_occupancy=1`; indexed |
| `floor` | Data | No | Floor within building |
| `wing` | Data | No | Wing/block identifier |
| `is_ac` | Check | No | Air-conditioned flag |

### Capacity (read-only)

| Fieldname | Type | Notes |
|-----------|------|-------|
| `total_beds` | Int | Count of active Hospital Bed children |
| `occupied_beds` | Int | Active beds with `occupancy_status=Occupied` |
| `available_beds` | Int | Computed: `total_beds - occupied_beds` |

### Healthcare Linkage

| Fieldname | Type | Notes |
|-----------|------|-------|
| `healthcare_service_unit` | Link (Healthcare Service Unit) | Auto-created group node; read-only |

### Status

| Fieldname | Type | Default | Notes |
|-----------|------|---------|-------|
| `is_active` | Check | 1 | Disable instead of delete |

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
Builds the document name as `{hospital_ward.name}-{room_number}`.

### `validate`
1. Validates `room_number` format (regex `^[A-Za-z0-9][A-Za-z0-9\-]*$`)
2. Validates `room_number` uniqueness per ward with row-level locking
3. Validates ward is active
4. Validates service unit type has `inpatient_occupancy=1`
5. Computes `available_beds`

### `before_save`
Normalises `room_number` to uppercase.

### `after_insert`
Auto-creates an HSU group node under the ward's HSU (if ward has one).

### `on_trash`
Prevents deletion when Hospital Bed records are linked.

## Client-Side Logic

- `room_number` is auto-uppercased on change
- `hospital_ward` query filtered to active wards
- `service_unit_type` query filtered to `inpatient_occupancy=1`
- `healthcare_service_unit` query filtered to group nodes in same company
- Company is fetched from ward on selection
- Capacity fields and HSU link are locked read-only

## List View

- Columns: room_number, hospital_ward, service_unit_type, is_active
- Sort: room_number ASC
- Search fields: room_number, room_name, hospital_ward, service_unit_type

## Workspace

Available under **IPD Setup** workspace.

## Future Enhancements

- Room-level amenity checklist
- Photo/floor-plan attachment
- Room-type change with active beds validation
