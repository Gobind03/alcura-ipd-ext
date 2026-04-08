# US-A4: Assign Price Lists to Room Types (Room Tariff Mapping)

## Purpose

Enable billing administrators to attach daily tariffs, nursing charges, ICU monitoring charges, and package rates to room types so that room rent and related charges are billed correctly. Tariffs are payer-aware (Cash / Corporate / TPA) and date-effective, supporting Indian hospital billing workflows.

## Scope

- Map room types (Healthcare Service Unit Type) to ERPNext Price Lists
- Define per-charge-type line items (Room Rent, Nursing Charge, ICU Monitoring, etc.)
- Differentiate tariffs by payer type: Cash, Corporate, TPA
- Support date-effective validity windows, including open-ended tariffs
- Prevent overlapping active tariff periods for the same room type + payer combination
- Provide a tariff resolution service for downstream billing engines
- Workspace integration for quick access

## Reused Standard DocTypes

| DocType | How Used |
|---------|----------|
| Healthcare Service Unit Type | The "room type" dimension; linked from Room Tariff Mapping |
| Price List | ERPNext selling price list, linked per tariff mapping |
| Item | Individual billable charge items (Room Rent item, Nursing Charge item, etc.) |
| Company | Tariffs are scoped per company |
| Customer | Optional payer entity for Corporate and TPA payer types |

## New Custom DocTypes

| DocType | Module | Purpose |
|---------|--------|---------|
| Room Tariff Mapping | Alcura IPD Extensions | Maps room type + payer type + validity period to a price list and charge items |
| Room Tariff Item | Alcura IPD Extensions | Child table holding individual charge-type line items with rate and billing frequency |

## Fields Added to Standard DocTypes

None. Room Tariff Mapping links to standard doctypes via Link fields. The `default_price_list` custom field on Healthcare Service Unit Type (from US-A2) is used as a convenience auto-fetch source.

## Workflow States

Not applicable. Room Tariff Mapping is a non-submittable master. Active/inactive status is controlled via the `is_active` check field. The `amended_from` field tracks manual amendment lineage.

## Permissions

| Role | Read | Write | Create | Delete |
|------|------|-------|--------|--------|
| Healthcare Administrator | Yes | Yes | Yes | Yes |
| Accounts Manager | Yes | Yes | No | No |
| Nursing User | Yes | No | No | No |
| Physician | Yes | No | No | No |

## Validation Logic

1. **Room type inpatient check**: Room type must have `inpatient_occupancy=1`.
2. **Date range**: `valid_to >= valid_from` when `valid_to` is set.
3. **Payer required for Corporate/TPA**: `payer` is mandatory when `payer_type` is not Cash.
4. **Payer cleared for Cash**: `payer` is automatically cleared when `payer_type=Cash`.
5. **At least one tariff item**: The `tariff_items` child table must have at least one row.
6. **No duplicate charge types**: Each `charge_type` may appear only once per mapping.
7. **Overlap prevention**: For the same `(room_type, payer_type, payer, company)` combination, no two active mappings may have overlapping `[valid_from, valid_to]` date ranges. Uses `SELECT ... FOR UPDATE` to prevent race conditions.

## Tariff Resolution Service

Located in `alcura_ipd_ext/services/tariff_service.py`.

### `resolve_tariff(room_type, payer_type, payer, effective_date, company, charge_type)`

Returns the best-matching active tariff mapping as a dict with `name`, `price_list`, `valid_from`, `valid_to`, and `tariff_items`.

Resolution priority:
1. **Exact match**: room_type + payer_type + specific payer + date in validity
2. **Generic payer**: room_type + payer_type + no specific payer + date in validity
3. **Cash fallback**: room_type + Cash + date in validity (only when payer_type != Cash)

### `get_tariff_rate(room_type, charge_type, payer_type, payer, effective_date, company)`

Convenience wrapper that returns the `float` rate for a single charge type, or `0.0` if unresolved.

Both functions are `@frappe.whitelist()` for API access.

## Notifications

None for this story. Future stories may add notifications for:
- Tariff expiry warnings (approaching `valid_to`)
- Tariff change audit alerts

## Reporting Impact

Room Tariff Mapping will feed:
- Active tariff lookups by room type / payer type
- Tariff comparison reports across payer types
- Revenue projection reports based on tariff rates and occupancy
- Billing audit reports verifying correct tariff application

List-view standard filters support filtering by room_type, payer_type, payer, is_active, valid_from, and valid_to.

## Test Cases

See [docs/testing/us-a4-room-tariffs.md](../testing/us-a4-room-tariffs.md).

## Open Questions / Assumptions

1. **Customer for TPA/Corporate payers**: We use ERPNext's standard `Customer` doctype for both Corporate and TPA payer entities. A dedicated TPA Master may be introduced in a future story if needed.
2. **No billing execution**: The tariff resolution service is a lookup API. Actual Sales Invoice line-item creation from tariffs is a future billing story.
3. **UOM defaults to Nos**: Since Frappe sites may not have a standard "Day" UOM, we default to "Nos". The `billing_frequency` field captures the temporal dimension (Per Day, Per Hour, One Time, Per Visit).
4. **Non-submittable master**: Room Tariff Mapping uses `is_active` toggle instead of docstatus workflow. `amended_from` provides manual amendment lineage.
5. **Price List on parent**: All charge items in a mapping share the same Price List context. Per-item price lists are not supported.
6. **Open-ended tariffs**: A tariff with `valid_to=NULL` is treated as indefinite and will block future overlapping tariffs for the same combination until deactivated.
