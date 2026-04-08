# DocType: Hospital Bed

## Overview

**Module:** Alcura IPD Extensions
**Type:** Master (non-submittable)
**Track Changes:** Yes
**Naming Rule:** `{hospital_room_name}-{bed_number}` (e.g., `TST-GW01-101-A`)

Hospital Bed is the core operational master for IPD bed management. It tracks occupancy, housekeeping, maintenance, infection control, and gender restriction for each physical bed. Each bed optionally bridges to a Healthcare Service Unit leaf node for standard billing and admission pipeline integration.

## Fields

### Bed Identity

| Fieldname | Type | Required | Notes |
|-----------|------|----------|-------|
| `bed_number` | Data | Yes | Short ID (e.g., "A", "1", "L1"), unique per room, auto-uppercased |
| `bed_label` | Data | No | Descriptive label (e.g., "Window Bed Left") |
| `hospital_room` | Link (Hospital Room) | Yes | Parent room; indexed |
| `hospital_ward` | Link (Hospital Ward) | Yes | Fetched from room; read-only; indexed |
| `company` | Link (Company) | Yes | Fetched from room; read-only; indexed |

### Classification

| Fieldname | Type | Notes |
|-----------|------|-------|
| `service_unit_type` | Link (Healthcare Service Unit Type) | Fetched from room; read-only; indexed |

### Operational Status

| Fieldname | Type | Options | Default | Notes |
|-----------|------|---------|---------|-------|
| `occupancy_status` | Select | Vacant, Occupied | Vacant | Synced with HSU; permlevel 1 |
| `housekeeping_status` | Select | Clean, Dirty, In Progress | Clean | Indexed |
| `maintenance_hold` | Check | - | 0 | Blocks bed allocation |
| `infection_block` | Check | - | 0 | Blocks bed allocation |
| `gender_restriction` | Select | No Restriction, Male Only, Female Only | No Restriction | Overrides ward default |

### Equipment

| Fieldname | Type | Notes |
|-----------|------|-------|
| `equipment_notes` | Small Text | Free-form equipment/readiness notes |

### Healthcare Linkage

| Fieldname | Type | Notes |
|-----------|------|-------|
| `healthcare_service_unit` | Link (Healthcare Service Unit) | Auto-created leaf node; read-only; indexed |

### Status

| Fieldname | Type | Default | Notes |
|-----------|------|---------|-------|
| `is_active` | Check | 1 | Cannot disable when Occupied |

## Indexes

The following fields have `search_index=1` for high-throughput operational queries:
- `hospital_room`, `hospital_ward`, `company`
- `occupancy_status`, `housekeeping_status`
- `service_unit_type`, `healthcare_service_unit`

## Permissions

| Role | Read | Write (L0) | Write (L1) | Create | Delete |
|------|------|-----------|-----------|--------|--------|
| Healthcare Administrator | Yes | Yes | Yes | Yes | Yes |
| Nursing User | Yes | Yes | No | No | No |
| Physician | Yes | No | No | No | No |

Level 0 fields: bed_number, bed_label, hospital_room, housekeeping_status, maintenance_hold, infection_block, gender_restriction, equipment_notes, is_active.

Level 1 fields: occupancy_status (restricted to prevent manual occupancy changes by non-admin roles).

## Server-Side Logic

### `autoname`
Builds the document name as `{hospital_room.name}-{bed_number}`.

### `validate`
1. Validates `bed_number` format
2. Validates `bed_number` uniqueness per room with row-level locking
3. Validates room is active
4. Prevents disable when `occupancy_status=Occupied`
5. Fetches `hospital_ward`, `company`, `service_unit_type` from room

### `before_save`
Normalises `bed_number` to uppercase.

### `after_insert`
- Auto-creates an HSU leaf node under the room's HSU (if room has one)
- Triggers capacity rollup on room and ward

### `on_update`
- Syncs `occupancy_status` to linked HSU
- Triggers capacity rollup on room and ward

### `on_trash`
- Prevents deletion when occupied
- Prevents deletion when referenced by Inpatient Occupancy
- Triggers capacity rollup on room and ward

## Client-Side Logic

- `bed_number` is auto-uppercased on change
- `hospital_room` query filtered to active rooms
- HSU link filtered to leaf nodes with `inpatient_occupancy=1` in same company
- Ward, company, service_unit_type are fetched from room and locked read-only
- Status indicator shows contextual colour: Available (green), Occupied (blue), Dirty (orange), Cleaning (yellow), Maintenance (orange), Infection Block (red), Inactive (grey)

## Occupancy Sync

### Bed → HSU
When `occupancy_status` changes on Hospital Bed (via save), the linked HSU's `occupancy_status` is updated.

### HSU → Bed
When the standard admission/discharge flow changes an HSU's `occupancy_status`, the `Healthcare Service Unit.on_update` doc_event hook propagates the change to the linked Hospital Bed and triggers capacity rollup.

## Capacity Rollup

On every bed insert, update, or delete:
1. `Hospital Room`: `total_beds`, `occupied_beds`, `available_beds` are recomputed from active bed children.
2. `Hospital Ward`: Same counters recomputed from all active beds in the ward.

Only active beds (`is_active=1`) are counted.

## List View

- Columns: bed_number, hospital_room, hospital_ward, occupancy_status, housekeeping_status, is_active
- Sort: bed_number ASC
- Search fields: bed_number, bed_label, hospital_room, hospital_ward, occupancy_status

## Workspace

Available under **IPD Setup** workspace.

## Future Enhancements

- Bed transfer workflow (move bed assignment between rooms)
- Housekeeping SLA timer and escalation
- Equipment checklist (structured, not free-text)
- Bed allocation API for admission desk
- Real-time bed board dashboard
