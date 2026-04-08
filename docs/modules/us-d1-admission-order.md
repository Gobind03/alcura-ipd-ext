# US-D1: Create Admission from Practitioner Order

## Purpose

Enable doctors to order IPD admission directly from a submitted Patient Encounter, creating a traceable Inpatient Record with extended admission order details (priority, requested ward, expected LOS, notes).

## Scope

- Client script on Patient Encounter with "Order IPD Admission" dialog
- Whitelisted API for creating Inpatient Records from encounters
- Custom fields on Patient Encounter (back-link) and Inpatient Record (admission order details)
- Timeline comments on encounter, IR, and patient
- Payer profile carry-over from patient defaults

## Reused Standard DocTypes

| DocType | How Used |
|---------|----------|
| Patient Encounter | Source document — practitioner triggers admission from submitted encounter |
| Inpatient Record | Target — created in "Admission Scheduled" status with custom fields |
| Patient | Patient reference and payer profile lookup |
| Healthcare Practitioner | Carried as `primary_practitioner` on the IR |
| Medical Department | Carried from encounter to IR |

## New Custom DocTypes

None — this story extends existing doctypes via custom fields only.

## Fields Added

### Patient Encounter

| Fieldname | Type | Label | Notes |
|-----------|------|-------|-------|
| `custom_ipd_admission_section` | Section Break | IPD Admission Order | Collapsible |
| `custom_ipd_admission_ordered` | Check | IPD Admission Ordered | Read-only |
| `custom_ipd_inpatient_record` | Link → Inpatient Record | Inpatient Record | Read-only |

### Inpatient Record

| Fieldname | Type | Label | Notes |
|-----------|------|-------|-------|
| `custom_admission_order_section` | Section Break | Admission Order Details | |
| `custom_requesting_encounter` | Link → Patient Encounter | Requesting Encounter | Read-only, indexed |
| `custom_admission_priority` | Select | Admission Priority | Routine/Urgent/Emergency |
| `custom_expected_los_days` | Int | Expected LOS (Days) | |
| `custom_column_break_admission_1` | Column Break | | |
| `custom_requested_ward` | Link → Hospital Ward | Requested Ward | |
| `custom_admission_notes` | Small Text | Admission Notes | |

## Workflow States

No formal workflow — a one-shot operation:
1. Encounter submitted → Doctor clicks "Order IPD Admission"
2. Dialog captures priority, ward, LOS, notes
3. API creates IR in "Admission Scheduled" status
4. Encounter back-linked to IR

## Permissions

| Action | Required Role |
|--------|--------------|
| Order admission | Read on Patient Encounter + Create on Inpatient Record |
| View admission details | Read on Inpatient Record |

## Validation Logic

1. Patient Encounter must be submitted (`docstatus == 1`)
2. Encounter must not have an existing admission order (`custom_ipd_admission_ordered == 0`)
3. Encounter must have a patient linked
4. Duplicate admission prevention: one IR per encounter

## Notifications

- Timeline comment on Inpatient Record with priority, ward, and encounter reference
- Timeline comment on Patient Encounter with IR link
- Timeline comment on Patient record

## Reporting Impact

- Inpatient Record list can be filtered by `custom_admission_priority`
- Requesting encounter link enables traceability audits

## Test Cases

See [testing/us-d1-admission-order.md](../testing/us-d1-admission-order.md).

## Open Questions / Assumptions

1. The standard "Order Admission" button on Patient Encounter remains available; our "Order IPD Admission" is an alternative that captures additional data.
2. Expected discharge is calculated from today + LOS days when LOS is provided.
3. Patient's default payer profile is automatically carried to the IR.
4. The primary practitioner on the IR is set from the encounter's practitioner.
