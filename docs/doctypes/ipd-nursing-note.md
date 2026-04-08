# IPD Nursing Note

## Purpose

Narrative nursing documentation with categorization, urgency levels, and addendum support. Covers assessment observations, interventions, handoff notes, and escalations.

## Type

Regular DocType. Named by series `NN-.#####`.

## Key Fields

| Field | Type | Notes |
|-------|------|-------|
| patient / inpatient_record | Links | Indexed |
| note_datetime | Datetime | |
| category | Select | Assessment, Intervention, Response, Handoff, Escalation, General, Other |
| note_text | Text Editor | Required |
| urgency | Select | Routine, Urgent, Critical |
| status | Select | Active / Amended |

## Addendum Model

- Original note marked `Amended`, addendum created with `is_addendum = True`
- Addendum reason required
- Double amendments blocked

## Notifications

Critical urgency notes trigger `critical_nursing_note` realtime event.

## Permissions

Create/Write: Nursing User. Read: Nursing User, Physician, Healthcare Administrator.
