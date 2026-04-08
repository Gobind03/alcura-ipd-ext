# US-J1: Initiate Discharge Request

## Purpose

Enables doctors to raise a discharge advice in the system, triggering downstream departments (nursing, billing, pharmacy, TPA) to begin closure tasks. The discharge advice is an operational directive distinct from the clinical discharge summary.

## Scope

- Doctor raises discharge advice with clinical summary, medications, follow-up, diet, and warning signs
- Downstream departments receive notifications
- Expected discharge time feeds into bed planning
- Discharge advice lifecycle: Draft → Advised → Acknowledged → Completed / Cancelled

## Reused Standard DocTypes

- **Inpatient Record** — extended with custom fields for discharge advice linkage
- **Patient Encounter** — existing `custom_ipd_note_type = "Discharge Summary"` for clinical summary
- **Healthcare Practitioner** — consultant reference
- **Patient** — patient reference

## New Custom DocTypes

- **IPD Discharge Advice** — operational trigger for discharge workflow

## Custom Fields Added

On **Inpatient Record**:
- `custom_discharge_advice` (Link to IPD Discharge Advice)
- `custom_discharge_advice_status` (Data, fetch_from)
- `custom_expected_discharge_datetime` (Datetime, fetch_from)
- `custom_nursing_discharge_checklist` (Link to Nursing Discharge Checklist)
- `custom_nursing_discharge_status` (Data, fetch_from)

## Workflow States

| State | Entry Action | Triggers |
|-------|-------------|----------|
| Draft | Advice created | — |
| Advised | Doctor submits | Notifications to nursing, billing, pharmacy, TPA |
| Acknowledged | Nursing/desk acknowledges | Consultant notified |
| Completed | Final discharge processed | Advice marked complete |
| Cancelled | Doctor or admin cancels | IR link cleared, reason recorded |

## Permissions

| Role | Create | Read | Write | Delete |
|------|--------|------|-------|--------|
| Physician | ✓ | ✓ | ✓ | — |
| Nursing User | — | ✓ | ✓ | — |
| Healthcare Administrator | ✓ | ✓ | ✓ | ✓ |
| IPD Billing User | — | ✓ | — | — |
| TPA Desk User | — | ✓ | — | — |

## Validation Logic

- **Server-side**: IR must be `Admitted` or `Discharge Scheduled`; only one active advice per IR; cancellation requires reason; strict state machine transitions
- **Client-side**: Conditional button visibility based on advice status

## Notifications

- On Advised: In-app + realtime to Nursing User, IPD Billing User, Pharmacy User, TPA Desk User (non-cash patients)
- On Acknowledged: In-app to advising consultant
- Realtime event: `ipd_discharge_notification`

## Reporting Impact

- Discharge advice status visible on Inpatient Record dashboard banner
- Aggregate discharge status API (`get_discharge_status`) feeds bedside displays

## Files

| File | Purpose |
|------|---------|
| `doctype/ipd_discharge_advice/ipd_discharge_advice.json` | Schema |
| `doctype/ipd_discharge_advice/ipd_discharge_advice.py` | Controller |
| `doctype/ipd_discharge_advice/ipd_discharge_advice.js` | Client scripts |
| `services/discharge_advice_service.py` | Domain logic |
| `services/discharge_notification_service.py` | Notification logic |
| `api/discharge.py` | Whitelisted endpoints |
| `public/js/inpatient_record.js` | IR discharge buttons/banners |
| `setup/custom_fields.py` | Custom field definitions |

## Open Questions / Assumptions

- Discharge Summary (Patient Encounter note type) remains a separate clinical document created by the doctor independently
- The advice can be raised even if the billing checklist hasn't been created yet
- TPA notifications are only sent for non-Cash payer types
