# Housekeeping TAT Report

## Overview

Script report showing housekeeping turnaround times with ward/cleaning-type breakdowns, SLA breach tracking, and pending task monitoring.

## Type

Script Report (ref doctype: Bed Housekeeping Task)

## Filters

| Filter | Type | Default |
|--------|------|---------|
| Ward | Link (Hospital Ward) | — |
| Cleaning Type | Select | — |
| Status | Select | — |
| From Date | Date | 7 days ago |
| To Date | Date | Today |
| Company | Link (Company) | — |

## Columns

| Column | Type | Notes |
|--------|------|-------|
| Task | Link | Task name |
| Bed | Link | Hospital Bed |
| Ward | Link | Hospital Ward |
| Cleaning Type | Data | Standard / Deep Clean / Isolation Clean / Terminal Clean |
| Status | Data | Pending / In Progress / Completed / Cancelled |
| Trigger | Data | Discharge / Transfer / Manual |
| Created | Datetime | Task creation time |
| Started | Datetime | Cleaning start |
| Completed | Datetime | Cleaning end |
| TAT (min) | Int | Turnaround time in minutes |
| SLA Target (min) | Int | Expected turnaround |
| SLA Breached | Check | Whether SLA was exceeded |

## Access

- Healthcare Administrator
- Nursing User
- IPD Admission Officer

## Files

- `report/housekeeping_tat_report/housekeeping_tat_report.json` — Report definition
- `report/housekeeping_tat_report/housekeeping_tat_report.py` — Data query
- `report/housekeeping_tat_report/housekeeping_tat_report.js` — Filter UI
