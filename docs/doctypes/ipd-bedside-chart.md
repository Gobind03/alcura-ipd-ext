# IPD Bedside Chart

## Purpose

Per-admission chart schedule linking an Inpatient Record to a Chart Template. Tracks recording frequency, lifecycle status, and overdue detection.

## Type

Regular DocType. Named by series `BSC-.#####`.

## Key Fields

| Field | Type | Notes |
|-------|------|-------|
| patient | Link: Patient | Indexed |
| inpatient_record | Link: Inpatient Record | Indexed |
| chart_template | Link: IPD Chart Template | |
| chart_type | Data | Fetched from template, indexed |
| frequency_minutes | Int | Overridable from template default |
| status | Select | Active / Paused / Discontinued |
| started_at / started_by | Datetime / Link: User | |
| discontinued_at / discontinued_by | Datetime / Link: User | Set on discontinuation |
| last_entry_at | Datetime | Updated on each entry |
| total_entries | Int | Count of active entries |
| ward / bed | Link | Denormalized from IR |

## Virtual Properties

- `next_due_at`: `last_entry_at + frequency_minutes` (or `started_at` if no entries)
- `is_overdue`: `True` if status is Active and `now > next_due_at`
- `overdue_minutes`: minutes past due

## Status Transitions

Active -> Paused -> Active (resume)
Active -> Discontinued
Paused -> Discontinued

## Validation

- Frequency >= 1 minute
- Status transitions validated (no Discontinued -> Active)
- One active chart per template per admission

## Permissions

Create/Write: Nursing User, Physician, Healthcare Administrator. Delete: Healthcare Administrator only.
