# US-A1: Ward Master

## Purpose

Provide a dedicated ward master to model the physical and operational ward structure of an Indian hospital. This master drives downstream bed allocation, admission filtering, occupancy reporting, and nursing-station assignment.

## Scope

- CRUD for Hospital Ward records
- Ward classification (General, Semi-Private, Private, Deluxe, Suite, ICU variants, HDU, Burns, Isolation)
- Gender restriction tagging
- Critical-care auto-flagging
- Isolation support flag
- Linkage to standard Healthcare Service Unit tree
- Workspace access under IPD Setup

## Reused Standard DocTypes

| DocType | How Used |
|---------|----------|
| Company | Each ward belongs to a company |
| Medical Department | Ward specialty / department linkage |
| Healthcare Service Unit | Optional link to the HSU group node representing the ward in the facility tree |
| Healthcare Service Unit Type | Optional classification linkage |

## New Custom DocTypes

| DocType | Module | Purpose |
|---------|--------|---------|
| Hospital Ward | Alcura IPD Extensions | Operational ward master with classification, location, clinical configuration, and capacity tracking |

## Fields Added to Standard DocTypes

None. Hospital Ward is a standalone custom DocType that links to standard doctypes via Link fields.

## Workflow States

Not applicable. Hospital Ward is a non-submittable master document. Active/inactive status is controlled via the `is_active` check field.

## Permissions

| Role | Read | Write | Create | Delete |
|------|------|-------|--------|--------|
| Healthcare Administrator | Yes | Yes | Yes | Yes |
| Nursing User | Yes | No | No | No |
| Physician | Yes | No | No | No |

## Validation Logic

1. **Ward code format**: Must be alphanumeric with optional hyphens; no spaces or special characters.
2. **Ward code uniqueness**: Unique per company, enforced with `select-for-update` to prevent race conditions.
3. **Critical care auto-flag**: `is_critical_care` is automatically set to 1 when `ward_classification` is one of: ICU, CICU, MICU, NICU, PICU, SICU, HDU, Burns.
4. **HSU group check**: If a Healthcare Service Unit is linked, it must be a group node (`is_group=1`).
5. **Available beds**: Computed as `total_beds - occupied_beds` on every save.

## Notifications

None for this story. Future stories will add notifications for occupancy thresholds.

## Reporting Impact

Hospital Ward will serve as a dimension for:
- Ward-wise occupancy reports
- Bed availability dashboards
- Admission distribution by ward classification

These reports will be built in subsequent stories once bed and room masters are in place.

## Test Cases

See [docs/testing/us-a1-ward-master.md](../testing/us-a1-ward-master.md).

## Open Questions / Assumptions

1. **Branch as Data field**: Branch is stored as a free-text Data field rather than a Link to the HRMS Branch doctype to avoid a hard dependency on HRMS. This can be changed to a Link field in a future story if needed.
2. **Nursing Station as Data**: Nursing station is a free-text field. A dedicated Nursing Station master may be created in a future story.
3. **Capacity fields are read-only placeholders**: `total_beds`, `occupied_beds`, and `available_beds` will be populated by the Room/Bed master stories. For now they default to 0.
4. **Deletion protection is a placeholder**: The `on_trash` hook is wired but currently passes through. Concrete checks will be added once Room/Bed doctypes reference Hospital Ward.
