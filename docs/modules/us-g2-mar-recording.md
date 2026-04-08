# US-G2: Medication Administration Record (MAR) Recording

## Purpose

Enable nurses to track due medications via a Medication Administration Record, supporting time-slot-based scheduling, bedside confirmation with status (Given/Held/Refused/Delayed/Missed), shift-based views, and automatic overdue detection.

## Scope

- Auto-generation of Scheduled MAR entries from medication order frequency
- Time-slot grid view (MAR Board) per ward/shift
- Quick-action administration recording
- Overdue detection and missed medication alerts
- PRN (as-needed) on-demand entry creation
- Shift summary for handoff

## Reused DocTypes

| DocType | Usage |
|---------|-------|
| IPD MAR Entry | Extended with Delayed status, shift, delay fields |
| IPD Clinical Order | Source of medication orders for schedule generation |

## Schema Changes to IPD MAR Entry

| Field | Type | Notes |
|-------|------|-------|
| administration_status | Select | Added "Delayed" option |
| delay_reason | Small Text | Required when Delayed |
| delay_minutes | Int | How late the administration was |
| shift | Select (Morning/Afternoon/Night) | Auto-computed from scheduled_time |
| dispense_entry | Link (IPD Dispense Entry) | Links to dispensed medication |

## Frequency-to-Schedule Mapping

| Frequency | Times |
|-----------|-------|
| OD | 08:00 |
| BD | 08:00, 20:00 |
| TDS | 06:00, 14:00, 22:00 |
| QID | 06:00, 12:00, 18:00, 00:00 |
| Q4H | 00:00, 04:00, 08:00, 12:00, 16:00, 20:00 |
| Q6H | 00:00, 06:00, 12:00, 18:00 |
| Q8H | 00:00, 08:00, 16:00 |
| Q12H | 08:00, 20:00 |
| STAT | Immediate (single entry at order time) |
| PRN | No scheduled entries; created on demand |

## Shift Boundaries

| Shift | Start | End |
|-------|-------|-----|
| Morning | 06:00 | 14:00 |
| Afternoon | 14:00 | 22:00 |
| Night | 22:00 | 06:00 (next day) |

## Workflow

```
Medication Order Placed → Generate Scheduled MAR Entries
                        → Entries appear on MAR Board by time slot
                        → Nurse actions: Given / Held / Refused / Delayed
                        → No action within grace period → Scheduler marks Missed
```

## Integration with Clinical Orders

- On `place_order` (Medication, non-PRN): auto-generate MAR entries for full duration
- On `cancel_order` or `hold_order`: cancel all pending Scheduled entries
- On `resume_order`: MAR entries can be regenerated

## MAR Board Page

- Path: `/app/mar-board`
- Filters: Ward, Date, Shift
- Grid: Rows = patients (by bed), Columns = time slots
- Color-coded pills: green=Given, grey=Scheduled, red=Missed, yellow=Held, orange=Delayed
- Click pill → quick-action dialog for administration recording
- Shift summary bar at top

## Scheduler Task

`mark_overdue_mar_entries` runs every 15 minutes:
- Finds Scheduled entries past their time + 60-minute grace period
- Marks them as Missed
- Fires `mar_missed_alert` realtime event

## API Endpoints

| Endpoint | Method |
|----------|--------|
| `alcura_ipd_ext.api.mar.get_due_medications` | GET |
| `alcura_ipd_ext.api.mar.get_ward_mar_board` | GET |
| `alcura_ipd_ext.api.mar.administer_medication` | POST |
| `alcura_ipd_ext.api.mar.create_prn_mar_entry` | POST |
| `alcura_ipd_ext.api.mar.get_shift_summary` | GET |
| `alcura_ipd_ext.api.mar.generate_daily_entries` | POST |

## Test Cases

See `docs/testing/us-g2-tests.md` and `tests/test_mar_schedule_service.py`.
