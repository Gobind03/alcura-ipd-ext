# US-E2: Nursing Admission Assessment

## Purpose

Enable staff nurses to record a structured nursing admission assessment including vitals, pain score, allergy status, skin condition, fall risk, Braden score, diet, elimination, mobility, and device lines. High-risk indicators automatically raise tasks and alerts so nursing care can begin immediately.

## Scope

- Extend US-E1 intake assessment templates with diet, elimination, and device lines sections
- Compute risk levels from scored Patient Assessments (Morse Fall, Braden, MUST)
- Persist risk flags on Inpatient Record for dashboard visibility
- Generate ToDo alerts for high-risk patients (fall, pressure injury, nutrition)
- Post allergy alert comments on the IR timeline
- Show risk banners on Inpatient Record, IPD Intake Assessment, and Patient Assessment forms
- Provide a Nursing Risk Summary report for ward-level risk oversight

## Reused Standard DocTypes

| DocType | How Used |
|---------|----------|
| Patient Assessment | Scored assessments trigger risk recalculation on submit |
| Patient Assessment Template | Morse Fall Scale, Braden Scale, MUST template definitions |
| IPD Intake Assessment | Allergy data extracted on completion |
| IPD Intake Assessment Template | Enhanced with diet, elimination, device lines fields |
| Inpatient Record | Custom risk flag fields added |
| ToDo | Alert tasks for high-risk patients |
| Comment | Allergy alert timeline comments |

## New Custom DocTypes

None. US-E2 extends existing doctypes and adds service-layer logic.

## Fields Added to Standard DocTypes

### Inpatient Record

| Field | Type | Notes |
|-------|------|-------|
| `custom_nursing_risk_section` | Section Break | Collapsible section after intake status |
| `custom_fall_risk_level` | Select | Low / Moderate / High; read-only |
| `custom_pressure_risk_level` | Select | No Risk / Low / Moderate / High / Very High; read-only |
| `custom_nutrition_risk_level` | Select | Low / Medium / High; read-only |
| `custom_allergy_alert` | Check | Read-only flag |
| `custom_allergy_summary` | Small Text | Read-only; extracted from intake |
| `custom_risk_flags_updated_on` | Datetime | Read-only timestamp |
| `custom_risk_flags_updated_by` | Link → User | Read-only |

### IPD Intake Assessment Template (via fixtures)

New field sections added to `_COMMON_NURSING_FIELDS`:
- Diet & Nutrition (4 fields)
- Elimination (5 fields)
- Device Lines & Access (9 fields, expanding previous 2-field IV section)

## Workflow States

No new workflow states. Risk flags are computed values, not user-driven state transitions.

## Permissions

| Component | Roles Required |
|-----------|---------------|
| Risk flag fields on IR | Read: Nursing User, Physician, Healthcare Administrator |
| Recalculate Risks API | Write on Inpatient Record |
| Nursing Risk Summary report | Healthcare Administrator, Nursing User, Physician |

## Validation Logic

1. Risk classification uses standard clinical cutoffs (Morse: 0-24/25-44/45+; Braden: 6-9/10-12/13-14/15-18/19+; MUST: 0/1/2+)
2. Risk flags update automatically when a scored Patient Assessment is submitted
3. Risk flags also update when an IPD Intake Assessment is completed (allergy extraction)
4. Alert generation is idempotent — duplicate ToDo alerts are not created

## Notifications

| Trigger | Action |
|---------|--------|
| Fall Risk = High | ToDo assigned to Nursing User: "Fall Prevention Protocol" |
| Pressure Risk = High/Very High | ToDo assigned to Nursing User: "Pressure Injury Prevention" |
| Nutrition Risk = High | ToDo assigned: "Dietician Review Required" |
| Allergy detected | Timeline comment on IR: "ALLERGY ALERT: {details}" |
| Any high risk alert | `frappe.publish_realtime("nursing_risk_alert", ...)` for live notification |

## Reporting Impact

- New report: **Nursing Risk Summary** — filters by company, ward, risk type, minimum level, consultant
- Risk banners displayed on Inpatient Record, IPD Intake Assessment, and Patient Assessment forms
- IPD Desk workspace updated with report link

## Test Cases

See [testing/us-e2-nursing-admission-assessment.md](../testing/us-e2-nursing-admission-assessment.md).

## Open Questions / Assumptions

1. Risk thresholds use published clinical literature values; hospitals may want configurable thresholds in future.
2. ToDo alerts are assigned to the first available Nursing User; ward-specific assignment could be enhanced.
3. Allergy extraction looks for "Known Allergies" and "Allergy Details" field labels in intake responses.
4. Diet and elimination fields are informational — they do not feed into risk scoring.
5. Risk flags on IR are overwritten on each recalculation (latest assessment wins).
6. Patient Assessment must be submittable (docstatus=1) for the on_submit hook to fire.
7. The migration patch adds new fields to existing nursing templates without removing any existing fields.
