# Report: Bed Transfer and Housekeeping

## Overview

A combined Script Report showing bed transfers, currently blocked beds, and housekeeping turnaround metrics. Designed for hospital administrators to identify capacity bottlenecks and monitor cleaning efficiency.

## Type

Script Report (server-side Python + client-side JS)

## Module

Alcura IPD Extensions

## Reference DocType

Bed Movement Log

## Access Roles

- Healthcare Administrator
- Nursing User
- Physician

## Filters

| Filter | Type | Default | Required | Description |
|--------|------|---------|----------|-------------|
| From Date | Date | 7 days ago | Yes | Start of reporting period |
| To Date | Date | Today | Yes | End of reporting period |
| Ward | Link (Hospital Ward) | — | No | Filter by ward |
| Consultant | Link (Healthcare Practitioner) | — | No | Filter by ordering practitioner |
| Movement Type | Select (All/Transfer/Discharge) | All | No | Filter movement type |
| Company | Link (Company) | User default | No | Filter by company |
| Branch | Data | — | No | Filter by ward branch |

## Data Table Columns (Transfers)

| Column | Type | Width | Notes |
|--------|------|-------|-------|
| Movement Log | Link (Bed Movement Log) | 120 | |
| Type | Data | 80 | Transfer (blue pill) / Discharge (orange pill) |
| Patient | Link (Patient) | 100 | |
| Patient Name | Data | 150 | |
| From Ward | Link (Hospital Ward) | 130 | |
| From Room | Link (Hospital Room) | 110 | |
| From Bed | Link (Hospital Bed) | 110 | |
| To Ward | Link (Hospital Ward) | 130 | |
| To Room | Link (Hospital Room) | 110 | |
| To Bed | Link (Hospital Bed) | 110 | |
| Reason | Data | 150 | Transfer/discharge reason |
| Consultant | Data | 140 | Ordering practitioner name |
| Date/Time | Datetime | 160 | Movement timestamp |

## Message HTML Sections

### Blocked Beds Table
Current snapshot of beds with maintenance_hold or infection_block set. Columns: Bed, Ward, Room, Reason, Since.

### Housekeeping Summary
Aggregate counts: Total tasks, Completed, Pending, SLA Breached (count and %), Avg TAT.

### TAT by Ward and Cleaning Type
Grouped table showing task count and average TAT per ward per cleaning type (Standard, Deep Clean, Isolation Clean, Terminal Clean).

## Summary Cards

| Card | Indicator Logic | Description |
|------|-----------------|-------------|
| Total Transfers | Blue | Transfer movements in period |
| Blocked Beds | Red if > 0, else Green | Currently blocked bed count |
| Avg Housekeeping TAT (min) | Blue | Average completed turnaround |
| SLA Breach % | Red > 20%, Orange > 10%, Green | Percentage of tasks that breached SLA |

## Performance

- Transfer query uses indexed fields: movement_type, movement_datetime, company, from_ward, to_ward
- Blocked beds query uses indexed fields: is_active, hospital_ward, company
- Housekeeping summary is a single aggregate SQL query
- TAT by ward uses GROUP BY (no N+1)

## Reused Standard DocTypes

- Bed Movement Log (transfer data)
- Hospital Bed (blocked beds snapshot)
- Bed Housekeeping Task (TAT metrics)
- Hospital Ward (filter dimension)

## New Custom DocTypes

None.
