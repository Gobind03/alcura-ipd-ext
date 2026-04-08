# IPD Discharge Advice

## Overview

Represents a doctor's discharge directive for an admitted patient. Serves as the operational trigger that initiates the discharge workflow across nursing, billing, pharmacy, and TPA departments.

## Module

Alcura IPD Extensions

## Naming

`DDA-.YYYY.-.#####` (e.g., DDA-2026-00001)

## Key Fields

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| inpatient_record | Link (Inpatient Record) | ✓ | Indexed |
| patient | Link (Patient) | ✓ | Indexed |
| consultant | Link (Healthcare Practitioner) | ✓ | Indexed |
| status | Select | ✓ | Draft / Advised / Acknowledged / Completed / Cancelled |
| expected_discharge_datetime | Datetime | ✓ | |
| discharge_type | Select | ✓ | Normal / LAMA / Against Medical Advice / Transfer / Death / Absconded |
| condition_at_discharge | Select | — | Improved / Unchanged / Deteriorated / etc. |
| primary_diagnosis | Small Text | — | |
| discharge_medications | Text Editor | — | Prescriptions to take home |
| follow_up_instructions | Text Editor | — | |
| warning_signs | Text Editor | — | Signs requiring immediate return |

## Audit Fields

- `advised_by`, `advised_on` — set when advice is submitted
- `acknowledged_by`, `acknowledged_on` — set on nursing/desk acknowledgment
- `cancelled_by`, `cancelled_on`, `cancellation_reason` — set on cancellation

## Status Machine

- Draft → Advised (submit_advice)
- Advised → Acknowledged (acknowledge)
- Acknowledged → Completed (complete)
- Draft/Advised → Cancelled (cancel_advice, requires reason)
- Completed, Cancelled → terminal states

## Validations

- IR must be Admitted or Discharge Scheduled
- Only one active (non-cancelled, non-completed) advice per IR
- Cancellation requires reason
- Status transitions enforced server-side

## Controller Methods (Whitelisted)

- `submit_advice()` — transitions to Advised, sends notifications
- `acknowledge()` — transitions to Acknowledged
- `complete()` — transitions to Completed, records actual datetime
- `cancel_advice(reason)` — transitions to Cancelled

## Related DocTypes

- Inpatient Record (parent reference)
- Nursing Discharge Checklist (created on acknowledge)
- Discharge Billing Checklist (created independently)
