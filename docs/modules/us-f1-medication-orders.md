# US-F1: Place Medication Orders from IPD Chart

## Purpose

Enable doctors to prescribe inpatient medications digitally for immediate pharmacy and nursing action.

## Scope

- Medication order creation from Inpatient Record and Patient Encounter
- Drug, dose, route, frequency, schedule, indication, STAT/PRN flags
- Instant pharmacy and nursing notification
- SLA tracking for acknowledgment and dispensing
- Linkage to MAR (Medication Administration Record) entries

## Reused Doctypes

- **Patient Encounter** — source for drug prescriptions via `drug_prescription` child table
- **Item** — medication items linked via `medication_item`
- **Inpatient Record** — context for order placement

## New/Extended Doctypes

- **IPD Clinical Order** — `order_type = "Medication"` with medication-specific fields
- **IPD MAR Entry** — new `clinical_order` Link field bridges administration to order

## Fields (Medication-specific)

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| medication_item | Link (Item) | No | Optional link to stock item |
| medication_name | Data | Yes | Free-text or fetched from item |
| dose | Data | No | e.g., "500" |
| dose_uom | Data | No | e.g., "mg" |
| route | Select | No | Oral/IV/IM/SC/SL/Topical/Inhaled/Rectal/PR/Other |
| frequency | Select | No | Once/OD/BD/TDS/QID/Q4H/.../PRN/STAT/Continuous |
| is_stat | Check | No | Auto-sets urgency to STAT |
| is_prn | Check | No | Requires prn_reason |
| prn_reason | Small Text | Conditional | Required when is_prn = 1 |
| start_datetime | Datetime | No | Schedule start |
| end_datetime | Datetime | No | Schedule end |
| duration_days | Int | No | Duration in days |
| indication | Small Text | No | Clinical indication |
| schedule_instructions | Small Text | No | Additional scheduling notes |

## Workflow

1. **Order placement:** Doctor selects medication via quick-order dialog on IR form or includes in PE prescription
2. **Auto-creation from PE:** On PE submit, `drug_prescription` rows auto-create Clinical Orders
3. **Notification:** Pharmacy User and Nursing User receive Notification Log + realtime event
4. **Acknowledgment:** Pharmacist acknowledges order via Pharmacy Queue
5. **Dispensing:** Pharmacist marks as Dispensed (milestone) then Completed
6. **Administration:** Nurse creates MAR Entry linked to the Clinical Order

## Permissions

| Role | Access |
|------|--------|
| Physician | Create, Read, Write |
| Pharmacy User | Read, Write (for acknowledgment/dispensing) |
| Nursing User | Read |
| Healthcare Administrator | Full |

## Notifications

- **On order creation:** To Pharmacy User + Nursing User
- **On acknowledgment:** To ordering practitioner
- **On completion:** To ordering practitioner + Nursing User

## Test Cases

- Order creation with all fields populated
- STAT order auto-sets urgency
- PRN requires reason validation
- Medication name required validation
- PE drug_prescription auto-creates orders
- IR count updates on create/complete
