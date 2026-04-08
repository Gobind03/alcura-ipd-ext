# IPD IO Entry

## Purpose

Records intake and output fluid volumes for an inpatient. Each entry represents a single fluid event (e.g., 500mL NS IV, 300mL urine output).

## Type

Regular DocType. Named by series `IO-.#####`.

## Key Fields

| Field | Type | Notes |
|-------|------|-------|
| patient / inpatient_record | Links | Indexed |
| entry_datetime | Datetime | |
| io_type | Select | Intake / Output |
| fluid_category | Select | IV Fluid, Oral, Blood Products, TPN, Urine, Drain, Vomit, Stool, Blood Loss, NG Aspirate, Other |
| fluid_name | Data | Specific fluid name |
| route | Select | IV, Oral, NG Tube, Catheter, Drain, Stoma, Other |
| volume_ml | Float | Required, must be > 0 |
| status | Select | Active / Corrected |

## Fluid Balance

Fluid balance is computed from active I/O entries:
- Daily: sum(intake) - sum(output)
- Hourly: grouped by hour
- Shift-wise: Morning (06-14), Afternoon (14-22), Night (22-06)

Corrected entries are excluded from balance calculations.

## Correction Model

Same as Chart Entry — original marked Corrected, new entry with is_correction flag.

## Permissions

Create/Write: Nursing User. Read: Nursing User, Physician, Healthcare Administrator.
