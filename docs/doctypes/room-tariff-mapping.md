# Room Tariff Mapping

## Overview

Maps a room type (Healthcare Service Unit Type) to payer-differentiated, date-effective tariff charge items. Each mapping connects a room type, payer type, and optional specific payer to a Price List and a set of charge-type line items with rates and billing frequencies.

## Schema

### Room Tariff Mapping (Parent)

| Fieldname | Type | Options | Required | Indexed | Notes |
|-----------|------|---------|----------|---------|-------|
| naming_series | Select | RTM-.##### | — | — | Hidden; auto-generated |
| room_type | Link | Healthcare Service Unit Type | Yes | Yes | Must have inpatient_occupancy=1 |
| company | Link | Company | Yes | Yes | Default: user's company |
| payer_type | Select | Cash, Corporate, TPA | Yes | Yes | Drives payer field visibility |
| payer | Link | Customer | Conditional | Yes | Required for Corporate/TPA; hidden for Cash |
| valid_from | Date | — | Yes | Yes | Start of tariff validity |
| valid_to | Date | — | No | Yes | End of validity; NULL = open-ended |
| price_list | Link | Price List | Yes | — | ERPNext selling price list |
| tariff_items | Table | Room Tariff Item | Yes | — | At least one row required |
| is_active | Check | — | — | Yes | Default: 1 |
| amended_from | Link | Room Tariff Mapping | — | — | Manual amendment tracking |
| description | Small Text | — | — | — | Free-text notes |

### Room Tariff Item (Child Table)

| Fieldname | Type | Options | Required | Notes |
|-----------|------|---------|----------|-------|
| charge_type | Select | Room Rent, Nursing Charge, ICU Monitoring Charge, Oxygen Charge, Doctor Visit Charge, Diet Charge, Other | Yes | Unique per mapping |
| item_code | Link | Item | Yes | ERPNext billable item |
| item_name | Data | — | — | Fetched from item_code; read-only |
| rate | Currency | — | Yes | Per-unit tariff rate |
| uom | Link | UOM | — | Default: Nos |
| billing_frequency | Select | Per Day, Per Hour, One Time, Per Visit | — | Default: Per Day |
| description | Small Text | — | — | Free-text notes |

## Naming

Auto-named via naming series: `RTM-00001`, `RTM-00002`, etc.

## Permissions

| Role | Read | Write | Create | Delete |
|------|------|-------|--------|--------|
| Healthcare Administrator | Yes | Yes | Yes | Yes |
| Accounts Manager | Yes | Yes | No | No |
| Nursing User | Yes | No | No | No |
| Physician | Yes | No | No | No |

## Validations

### Server-Side (room_tariff_mapping.py)

1. **Room type inpatient check**: `Healthcare Service Unit Type.inpatient_occupancy` must be 1.
2. **Date range**: `valid_to >= valid_from` when both are set.
3. **Payer sanitisation**: Cleared for Cash; required for Corporate/TPA.
4. **Tariff items required**: At least one child row.
5. **Unique charge types**: No duplicate `charge_type` within `tariff_items`.
6. **Overlap prevention**: For the same `(room_type, payer_type, payer, company)`, active mappings must not have overlapping date ranges. Uses `FOR UPDATE` locking.

### Client-Side (room_tariff_mapping.js)

- `room_type` filtered to `inpatient_occupancy=1`
- `payer` filtered to enabled customers; visibility toggled by `payer_type`
- `price_list` filtered to selling price lists
- `item_code` in child table filtered to non-disabled items
- Auto-fetches `default_price_list` from room type when `price_list` is empty

## Overlap Detection Algorithm

Two date ranges `[S_a, E_a]` and `[S_b, E_b]` overlap when:
- `S_a <= E_b` (or `E_b` is NULL) **AND**
- `S_b <= E_a` (or `E_a` is NULL)

This handles open-ended tariffs (NULL `valid_to`) correctly.

## Tariff Resolution

See `alcura_ipd_ext/services/tariff_service.py`:

- `resolve_tariff()` — returns best-matching mapping dict with tariff items
- `get_tariff_rate()` — returns rate for a specific charge type

Resolution priority: exact payer match > generic payer type > Cash fallback.

## Related DocTypes

- **Healthcare Service Unit Type** — room type dimension (US-A2)
- **Hospital Room** — links to room type, inherits tariff context
- **Hospital Bed** — inherits room type from room
- **Price List** — ERPNext standard
- **Item** — ERPNext standard billable items

## Workspace

Available under **IPD Setup** workspace in the "Tariffs" card section.
