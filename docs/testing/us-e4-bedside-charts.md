# US-E4: Bedside Charts — Test Scenarios

## Test Files

- `tests/test_charting_service.py` — Template validation, chart lifecycle, entry recording, correction flow
- `tests/test_io_service.py` — I/O entry validation, correction, fluid balance computation
- `tests/test_mar_service.py` — MAR validation, correction, summary queries
- `tests/test_nursing_note.py` — Note validation, addendum flow, urgency handling
- `tests/test_overdue_charts.py` — Overdue detection, grace period, virtual properties

## Template Validation (test_charting_service.py)

| # | Scenario | Expected |
|---|----------|----------|
| 1 | Template with no parameters | ValidationError |
| 2 | Template with duplicate parameter names | ValidationError "Duplicate" |
| 3 | Select parameter without options | ValidationError |
| 4 | Valid template with multiple parameters | Created successfully |

## Chart Lifecycle (test_charting_service.py)

| # | Scenario | Expected |
|---|----------|----------|
| 5 | Start chart for admitted patient | Chart created with Active status |
| 6 | Start duplicate chart for same template | ValidationError |
| 7 | Status transition Active -> Paused -> Active -> Discontinued | All transitions succeed; discontinued sets timestamps |

## Chart Entry Recording (test_charting_service.py)

| # | Scenario | Expected |
|---|----------|----------|
| 8 | Record normal vitals | Entry created, total_entries updated, no critical |
| 9 | Record critical temperature (>39.5) | Entry flagged critical, alert raised |
| 10 | Record entry for discontinued chart | ValidationError |

## Correction Flow (test_charting_service.py)

| # | Scenario | Expected |
|---|----------|----------|
| 11 | Create correction for active entry | Original marked Corrected, new entry linked |
| 12 | Attempt double correction | ValidationError |
| 13 | Correction without reason | ValidationError |

## I/O Entry (test_io_service.py)

| # | Scenario | Expected |
|---|----------|----------|
| 14 | Volume = 0 | ValidationError |
| 15 | Valid intake entry | Created with Active status |
| 16 | Correction with reason | Original marked Corrected |
| 17 | Correction without reason | ValidationError |

## Fluid Balance (test_io_service.py)

| # | Scenario | Expected |
|---|----------|----------|
| 18 | Daily balance with intake and output | Correct totals and breakdown |
| 19 | Corrected entries excluded | Balance excludes corrected entries |
| 20 | Hourly balance | 24 rows, correct distribution |
| 21 | Shift balance | 3 shift rows, totals match |

## MAR Entry (test_mar_service.py)

| # | Scenario | Expected |
|---|----------|----------|
| 22 | Held without reason | ValidationError |
| 23 | Refused without reason | ValidationError |
| 24 | Given auto-sets timestamp | administered_at populated |
| 25 | Valid scheduled entry | Created successfully |
| 26 | Correction flow | Original marked Corrected |
| 27 | Double correction blocked | ValidationError |

## MAR Summary (test_mar_service.py)

| # | Scenario | Expected |
|---|----------|----------|
| 28 | Summary counts | Correct status_counts breakdown |

## Nursing Note (test_nursing_note.py)

| # | Scenario | Expected |
|---|----------|----------|
| 29 | Empty note text | ValidationError |
| 30 | Valid note creation | Created with Active status |
| 31 | Addendum marks original | Original marked Amended |
| 32 | Addendum without reason | ValidationError |
| 33 | Double addendum blocked | ValidationError |
| 34 | Critical note accepted | Created with urgency = Critical |

## Overdue Detection (test_overdue_charts.py)

| # | Scenario | Expected |
|---|----------|----------|
| 35 | Newly started chart | Not overdue |
| 36 | Chart with stale started_at | Detected as overdue |
| 37 | Grace period applied | Chart within grace not overdue |
| 38 | Discontinued chart | Not overdue regardless of timing |
| 39 | is_overdue virtual property | Returns True when overdue |
| 40 | Paused chart not overdue | is_overdue returns False |
