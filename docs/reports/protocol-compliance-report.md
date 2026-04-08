# Protocol Compliance Report

## Purpose

Shows compliance scores across activated protocol bundles, filterable
by bundle type, ward, status, and date range.

## Type

Script Report (ref_doctype: Active Protocol Bundle)

## Filters

| Filter | Type | Notes |
|--------|------|-------|
| Protocol Bundle | Link | Optional |
| Status | Select | Active/Completed/Discontinued/Expired |
| Ward | Link (Hospital Ward) | Optional |
| From Date | Date | Default: 1 month ago |
| To Date | Date | Default: today |

## Columns

| Column | Type | Width |
|--------|------|-------|
| Active Bundle | Link | 140 |
| Protocol | Link | 200 |
| Category | Data | 100 |
| Patient | Link | 140 |
| Ward | Link | 120 |
| Status | Data | 100 |
| Compliance % | Percent | 110 |
| Total Steps | Int | 90 |
| Completed | Int | 90 |
| Missed | Int | 80 |
| Activated | Datetime | 160 |

## Permissions

- Healthcare Administrator
- ICU Administrator
- Physician
