# MAR Schedule Lifecycle

## Overview

Medication Administration Record entries are auto-generated from medication order frequency and presented to nurses via the MAR Board for time-slot-based tracking.

## Entry Generation

When a medication order is placed (`place_order`):

1. If frequency is not PRN, `generate_mar_entries_for_order` is called
2. Computes scheduled times from frequency map and duration
3. Creates MAR entries with `administration_status = "Scheduled"`
4. Each entry gets an auto-computed `shift` (Morning/Afternoon/Night)

### Frequency Map

| Frequency | Daily Times |
|-----------|------------|
| OD | 08:00 |
| BD | 08:00, 20:00 |
| TDS | 06:00, 14:00, 22:00 |
| QID | 06:00, 12:00, 18:00, 00:00 |
| Q4H | Every 4 hours from 00:00 |
| STAT | Single entry at order time |
| PRN | No auto-generation |

## Administration Status Flow

```
Scheduled → Given (nurse administers)
          → Held (with reason)
          → Refused (with reason)
          → Delayed (with reason + minutes)
          → Missed (scheduler marks overdue)
```

## Overdue Detection

`mark_overdue_mar_entries` scheduler task (every 15 min):
- Finds Scheduled entries past `scheduled_time + 60min`
- Sets `administration_status = "Missed"`
- Fires `mar_missed_alert` realtime event

## Order Lifecycle Integration

| Order Event | MAR Impact |
|-------------|-----------|
| Order placed | Generate scheduled entries |
| Order cancelled | Cancel pending entries (mark Missed) |
| Order put on hold | Cancel pending entries |
| Order resumed | New entries can be regenerated |

## MAR Board Display

- **Filter**: Ward, Date, Shift
- **Grid**: Rows = patients (by bed), Columns = time slots
- **Pills**: Color-coded by status
  - Green = Given / Self-Administered
  - Grey = Scheduled
  - Red = Missed
  - Yellow = Held
  - Orange = Delayed
  - Dark Grey = Refused
- **Click** on Scheduled/Delayed pill → action dialog

## Shift Boundaries

| Shift | Start | End |
|-------|-------|-----|
| Morning | 06:00 | 14:00 |
| Afternoon | 14:00 | 22:00 |
| Night | 22:00 | 06:00 (next day) |
