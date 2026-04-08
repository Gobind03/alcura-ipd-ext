# Testing: US-B1 — Show Live Available Beds by Room Type

## Test File

`alcura_ipd_ext/tests/test_bed_availability_service.py`

## Test Scenarios

### 1. Basic Availability

| # | Scenario | Expected |
|---|----------|----------|
| 1.1 | Vacant, clean, active beds | Appear in results |
| 1.2 | Occupied beds (show_unavailable=0) | Excluded |
| 1.3 | Occupied beds (show_unavailable=1) | Included |
| 1.4 | Inactive beds | Always excluded |

### 2. Policy Exclusions

| # | Scenario | Expected |
|---|----------|----------|
| 2.1 | Dirty beds, exclude_dirty_beds=1 | Excluded |
| 2.2 | Dirty beds, exclude_dirty_beds=0 | Included |
| 2.3 | Cleaning beds, exclude_cleaning_beds=1 | Excluded |
| 2.4 | Maintenance-hold beds, exclude_maintenance_beds=1 | Excluded |
| 2.5 | Infection-blocked beds, exclude_infection_blocked=1 | Excluded |

### 3. User Filters

| # | Scenario | Expected |
|---|----------|----------|
| 3.1 | Filter by ward | Only beds in that ward |
| 3.2 | Filter by room type | Only beds of that room type |
| 3.3 | Filter by floor | Only beds on that floor |
| 3.4 | Critical care only | Only ICU/HDU ward beds |
| 3.5 | Isolation only | Only isolation-capable ward beds |
| 3.6 | Gender=Male Only (Strict) | Male Only + No Restriction beds |
| 3.7 | Gender=Male Only (Ignore) | All beds regardless of restriction |

### 4. Availability Labels

| # | Scenario | Expected Label |
|---|----------|----------------|
| 4.1 | Vacant + Clean + No holds | "Available" |
| 4.2 | Occupied | "Occupied" |
| 4.3 | Maintenance hold | "Maintenance" |
| 4.4 | Dirty housekeeping | "Dirty" |

### 5. Payer Eligibility

| # | Scenario | Expected |
|---|----------|----------|
| 5.1 | Strict policy + no tariff for room type | Bed excluded |
| 5.2 | Advisory policy + no tariff for room type | Bed included, payer_eligible="No" |
| 5.3 | Advisory policy + tariff exists | payer_eligible="Yes", daily_rate populated |
| 5.4 | Ignore policy | No tariff check, daily_rate=None |

### 6. Summary Counts

| # | Scenario | Expected |
|---|----------|----------|
| 6.1 | 4 beds: 1 occupied, 1 dirty, 1 maintenance, 1 clean | total=4, occupied=1, blocked=2, available=1 |

### 7. Edge Cases

| # | Scenario | Expected |
|---|----------|----------|
| 7.1 | No matching beds | Empty list |
| 7.2 | No matching beds for summary | All counts = 0 |

### 8. Report Integration

| # | Scenario | Expected |
|---|----------|----------|
| 8.1 | `execute({})` | Returns (columns, data, None, None, summary) |
| 8.2 | With payer_type filter | Daily Rate and Payer Eligible columns present |
| 8.3 | Without payer_type filter | Payer columns absent |
