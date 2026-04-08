# US-G2: MAR Schedule Tests

## Test File

`alcura_ipd_ext/tests/test_mar_schedule_service.py`

## Test Classes and Coverage

### TestGenerateFromOrder

| Test | What it validates |
|------|------------------|
| `test_generate_bd_schedule` | BD frequency generates 1-2 entries per day |
| `test_generate_tds_schedule` | TDS frequency generates 3 entries per day |
| `test_stat_order_single_entry` | STAT creates exactly 1 entry |
| `test_prn_no_entries` | PRN creates 0 entries |
| `test_non_medication_no_entries` | Lab Test orders produce no MAR entries |
| `test_no_duplicate_entries` | Second call does not create duplicates |

### TestShiftComputation

| Test | What it validates |
|------|------------------|
| `test_morning_shift` | 06:00-13:59 maps to Morning |
| `test_afternoon_shift` | 14:00-21:59 maps to Afternoon |
| `test_night_shift` | 22:00-05:59 maps to Night |

### TestMarkOverdue

| Test | What it validates |
|------|------------------|
| `test_mark_overdue_entries` | Scheduled entries past grace period get marked Missed |

### TestCancelPendingEntries

| Test | What it validates |
|------|------------------|
| `test_cancel_pending_entries` | All pending entries for an order get cancelled |

### TestWardMARBoard

| Test | What it validates |
|------|------------------|
| `test_board_returns_structure` | Returns dict with patients, status_counts, total |

### TestShiftSummary

| Test | What it validates |
|------|------------------|
| `test_shift_summary_structure` | Returns dict with total, status_counts, patient_count |

## Running

```bash
bench --site <site> run-tests --app alcura_ipd_ext --module alcura_ipd_ext.tests.test_mar_schedule_service
```
