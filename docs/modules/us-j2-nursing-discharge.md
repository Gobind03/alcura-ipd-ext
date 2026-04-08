# US-J2: Complete Nursing Discharge and Handover

## Purpose

Provides nurses with a structured discharge checklist to ensure safe clinical closure before a patient leaves. Covers line removal, medication counseling, belongings return, patient education, and final documentation.

## Scope

- Checklist with 15 standard items spanning 7 categories
- Item-level completion tracking with audit trail
- Mandatory item enforcement before signoff
- Senior nurse verification of handover
- Status visible to discharge desk via Inpatient Record banner

## Reused Standard DocTypes

- **Inpatient Record** — extended with nursing checklist link
- **IPD Chart Entry** — optional link for final vitals reference

## New Custom DocTypes

- **Nursing Discharge Checklist** — parent checklist document
- **Nursing Discharge Checklist Item** — child table for individual items

## Workflow States

| State | Condition |
|-------|-----------|
| Pending | No items completed |
| In Progress | At least one item completed but not all |
| Completed | All mandatory items done + signoff performed |

## Standard Checklist Items (15)

1. IV line / cannula removed (Line Removal, mandatory)
2. Urinary catheter removed if applicable (Line Removal)
3. Drain/tube removed if applicable (Line Removal)
4. Medication counseling completed (Medication, mandatory)
5. Discharge medications received from pharmacy (Medication, mandatory)
6. Home-care instructions provided (Patient Education, mandatory)
7. Warning signs explained to patient/family (Patient Education, mandatory)
8. Diet instructions given (Patient Education)
9. Follow-up appointment communicated (Patient Education)
10. Patient belongings returned (Belongings, mandatory)
11. Valuables checked and signed (Belongings)
12. Final vitals recorded (Documentation, mandatory)
13. Wristband removed (Safety, mandatory)
14. Discharge papers signed by patient/NOK (Documentation, mandatory)
15. Escort / transport arranged (Safety)

## Permissions

| Role | Create | Read | Write | Delete |
|------|--------|------|-------|--------|
| Nursing User | ✓ | ✓ | ✓ | — |
| Physician | — | ✓ | — | — |
| Healthcare Administrator | ✓ | ✓ | ✓ | ✓ |
| IPD Admission Officer | — | ✓ | — | — |

## Validation Logic

- Skip requires mandatory reason
- Signoff blocked if any mandatory items still pending
- Verification only after completion
- All completion timestamps and user IDs recorded per item

## Client UX

- Progress bar at top showing X/15 items
- Quick-action buttons per row (Done / Not Applicable / Skip)
- "Complete & Sign Off" primary button with handover notes dialog
- "Verify Handover" button for senior nurse
- Status color indicators

## Files

| File | Purpose |
|------|---------|
| `doctype/nursing_discharge_checklist/nursing_discharge_checklist.json` | Schema |
| `doctype/nursing_discharge_checklist/nursing_discharge_checklist.py` | Controller |
| `doctype/nursing_discharge_checklist/nursing_discharge_checklist.js` | Client scripts |
| `doctype/nursing_discharge_checklist_item/nursing_discharge_checklist_item.json` | Child table schema |
| `services/nursing_discharge_service.py` | Domain logic |

## Open Questions / Assumptions

- Standard items are seeded on creation; hospitals may want to customize the item list in future
- Non-mandatory items can be left pending without blocking signoff
- Verification is optional but recommended; not enforced for bed vacate
