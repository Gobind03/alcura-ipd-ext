# US-N1: Nursing Workload by Ward

## Purpose

Provide a ward-level workload summary so nursing superintendents can
deploy staff based on census, patient acuity, charting backlog,
medication administration load, and protocol compliance gaps.

## Scope

Single Script Report with supporting service module. Read-only; no
new doctypes or custom fields.

## Reused Standard Doctypes

- **Inpatient Record** — census and risk flag fields (`custom_fall_risk_level`,
  `custom_pressure_risk_level`, `custom_current_ward`)
- **Patient** — patient identity

## Reused Custom Doctypes

- **Hospital Ward** — ward list (filter by `is_active`, `company`)
- **IPD Bedside Chart** — overdue chart detection (via `charting_service`)
- **IPD MAR Entry** — Scheduled / Missed medication entries
- **Active Protocol Bundle** / **Protocol Step Tracker** — overdue protocol steps

## New Custom Doctypes

None.

## Fields Added

None.

## Service Design

`services/nursing_workload_service.py` provides:

- `get_ward_workload(company, ward)` — returns list of ward-level rows
- `get_workload_totals(rows)` — aggregate totals for report summary

All per-ward counts use batch `GROUP BY` SQL to avoid N+1 patterns.
Overdue chart detection reuses `charting_service.get_overdue_charts()`.

### Workload Score Formula

```
score = census * 1
      + high_acuity * 2
      + overdue_charts * 3
      + overdue_mar * 3
      + overdue_protocol * 2
```

### Acuity Definition

High acuity = `custom_fall_risk_level = 'High'` OR
`custom_pressure_risk_level IN ('High', 'Very High')`.

## Workflow States

N/A (report only).

## Permissions

- Healthcare Administrator
- Nursing User

## Validation Logic

None (read-only report).

## Notifications

None (see `tasks.check_overdue_charts` for overdue alerts).

## Reporting Impact

New report: **Nursing Workload by Ward** in IPD Operations workspace.

## Test Cases

See `docs/testing/us-n1-nursing-workload.md`.

## Open Questions / Assumptions

- Workload score weights are configurable in code but not yet
  exposed as settings. Can be moved to a settings doctype later.
- Overdue protocol steps are counted at the step level, not the bundle
  level.
- Only admitted patients (IR status = Admitted) contribute to census.
