# US-B1: Show Live Available Beds by Room Type

## Purpose

Enable admission desk users to view available beds in real time, filtered by ward, room type, floor, critical care, gender, isolation, equipment readiness, and payer eligibility — so they can allocate the right bed quickly.

## Scope

- Server-side availability computation with optimized SQL queries
- IPD Bed Policy-driven exclusion rules (dirty, cleaning, maintenance, infection-blocked beds)
- Rich filter set: ward, room type, floor, critical care, gender, isolation, payer type + payer
- Room tariff summary and payer eligibility indicator
- Housekeeping status visibility
- Summary cards (total, available, occupied, blocked)
- Script Report with color-coded formatters
- Whitelisted API for programmatic access
- IPD Desk workspace for admission operations

## Reused Standard DocTypes

| DocType | How Used |
|---------|----------|
| Healthcare Service Unit Type | Room type dimension; inpatient_occupancy filter |
| Customer | Payer entity for Corporate/TPA payer eligibility |
| Medical Department | Specialty filter via ward linkage |
| Inpatient Record | Linked in IPD Desk workspace for operational context |

## Reused Custom DocTypes

| DocType | How Used |
|---------|----------|
| Hospital Bed | Primary data source — bed master with occupancy, housekeeping, maintenance, infection, gender |
| Hospital Room | Room master — floor, wing, room type, capacity |
| Hospital Ward | Ward master — classification, specialty, gender, critical care, isolation |
| Room Tariff Mapping | Payer-aware tariff lookup for daily rate and eligibility |
| IPD Bed Policy | Policy settings that control exclusion rules and enforcement levels |

## New Custom DocTypes

None. US-B1 consumes existing doctypes.

## Fields Added to Standard DocTypes

None.

## Workflow States

Not applicable. The bed board is a read-only report that reflects current bed state.

## Permissions

| Component | Roles Allowed |
|-----------|---------------|
| Live Bed Board report | Healthcare Administrator, Nursing User, Physician |
| `get_bed_board` API | Any user with Hospital Bed read permission |
| `get_bed_board_summary` API | Any user with Hospital Bed read permission |

## Validation Logic

1. **Permission check**: API endpoints verify `Hospital Bed` read permission before returning data.
2. **Policy enforcement**: Exclusion rules from IPD Bed Policy are applied server-side — no client bypass.
3. **Payer eligibility**: When `enforce_payer_eligibility` is Strict, beds without a matching tariff are removed from results.

## Notifications

None for this story. Future stories may add alerts for:
- Low bed availability (approaching buffer threshold)
- Housekeeping SLA breaches

## Reporting Impact

### Live Bed Board (Script Report)

- **Filters**: Ward, Room Type, Floor, Critical Care Only, Gender, Isolation Only, Payer Type, Payer, Show Unavailable
- **Columns**: Bed, Label, Room, Ward, Room Type, Floor, Availability (color-coded), Housekeeping (color-coded), Gender, Maintenance, Infection, Equipment, Daily Rate (when payer filter active), Payer Eligible (when payer filter active), Ward Class, Specialty
- **Summary cards**: Total Beds, Available (green), Occupied (red), Blocked (orange)

### Data Flow

```
Hospital Bed + Room + Ward (SQL JOIN)
  → Policy exclusions (WHERE clauses)
  → User filters (WHERE clauses)
  → Availability label computation
  → Payer eligibility enrichment (tariff_service)
  → Report columns + formatters
```

## Architecture

### Service Layer: `services/bed_availability_service.py`

| Function | Purpose |
|----------|---------|
| `get_available_beds(filters)` | Main query — joins beds/rooms/wards, applies policy + filters, enriches with tariff |
| `get_bed_board_summary(filters)` | Aggregate counts for summary cards |
| `_build_bed_query(filters, policy)` | SQL builder with parameterized conditions |
| `_append_policy_exclusions(conditions, policy)` | Translates policy flags to WHERE clauses |
| `_append_user_filters(conditions, params, filters, policy)` | Translates user filters to WHERE clauses |
| `_compute_availability_label(beds)` | Annotates each bed with human-readable status |
| `_apply_payer_eligibility(beds, payer_type, payer, policy, filters)` | Groups by room type, calls `resolve_tariff()` once per type |

### API Layer: `api/bed_board.py`

| Endpoint | Method |
|----------|--------|
| `alcura_ipd_ext.api.bed_board.get_bed_board` | Whitelisted — wraps `get_available_beds()` |
| `alcura_ipd_ext.api.bed_board.get_bed_board_summary` | Whitelisted — wraps `get_bed_board_summary()` |

### Report: `report/live_bed_board/`

- `live_bed_board.json` — Report definition (Script Report, ref_doctype: Hospital Bed)
- `live_bed_board.py` — `execute(filters)` delegates to service layer
- `live_bed_board.js` — Filter definitions, color-coded formatters, refresh button

### Workspaces

- **IPD Setup** — Updated with IPD Bed Policy link and Live Bed Board report shortcut
- **IPD Desk** — New workspace with Live Bed Board as primary shortcut, plus Hospital Bed and Inpatient Record links

## Test Cases

See [docs/testing/us-b1-live-bed-availability.md](../testing/us-b1-live-bed-availability.md).

## Open Questions / Assumptions

1. **Script Report vs Custom Page**: The Script Report is the initial implementation. If UX demands a card-based visual bed board with drag-and-drop allocation, a custom Frappe Page can be added in a future story, reusing the same service layer.
2. **Payer eligibility grouping**: Tariff lookups are grouped by room type (not per bed) to avoid N+1 queries. All beds of the same room type share the same tariff eligibility.
3. **Real-time refresh**: The report has a manual Refresh button. Real-time push via socketio can be added later when bed state changes trigger events.
4. **Gender "Advisory" mode**: Under Advisory enforcement, the gender filter is not applied as a WHERE clause — all beds appear, but future UX may add a visual warning indicator.
5. **Company scope**: If the user has a default company set, it is passed to the query. Multi-company filtering is not yet exposed as a report filter.
