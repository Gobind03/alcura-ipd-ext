# US-A3: Room and Bed Setup

## Purpose

Model individual hospital rooms and beds as operational masters for IPD workflows, with each bed bridging to a standard Healthcare Service Unit leaf node for billing and admission pipeline compatibility.

## Scope

- CRUD for Hospital Room records under wards
- CRUD for Hospital Bed records under rooms
- Bed operational state: occupancy, housekeeping, maintenance hold, infection block, gender restriction, equipment readiness
- Auto-creation of HSU tree nodes (group for room, leaf for bed)
- Bidirectional occupancy sync between Hospital Bed and Healthcare Service Unit
- Capacity rollup from beds to rooms and wards
- Deletion protection for rooms (when beds exist) and beds (when occupied or referenced by Inpatient Occupancy)
- Workspace integration under IPD Setup

## Reused Standard DocTypes

| DocType | How Used |
|---------|----------|
| Healthcare Service Unit | Leaf nodes represent beds in the facility tree; group nodes represent rooms; standard admission/billing pipeline |
| Healthcare Service Unit Type | Room type classification (extended in US-A2); linked from Hospital Room |
| Inpatient Record | References HSU via Inpatient Occupancy child table; unchanged |
| Inpatient Occupancy | Child table of Inpatient Record; references bed's HSU leaf node |
| Company | Each room and bed belongs to a company (via ward) |
| Hospital Ward | Parent for rooms; custom doctype from US-A1 |

## New Custom DocTypes

| DocType | Module | Purpose |
|---------|--------|---------|
| Hospital Room | Alcura IPD Extensions | Physical room within a ward; groups beds, carries room-type classification |
| Hospital Bed | Alcura IPD Extensions | Individual bed within a room; carries operational status, bridges to HSU |

## Fields Added to Standard DocTypes

None. Hospital Room and Hospital Bed link to standard doctypes via Link fields. The HSU tree is extended by auto-creating nodes, not by adding custom fields.

## Workflow States

Not applicable. Hospital Room and Hospital Bed are non-submittable masters. Operational state is managed via status fields (`occupancy_status`, `housekeeping_status`, `is_active`).

## Permissions

### Hospital Room

| Role | Read | Write | Create | Delete |
|------|------|-------|--------|--------|
| Healthcare Administrator | Yes | Yes | Yes | Yes |
| Nursing User | Yes | No | No | No |
| Physician | Yes | No | No | No |

### Hospital Bed

| Role | Read | Write (Level 0) | Write (Level 1) | Create | Delete |
|------|------|-----------------|-----------------|--------|--------|
| Healthcare Administrator | Yes | Yes | Yes | Yes | Yes |
| Nursing User | Yes | Yes | No | No | No |
| Physician | Yes | No | No | No | No |

Level 1 fields (occupancy_status) are restricted to Healthcare Administrator to prevent manual occupancy overrides by non-admin roles. Nursing User can update housekeeping_status, infection_block, and equipment_notes at Level 0.

## Validation Logic

### Hospital Room

1. **Room number format**: Alphanumeric with optional hyphens; no spaces or special characters.
2. **Room number uniqueness**: Unique per hospital_ward, enforced with `SELECT ... FOR UPDATE`.
3. **Ward must be active**: Cannot add rooms to an inactive ward.
4. **Service unit type**: Must have `inpatient_occupancy=1`.
5. **Available beds**: Computed as `total_beds - occupied_beds` on every save.

### Hospital Bed

1. **Bed number format**: Same pattern as room number.
2. **Bed number uniqueness**: Unique per hospital_room, enforced with `SELECT ... FOR UPDATE`.
3. **Room must be active**: Cannot add beds to an inactive room.
4. **Cannot disable when occupied**: Bed with `occupancy_status=Occupied` cannot be deactivated.
5. **Cannot delete when occupied**: Occupied beds cannot be deleted.
6. **Cannot delete with history**: Beds referenced by Inpatient Occupancy cannot be deleted.
7. **Ward/company inheritance**: `hospital_ward`, `company`, `service_unit_type` are auto-fetched from the room.

## Notifications

None for this story. Future stories will add notifications for:
- Housekeeping turnaround alerts
- Maintenance hold clearance
- Infection block escalation

## Reporting Impact

Hospital Room and Hospital Bed will serve as dimensions for:
- Ward-wise bed availability reports
- Room-type occupancy analytics
- Housekeeping turnaround reports
- Maintenance and infection reports
- Capacity utilisation dashboards

These reports will be built in subsequent stories.

## Test Cases

See [docs/testing/us-a3-room-bed-setup.md](../testing/us-a3-room-bed-setup.md).

## Open Questions / Assumptions

1. **HSU auto-creation is optional**: If a ward does not have an HSU group node, room and bed HSU nodes are not created. This allows incremental HSU tree setup.
2. **Occupancy sync is unidirectional per trigger**: Bed→HSU sync happens on bed save; HSU→Bed sync happens on HSU update (from admission/discharge). This avoids infinite loops.
3. **Gender restriction on bed overrides ward**: The bed-level gender restriction takes precedence over the ward-level setting for allocation queries.
4. **Capacity rollup uses active beds only**: Inactive beds are excluded from `total_beds` and `available_beds` counts.
5. **Housekeeping status is free-form**: No enforced state machine for housekeeping transitions in this story. Future stories may add strict transitions.
6. **Equipment notes is free-text**: No structured equipment inventory in this story.
