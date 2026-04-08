# IPD Fluid Balance Report

## Purpose

Hourly or shift-wise intake vs output fluid balance for a specific admission on a given date.

## Type

Script Report (ref_doctype: IPD IO Entry)

## Filters

| Filter | Type | Required |
|--------|------|----------|
| inpatient_record | Link: Inpatient Record | Yes |
| date | Date | No (default: today) |
| view | Select: Hourly / Shift | No (default: Hourly) |

## Views

### Hourly View

Columns: Hour, Intake (mL), Output (mL), Net (mL), Running Balance (mL).
Bar chart: Intake vs Output by hour.

### Shift View

Columns: Shift name, Start/End hour, Intake, Output, Balance.
Shifts: Morning (06-14), Afternoon (14-22), Night (22-06).

## Data Source

Uses `io_service.get_hourly_balance` and `io_service.get_shift_balance`. Only Active entries are included (Corrected entries excluded).

## Permissions

Healthcare Administrator, Nursing User, Physician.
