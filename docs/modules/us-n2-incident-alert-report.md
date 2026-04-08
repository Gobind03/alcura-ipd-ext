# US-N2: Incident and Critical Alert Report

## Purpose

Provide quality managers with a consolidated view of safety and quality
incidents — fall-risk events, missed medications, critical lab/vital
observations, and SLA breaches — so corrective action can be taken.

## Scope

Single Script Report with supporting service module. Read-only; derives
data from existing source records without creating a new incident DocType.

## Reused Standard Doctypes

- **Inpatient Record** — links all incidents to an admission
- **Patient** — patient identity
- **ToDo** — nursing risk alert tasks (created by `nursing_alert_service`)

## Reused Custom Doctypes

- **Hospital Ward** — ward filter
- **IPD MAR Entry** — missed medication events (`administration_status = Missed`)
- **IPD Chart Entry** / **IPD Chart Observation** — critical observations (`is_critical = 1`)
- **IPD Clinical Order** — SLA breaches (`is_sla_breached = 1`)

## New Custom Doctypes

None.

## Fields Added

None.

## Data Sourcing Strategy

Rather than maintaining a separate incident table, the report queries
four source record types and normalizes each into a common row format:

1. **Nursing risk alerts** — `ToDo` with `reference_type = "Inpatient Record"`
   and description containing `NursingRisk:<tag>` markers (embedded by
   `nursing_alert_service`). Classified as Fall Risk / Pressure Risk /
   Nutrition Risk.
2. **Missed medications** — `IPD MAR Entry` with `administration_status = "Missed"`.
3. **Critical observations** — `IPD Chart Entry` joined to `IPD Chart Observation`
   where `is_critical = 1`.
4. **SLA breaches** — `IPD Clinical Order` where `is_sla_breached = 1`.

Common row keys: `incident_datetime`, `incident_type`, `severity`,
`patient`, `patient_name`, `ward`, `description`, `source_doctype`,
`source_name`, `status`.

## Workflow States

N/A (report only).

## Permissions

- Healthcare Administrator
- Nursing User
- Physician

## Validation Logic

None (read-only).

## Notifications

None (source records already have their own notification flows).

## Reporting Impact

New report: **Incident Alert Report** in IPD Operations workspace.

## Test Cases

See `docs/testing/us-n2-incident-alert-report.md`.

## Open Questions / Assumptions

- Critical observations are sourced from all chart types, not limited
  to device-generated entries.
- Severity mapping: ToDo priority -> High/Medium/Low; missed med ->
  Medium; critical observation -> High; SLA breach -> High if STAT/Emergency,
  else Medium.
- Incident status reflects the source record status (e.g. ToDo Open/Closed).
- Each source type query is limited to 500 rows for performance.
