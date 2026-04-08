# DocType: IPD Bed Policy

## Overview

Single (settings) DocType that holds hospital-wide bed operation policies. These policies are read by the bed availability service and the Live Bed Board report to determine which beds are shown as available and how filtering rules are applied.

## Type

Single (`issingle = 1`)

## Module

Alcura IPD Extensions

## Fields

### Availability Exclusion Rules

| Fieldname | Type | Default | Description |
|-----------|------|---------|-------------|
| `exclude_dirty_beds` | Check | 1 | Exclude vacant beds with housekeeping status "Dirty" from available count |
| `exclude_cleaning_beds` | Check | 1 | Exclude vacant beds with housekeeping status "In Progress" from available count |
| `exclude_maintenance_beds` | Check | 1 | Exclude beds under maintenance hold from available count |
| `exclude_infection_blocked` | Check | 1 | Exclude beds with active infection block from available count |

### Gender Policy

| Fieldname | Type | Default | Options | Description |
|-----------|------|---------|---------|-------------|
| `gender_enforcement` | Select | Strict | Strict / Advisory / Ignore | How gender restriction is applied during bed filtering |

### Cleaning & Turnaround

| Fieldname | Type | Default | Description |
|-----------|------|---------|-------------|
| `cleaning_turnaround_sla_minutes` | Int | 60 | Expected housekeeping turnaround time in minutes |
| `auto_mark_dirty_on_discharge` | Check | 1 | Auto-set bed to "Dirty" on discharge |

### Reservation

| Fieldname | Type | Default | Description |
|-----------|------|---------|-------------|
| `reservation_timeout_minutes` | Int | 120 | Auto-release reservation after N minutes (future use) |

### Payer Eligibility

| Fieldname | Type | Default | Options | Description |
|-----------|------|---------|---------|-------------|
| `enforce_payer_eligibility` | Select | Advisory | Strict / Advisory / Ignore | How payer tariff eligibility is enforced |

### Ward Buffer

| Fieldname | Type | Default | Description |
|-----------|------|---------|-------------|
| `min_buffer_beds_per_ward` | Int | 0 | Minimum beds to keep unallocated per ward (future use) |

## Permissions

| Role | Read | Write |
|------|------|-------|
| Healthcare Administrator | Yes | Yes |
| Nursing User | Yes | No |
| Physician | Yes | No |

## Controller

**Path:** `alcura_ipd_ext/alcura_ipd_ext/doctype/ipd_bed_policy/ipd_bed_policy.py`

### Validation

- All integer fields (`cleaning_turnaround_sla_minutes`, `reservation_timeout_minutes`, `min_buffer_beds_per_ward`) must be >= 0.

### `get_policy() -> dict`

Module-level function that returns the current policy as a dict with sensible defaults. Uses `frappe.get_cached_doc` for performance. Falls back to hard-coded defaults if the Single has never been saved.

## Client Script

**Path:** `alcura_ipd_ext/alcura_ipd_ext/doctype/ipd_bed_policy/ipd_bed_policy.js`

Minimal: sets a "Settings" page indicator and displays introductory help text.
