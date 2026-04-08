# Report: ADT Census

## Overview

A Script Report that provides a daily Admission-Discharge-Transfer census, showing opening count, admissions, transfers in/out, discharges, deaths, and closing count per ward. Designed for medical superintendents and operations managers to monitor daily patient flow and ward census.

## Type

Script Report (server-side Python + client-side JS)

## Module

Alcura IPD Extensions

## Reference DocType

Inpatient Record

## Access Roles

- Healthcare Administrator
- Nursing User
- Physician

## Filters

| Filter | Type | Default | Required | Description |
|--------|------|---------|----------|-------------|
| Date | Date | Today | Yes | Census date |
| Ward | Link (Hospital Ward) | — | No | Filter to specific ward |
| Consultant | Link (Healthcare Practitioner) | — | No | Filter by primary practitioner |
| Company | Link (Company) | User default | No | Company filter |
| Branch | Data | — | No | Ward branch filter |

## Columns

| Column | Type | Width | Notes |
|--------|------|-------|-------|
| Ward | Link (Hospital Ward) | 160 | |
| Ward Name | Data | 140 | |
| Opening | Int | 80 | Patients in ward at midnight |
| Admissions | Int | 90 | New admissions during day |
| Transfers In | Int | 90 | Patients transferred into ward |
| Transfers Out | Int | 100 | Patients transferred out of ward |
| Discharges | Int | 90 | Patients discharged from ward |
| Deaths | Int | 70 | Deaths (subset of discharges); red when > 0 |
| Closing | Int | 80 | Closing census; color-coded vs opening |

## Summary Cards

| Card | Indicator | Description |
|------|-----------|-------------|
| Opening Census | Blue | Total opening count |
| Total Admissions | Green | Sum of admissions |
| Total Discharges | Orange | Sum of discharges |
| Deaths | Red | Sum of deaths |
| Closing Census | Blue | Total closing count |
| Net Movement | Green/Red | admissions + transfers_in - transfers_out - discharges |

## Chart

Stacked bar chart by ward showing admissions (green) and discharges (red).

## Census Logic

For a given date D and ward W:

- **Opening Census**: count of IRs whose last BML entry before midnight of D has `to_ward = W` and `movement_type != 'Discharge'`
- **Admissions**: BML `Admission` entries with `to_ward = W` within day D
- **Transfers In**: BML `Transfer` entries with `to_ward = W` within day D
- **Transfers Out**: BML `Transfer` entries with `from_ward = W` within day D
- **Discharges**: BML `Discharge` entries with `from_ward = W` within day D
- **Deaths**: subset of discharges where linked `IPD Discharge Advice` has `discharge_type = 'Death'`
- **Closing Census**: opening + admissions + transfers_in - transfers_out - discharges

## Edge Cases

- Same-day admission + discharge: counted in both admissions and discharges
- Same-day admission + transfer: admission in ward A, transfer out of A, transfer in to B
- Multiple transfers: each counted separately
- Patient transferred between wards then back: counted as transfer out + transfer in for each ward

## Interactive Features

- "Previous Day" / "Next Day" buttons for quick date navigation
- Closing census color-coded: red when higher than opening, green when lower

## Server-Side Implementation

**Service:** `alcura_ipd_ext/services/adt_census_service.py`

- `get_adt_census(filters)` — main entry point returning per-ward census rows
- `get_adt_totals(rows)` — aggregate totals computation
- Internal: `_compute_opening_census()`, `_compute_day_movements()`, `_compute_deaths()`

**Report:** `alcura_ipd_ext/alcura_ipd_ext/report/adt_census/adt_census.py`

## Performance

- Opening census uses a correlated subquery with MAX(movement_datetime) — indexed on inpatient_record and movement_datetime
- Day movements use four targeted queries grouped by ward (one per movement direction)
- Deaths use JOIN to IPD Discharge Advice on inpatient_record
- All queries use indexed fields: movement_type, movement_datetime, from_ward, to_ward, company

## Reused Standard DocTypes

- Bed Movement Log (all movement data)
- Inpatient Record (patient admission context)
- Hospital Ward (ward dimension)
- IPD Discharge Advice (death classification)

## New Custom DocTypes

None.
