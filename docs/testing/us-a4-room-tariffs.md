# US-A4: Room Tariff Mapping — Test Scenarios

## Test Files

- **Per-doctype**: `alcura_ipd_ext/alcura_ipd_ext/doctype/room_tariff_mapping/test_room_tariff_mapping.py`
- **Central suite**: `alcura_ipd_ext/tests/test_tariff_mapping.py` (re-exports per-doctype tests)

## Test Infrastructure

Tests use `frappe.tests.IntegrationTestCase` with `tearDown` rollback. Factory functions create prerequisite data (Company, Price List, Items, Customers, Healthcare Service Unit Types) idempotently.

## Test Scenarios

### Happy Path

| # | Test | Expected |
|---|------|----------|
| 1 | Create a valid Cash tariff mapping with a Room Rent item | Mapping created; 1 tariff item persisted |
| 2 | Create a tariff with multiple charge types (Room Rent, Nursing, ICU Monitoring) | Mapping created; 3 tariff items persisted |

### Validation

| # | Test | Expected |
|---|------|----------|
| 3 | Room type without inpatient_occupancy=1 | ValidationError |
| 4 | valid_to < valid_from | ValidationError |
| 5 | valid_from == valid_to (single-day) | Accepted |
| 6 | Corporate payer_type without payer | ValidationError |
| 7 | TPA payer_type without payer | ValidationError |
| 8 | Cash payer_type with payer set | Payer auto-cleared to None |
| 9 | Corporate payer_type with valid customer | Accepted |
| 10 | Empty tariff_items | ValidationError |
| 11 | Duplicate charge_type in tariff_items | ValidationError |

### Overlap Prevention

| # | Test | Expected |
|---|------|----------|
| 12 | Two active mappings with overlapping dates, same combo | ValidationError |
| 13 | Two active mappings with non-overlapping dates, same combo | Both accepted |
| 14 | Different payer_types, same room_type, overlapping dates | No conflict |
| 15 | Open-ended tariff (no valid_to) blocks future tariff for same combo | ValidationError |
| 16 | Inactive mapping does not block new overlapping active mapping | New mapping accepted |

### Tariff Resolution

| # | Test | Expected |
|---|------|----------|
| 17 | resolve_tariff with exact payer match | Returns exact mapping |
| 18 | resolve_tariff falls back to Cash when Corporate/TPA not found | Returns Cash mapping |
| 19 | resolve_tariff returns None when no mapping matches | None |
| 20 | resolve_tariff excludes inactive mappings | None (only inactive exists) |
| 21 | resolve_tariff outside validity date range | None |
| 22 | get_tariff_rate returns correct rate for Room Rent | 2000.0 |
| 23 | get_tariff_rate returns 0.0 when no mapping exists | 0.0 |
| 24 | resolve_tariff with charge_type filter returns only matching items | 1 item returned |

### Permissions

| # | Test | Expected |
|---|------|----------|
| 25 | Healthcare Administrator can create tariff mapping | Accepted |
| 26 | Nursing User cannot create tariff mapping | PermissionError |
| 27 | Nursing User can read tariff mapping | Mapping readable |

## Running Tests

```bash
# All tariff tests via bench
bench run-tests --app alcura_ipd_ext --doctype "Room Tariff Mapping"

# Via pytest (from bench directory)
pytest apps/alcura_ipd_ext/alcura_ipd_ext/tests/test_tariff_mapping.py -v
```

## Edge Cases to Monitor

- Concurrent tariff creation (overlap detection relies on FOR UPDATE locking)
- Open-ended tariffs spanning multiple financial years
- Large number of tariff items per mapping (performance)
- Price List currency vs Company default currency consistency (not validated in this story)
