# US-E4: Maintain Bedside Charts

## Purpose

Provide digital bedside charts for vitals, intake-output, medication administration, nursing notes, glucose charting, pain charting, ventilator charting, and fluid balance so that all bedside care is documented in one place.

## Scope

- Template-driven parameter charts (Vitals, Glucose, Pain, Ventilator)
- Dedicated doctypes for structurally distinct charts (I/O, MAR, Nursing Notes)
- Configurable recording frequency per chart instance
- Overdue entry detection with scheduled notifications
- Correction/addendum workflow with full audit trail
- Fluid balance computation (hourly, shift-wise, daily)
- Graph/chart visualization for vitals trends
- Integration with Inpatient Record via custom fields and dashboard
- Fixture data for 5 standard chart templates

## Reused Standard DocTypes

| DocType | How Used |
|---------|----------|
| Patient | Patient reference on all chart entries |
| Inpatient Record | IPD admission linkage; custom fields for chart counts |
| Hospital Ward | Ward denormalization on entries |
| Hospital Bed | Bed denormalization on entries |
| User | Audit: recorded_by, started_by, administered_by |
| Item | Optional medication item link on MAR entries |
| Healthcare Practitioner | Critical alert target via IR.primary_practitioner |
| Notification Log | In-app notifications for overdue and critical alerts |

## New Custom DocTypes

| DocType | Purpose |
|---------|---------|
| IPD Chart Template | Master template for parameter-based charts |
| IPD Chart Template Parameter | Child table: parameter definitions with validation ranges |
| IPD Bedside Chart | Per-admission chart schedule with frequency and overdue tracking |
| IPD Chart Entry | Individual parameter-based recording event |
| IPD Chart Observation | Child table: captured parameter values with critical flagging |
| IPD IO Entry | Intake/Output fluid recording |
| IPD Nursing Note | Narrative nursing documentation with addendum support |
| IPD MAR Entry | Medication administration record |

See individual doctype docs under `docs/doctypes/`.

## Fields Added to Standard DocTypes

### Inpatient Record

| Field | Type | Notes |
|-------|------|-------|
| `custom_charting_section` | Section Break | Collapsible |
| `custom_active_charts_count` | Int | Read-only |
| `custom_overdue_charts_count` | Int | Read-only |
| `custom_last_vitals_at` | Datetime | Read-only |

## Workflow States

### IPD Bedside Chart

| Status | Meaning |
|--------|---------|
| Active | Chart is being recorded at the configured frequency |
| Paused | Temporarily suspended (e.g., patient in procedure) |
| Discontinued | Permanently stopped |

### Chart Entry / IO Entry / MAR Entry

| Status | Meaning |
|--------|---------|
| Active | Current valid entry |
| Corrected | Superseded by a correction entry |

### Nursing Note

| Status | Meaning |
|--------|---------|
| Active | Current valid note |
| Amended | Superseded by an addendum |

## Permissions

| DocType | Create/Write | Read | Delete |
|---------|-------------|------|--------|
| IPD Chart Template | Healthcare Administrator | Nursing User, Physician, Healthcare Administrator | Healthcare Administrator |
| IPD Bedside Chart | Nursing User, Physician, Healthcare Administrator | All three | Healthcare Administrator |
| IPD Chart Entry | Nursing User, Physician | All three | None |
| IPD IO Entry | Nursing User | All three | None |
| IPD Nursing Note | Nursing User | All three | None |
| IPD MAR Entry | Nursing User | All three | None |

## Validation Logic

1. Chart templates require at least one parameter; duplicate parameter names blocked
2. Select parameters must have options defined
3. Chart entries blocked for Discontinued/Paused charts
4. Correction entries require a reason; double corrections blocked
5. I/O volume must be > 0
6. MAR hold_reason required when Held; refusal_reason when Refused
7. Nursing note text required; addendum reason required for addenda
8. Entry datetime cannot be in the future (5-minute tolerance)
9. Critical observations auto-flagged from template thresholds

## Notifications

| Trigger | Action |
|---------|--------|
| Critical observation | Realtime event + in-app notification to attending physician |
| Chart overdue > threshold | In-app notification to ward nurses (every 15 min) |
| Critical nursing note | Realtime event for charge nurse awareness |
| MAR missed | Realtime event for nurse alert |

## Reporting Impact

- **Vitals Trend**: Line chart of vital parameters over time
- **IPD Fluid Balance**: Hourly/shift-wise intake vs output with running balance
- **Overdue Charts**: Ward-level overdue chart monitor
- **MAR Summary**: Medication administration compliance with pie chart
- IPD Desk workspace updated with all charting links and reports
- Inpatient Record dashboard shows Bedside Charts group

## Test Cases

See [testing/us-e4-bedside-charts.md](../testing/us-e4-bedside-charts.md).

## Open Questions / Assumptions

1. MAR entries are standalone — full order-to-administration lifecycle deferred.
2. Ventilator charting uses the template-driven parameter model, not a separate doctype.
3. Fluid Balance is always computed, never stored.
4. Standard Vital Signs doctype is NOT reused; optional sync is future work.
5. Graph rendering uses Frappe Charts (built-in).
6. Chart entries are not submittable — uses explicit status field for correction model.
7. Entries cannot be deleted via UI.
8. Shift definitions use fixed 8-hour blocks (06-14, 14-22, 22-06).
