# MAR Summary Report

## Purpose

Medication administration compliance tracking. Shows all MAR entries with status breakdown and pie chart for a given admission and date range.

## Type

Script Report (ref_doctype: IPD MAR Entry)

## Filters

| Filter | Type | Required |
|--------|------|----------|
| inpatient_record | Link: Inpatient Record | No |
| patient | Link: Patient | No |
| administration_status | Select | No |
| ward | Link: Hospital Ward | No |
| from_date / to_date | Date | No (default: today) |

## Columns

Entry link, Patient Name, Medication, Dose, Route, Scheduled Time, Administered At, Status, Ward.

## Visualization

Pie chart showing distribution of administration statuses (Given, Held, Refused, Missed, etc.).

## Permissions

Healthcare Administrator, Nursing User, Physician.
