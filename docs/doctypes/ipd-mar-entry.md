# IPD MAR Entry

## Purpose

Medication Administration Record — tracks whether scheduled medications were given, held, refused, or missed. Supports witness recording for controlled substances.

## Type

Regular DocType. Named by series `MAR-.#####`.

## Key Fields

| Field | Type | Notes |
|-------|------|-------|
| patient / inpatient_record | Links | Indexed |
| medication_name | Data | Required |
| medication_item | Link: Item | Optional |
| dose / dose_uom / route | Data/Select | Dosage details |
| scheduled_time | Datetime | When medication was due |
| administered_at | Datetime | Auto-set when status is Given |
| administration_status | Select | Scheduled, Given, Held, Refused, Missed, Self-Administered |
| hold_reason / refusal_reason | Small Text | Required for respective statuses |
| administered_by / witness | Link: User | |
| site | Data | Injection/IV site |

## Validation

- Hold reason required when status = Held
- Refusal reason required when status = Refused
- administered_at and administered_by auto-set when Given/Self-Administered

## Notifications

Missed status triggers `mar_missed_alert` realtime event.

## Assumptions

MAR entries are standalone recordings. Full order-to-administration lifecycle (linking to Patient Encounter drug_prescription) is deferred to a future story.

## Permissions

Create/Write: Nursing User. Read: Nursing User, Physician, Healthcare Administrator.
