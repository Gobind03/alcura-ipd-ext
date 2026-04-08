# Testing: US-K3 ADT Census Report

## Test File

`alcura_ipd_ext/tests/test_adt_census_service.py`

## Test Class

`TestAdtCensusService`

## Test Scenarios

### 1. Basic Movements

| Test | Description | Expected |
|------|-------------|----------|
| `test_admission_counted` | Admission BML on census date | admissions = 1 |
| `test_discharge_counted` | Discharge BML on census date (admitted day before) | discharges = 1 |
| `test_transfer_in_out` | Transfer from A to B | A: transfers_out = 1; B: transfers_in = 1 |

### 2. Opening Census

| Test | Description | Expected |
|------|-------------|----------|
| `test_opening_census` | Patient admitted yesterday, still in ward | opening_census = 1 |
| `test_opening_census_excludes_discharged_before_midnight` | Discharged yesterday | opening_census = 0 |

### 3. Closing Census Formula

| Test | Description | Expected |
|------|-------------|----------|
| `test_closing_equals_opening_plus_movements` | 1 prior patient + 1 new admission | closing = 2 |

### 4. Same-Day Edge Cases

| Test | Description | Expected |
|------|-------------|----------|
| `test_same_day_admit_discharge` | Admit + discharge same day | admissions=1, discharges=1, closing=0 |
| `test_same_day_admit_transfer` | Admit in A, transfer to B same day | A: admit=1, out=1, closing=0; B: in=1, closing=1 |

### 5. Empty / Filter Cases

| Test | Description | Expected |
|------|-------------|----------|
| `test_empty_day_returns_zeros` | No activity in ward | All counts = 0 |
| `test_ward_filter_limits_results` | Two wards, filter by one | Only filtered ward |

### 6. Totals Computation

| Test | Description | Expected |
|------|-------------|----------|
| `test_totals_computation` | Two ward rows aggregated | Correct sums and net_movement |

### 7. Report Execute

| Test | Description | Expected |
|------|-------------|----------|
| `test_report_execute_returns_structure` | Valid filters | columns, data, 6 summary cards |
| `test_report_chart_structure` | Data available | Stacked bar chart |
| `test_report_empty_no_chart` | No data | chart = None |

## Fixtures

Tests use factory functions to create isolated ward/room/bed/IR/BML records. All tests use `frappe.db.rollback()` in tearDown.

## Coverage

- Service layer: `adt_census_service.py` (get_adt_census, get_adt_totals)
- Report layer: `adt_census.py` (execute)
- Opening census logic with midnight cutoff
- Day movement counting (4 directions)
- Closing census = opening + movements
- Same-day edge cases
- Ward filter isolation
- Empty result handling
