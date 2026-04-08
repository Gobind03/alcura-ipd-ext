# Protocol Compliance Report

## Purpose

Shows compliance scores across activated protocol bundles, filterable
by bundle type, category, unit type (ICU/CICU/MICU), ward, status, and date range. Supports step-level drilldown for quality review.

## Type

Script Report with chart (ref_doctype: Active Protocol Bundle)

## Filters

| Filter | Type | Notes |
|--------|------|-------|
| Protocol Bundle | Link | Optional |
| Category | Select | ICU/Sepsis/Ventilator/Nutrition/Pressure Injury/Fall Prevention/Other |
| Unit Type | Select | ICU/CICU/MICU/NICU/PICU/SICU/HDU — filters wards by service unit type |
| Status | Select | Active/Completed/Discontinued/Expired |
| Ward | Link (Hospital Ward) | Optional |
| From Date | Date | Default: 1 month ago |
| To Date | Date | Default: today |

## Columns

| Column | Type | Width |
|--------|------|-------|
| Active Bundle | Link | 140 (with step detail drilldown icon) |
| Protocol | Link | 200 |
| Category | Data | 100 |
| Patient | Link | 120 |
| Patient Name | Data | 140 |
| Ward | Link | 120 |
| Status | Data | 100 |
| Compliance % | Percent | 110 (color-coded) |
| Total Steps | Int | 90 |
| Completed | Int | 90 |
| Missed | Int | 80 (red pill when >0) |
| Delayed | Int | 80 (orange pill when >0) |
| Activated | Datetime | 160 |

## Report Summary

- Total Bundles
- Avg Compliance (color indicator)
- Full Compliance (count of 100% bundles)
- Total Missed Steps (red indicator)
- Delayed Steps (orange indicator)

## Chart

Bar chart showing average compliance percentage by protocol category.

## Step Detail Drilldown

Click the list icon on any Active Bundle row to open a dialog showing all Protocol Step Tracker rows with: sequence, step name, type, status (color-coded), mandatory flag, due at, completed at, delay (minutes), and notes.

## Permissions

- Healthcare Administrator
- ICU Administrator
- Physician
