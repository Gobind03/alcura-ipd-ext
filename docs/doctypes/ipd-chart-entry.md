# IPD Chart Entry

## Purpose

Individual recording event for parameter-based charts (Vitals, Glucose, Pain, Ventilator). Each entry contains a child table of observations matching the template parameters.

## Type

Regular DocType. Named by series `CE-.#####`.

## Key Fields

| Field | Type | Notes |
|-------|------|-------|
| bedside_chart | Link: IPD Bedside Chart | Indexed |
| patient / inpatient_record | Links | Denormalized, indexed |
| chart_type | Data | Denormalized, indexed |
| entry_datetime | Datetime | When observation was taken |
| recorded_by / recorded_by_name | Link: User / Data | |
| status | Select | Active / Corrected (read-only) |
| is_correction | Check | |
| corrects_entry | Link: IPD Chart Entry | Original entry being corrected |
| correction_reason | Small Text | Required if is_correction |
| observations | Table: IPD Chart Observation | |

## Child Table: IPD Chart Observation

| Field | Type |
|-------|------|
| parameter_name | Data |
| numeric_value | Float |
| text_value / select_value | Data |
| uom | Data |
| is_critical | Check (auto-computed) |

## Correction Model

- Original entry marked `Corrected`, new entry created with `is_correction = True`
- Both entries retain timestamps and user attribution
- Double corrections blocked

## Critical Detection

Observations auto-flagged as critical when numeric_value falls outside template's critical_low/critical_high. Critical entries trigger realtime alerts and in-app notifications.

## Validation

- Chart must be Active (not Paused/Discontinued)
- Correction requires reason and valid original entry
- Entry datetime cannot be in the future (5-min tolerance)
