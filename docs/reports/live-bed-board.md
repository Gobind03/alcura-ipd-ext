# Report: Live Bed Board

## Overview

A Script Report that shows real-time bed availability across the hospital, designed for admission desk operations. It supports rich filtering, color-coded status indicators, and payer eligibility information.

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

| Filter | Type | Options | Description |
|--------|------|---------|-------------|
| Ward | Link (Hospital Ward) | Active wards only | Filter beds by ward |
| Room Type | Link (Healthcare Service Unit Type) | Inpatient types only | Filter by room type |
| Floor | Data | Free text | Filter by room floor |
| Critical Care Only | Check | 0/1 | Show only ICU/HDU wards |
| Gender | Select | All / Male Only / Female Only | Filter by bed gender restriction |
| Isolation Only | Check | 0/1 | Show only isolation-capable wards |
| Payer Type | Select | Cash / Corporate / TPA | Enable payer eligibility check |
| Payer | Link (Customer) | Visible when Payer Type is Corporate/TPA | Specific payer for tariff lookup |
| Show Unavailable | Check | 0/1 | Include occupied and blocked beds |

## Columns

| Column | Type | Width | Notes |
|--------|------|-------|-------|
| Bed | Link (Hospital Bed) | 140 | |
| Label | Data | 90 | Bed label / alias |
| Room | Link (Hospital Room) | 130 | |
| Ward | Link (Hospital Ward) | 140 | |
| Room Type | Link (Healthcare Service Unit Type) | 140 | |
| Floor | Data | 60 | |
| Availability | Data | 110 | Color-coded: green=Available, red=Occupied, orange=Maintenance/Dirty, yellow=Cleaning |
| Housekeeping | Data | 100 | Color-coded: green=Clean, orange=Dirty, yellow=In Progress |
| Gender | Data | 90 | Bed gender restriction |
| Maintenance | Check | 50 | |
| Infection | Check | 50 | |
| Equipment | Data | 120 | Equipment notes |
| Daily Rate | Currency | 100 | Only when Payer Type filter is active |
| Payer Eligible | Data | 80 | Only when Payer Type filter is active; green=Yes, red=No |
| Ward Class | Data | 100 | Ward classification |
| Specialty | Link (Medical Department) | 120 | |

## Summary Cards

Displayed above the data table:

| Card | Color | Description |
|------|-------|-------------|
| Total Beds | Blue | All active beds matching ward/room filters |
| Available | Green | Vacant + Clean + No holds |
| Occupied | Red | Currently occupied beds |
| Blocked | Orange | Maintenance, infection, or dirty/cleaning beds |

## Server-Side Implementation

**File:** `alcura_ipd_ext/alcura_ipd_ext/report/live_bed_board/live_bed_board.py`

The `execute(filters)` function delegates to:
- `bed_availability_service.get_available_beds(filters)` for data rows
- `bed_availability_service.get_bed_board_summary(filters)` for summary cards

## Client-Side Implementation

**File:** `alcura_ipd_ext/alcura_ipd_ext/report/live_bed_board/live_bed_board.js`

- Filter definitions with dependent visibility (Payer shows when Payer Type is Corporate/TPA)
- Custom `formatter` for color-coded indicator pills on Availability, Housekeeping, and Payer Eligible columns
- Refresh button in the page header

## Performance

- All filtering happens server-side in a single SQL query (no N+1)
- Payer eligibility uses group-by-room-type tariff lookup (one `resolve_tariff()` call per distinct room type, not per bed)
- Hospital Bed table has indexes on: `hospital_room`, `hospital_ward`, `company`, `service_unit_type`, `occupancy_status`, `housekeeping_status`, `is_active`
