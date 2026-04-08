# Report: Bed Occupancy Dashboard

## Overview

A Script Report that provides aggregate occupancy statistics by ward or room type, designed for operations managers to monitor hospital capacity at a glance. Includes occupancy %, average length of stay, bed turnaround KPIs, and a bar chart visualization.

## Type

Script Report (server-side Python + client-side JS)

## Module

Alcura IPD Extensions

## Reference DocType

Hospital Bed

## Access Roles

- Healthcare Administrator
- Nursing User
- Physician

## Filters

| Filter | Type | Default | Description |
|--------|------|---------|-------------|
| Company | Link (Company) | User default | Filter by company |
| Branch | Data | — | Filter by ward branch/location |
| Ward | Link (Hospital Ward) | — | Filter to specific ward |
| Room Type | Link (Healthcare Service Unit Type) | — | Filter by room type |
| Critical Care Only | Check | 0 | Show only ICU/HDU wards |
| Group By | Select (Ward / Room Type) | Ward | Toggle aggregation level |

## Columns (Ward View)

| Column | Type | Width | Notes |
|--------|------|-------|-------|
| Ward | Link (Hospital Ward) | 160 | |
| Ward Name | Data | 140 | |
| Classification | Data | 100 | Ward classification (General, ICU, etc.) |
| Total | Int | 70 | Total active beds |
| Occupied | Int | 80 | Currently occupied beds |
| Vacant | Int | 70 | Vacant, clean, no holds |
| Reserved | Int | 80 | Reserved beds |
| Blocked | Int | 70 | Maintenance, infection, dirty, cleaning |
| Cleaning | Int | 80 | Beds with cleaning in progress |
| Maintenance | Int | 90 | Beds on maintenance hold |
| Occupancy % | Percent | 100 | occupied / total * 100; color-coded |
| Avg LOS (days) | Float | 110 | Average length of stay for admitted patients |
| Avg Turnaround (min) | Float | 140 | Average housekeeping turnaround time |

## Columns (Room Type View)

Same as ward view but first column is Room Type (Link to Healthcare Service Unit Type). Does not include LOS or turnaround columns.

## Summary Cards

| Card | Color Logic | Description |
|------|-------------|-------------|
| Total Beds | Blue | All active beds matching filters |
| Overall Occupancy % | Green/Orange/Red by threshold | Hospital-wide occupancy |
| ICU Occupancy % | Green/Orange/Red by threshold | Critical care wards only |
| Avg LOS (days) | Blue | Average across all wards |
| Avg Turnaround (min) | Blue | Average housekeeping turnaround |

## Chart

Horizontal bar chart of occupancy % by ward (or room type), using Frappe's built-in chart rendering.

## Server-Side Implementation

**Service:** `alcura_ipd_ext/services/occupancy_metrics_service.py`

- `get_ward_occupancy_summary(filters)` — GROUP BY ward aggregation
- `get_room_type_occupancy_summary(filters)` — GROUP BY room type
- `get_critical_care_summary(filters)` — ICU/HDU subset
- `get_avg_los_by_ward(filters)` — AVG(DATEDIFF) on Inpatient Record
- `get_bed_turnaround_by_ward(filters)` — AVG(turnaround_minutes) from Bed Housekeeping Task
- `get_overall_summary(filters)` — hospital-wide totals

**Report:** `alcura_ipd_ext/alcura_ipd_ext/report/bed_occupancy_dashboard/bed_occupancy_dashboard.py`

Delegates to the service for data and summary computation.

## Client-Side Implementation

**File:** `alcura_ipd_ext/alcura_ipd_ext/report/bed_occupancy_dashboard/bed_occupancy_dashboard.js`

- Group By toggle between Ward and Room Type
- Color-coded formatter for occupancy % (green < 70%, orange 70-90%, red > 90%)
- ICU/HDU classification highlighted in red
- Refresh button

## Performance

- All aggregation uses GROUP BY in single SQL queries (no N+1)
- LOS computed via SQL AVG(DATEDIFF), not row-by-row
- Hospital Bed has indexes on: hospital_ward, service_unit_type, occupancy_status, company, is_active

## Reused Standard DocTypes

- Hospital Bed
- Hospital Ward
- Hospital Room
- Inpatient Record
- Healthcare Service Unit Type
- Bed Housekeeping Task

## New Custom DocTypes

None.
