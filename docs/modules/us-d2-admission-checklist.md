# US-D2: IPD Admission Checklist

## Purpose

Provide a guided, template-driven admission checklist so that no step is missed before a patient is sent to the ward. Requirements may vary by payer type and care setting.

## Scope

- Template master with configurable items, categories, and override rules
- Per-admission checklist instance linked to the Inpatient Record
- Item completion and waiver workflows with audit trail
- Status recomputation (Incomplete → Complete / Overridden)
- Integration with Inpatient Record form (banner, gate before bed allocation)
- Role-based permissions for completion and override

## Reused Standard DocTypes

| DocType | How Used |
|---------|----------|
| Inpatient Record | 1:1 link via `custom_admission_checklist`; status synced |
| Patient | Patient reference on checklist |
| User | Audit: completed_by, override_by |

## New Custom DocTypes

| DocType | Purpose |
|---------|---------|
| Admission Checklist Template | Reusable master with item definitions |
| Admission Checklist Template Item | Child table: item label, category, mandatory, overridable |
| Admission Checklist | Per-admission instance linked to IR |
| Admission Checklist Entry | Child table: item status, audit fields, evidence |

See [doctypes/admission-checklist-template.md](../doctypes/admission-checklist-template.md) and [doctypes/admission-checklist.md](../doctypes/admission-checklist.md).

## Fields Added to Standard DocTypes

| DocType | Field | Type | Notes |
|---------|-------|------|-------|
| Inpatient Record | `custom_admission_checklist` | Link → Admission Checklist | Read-only |
| Inpatient Record | `custom_checklist_status` | Data | Read-only, fetched |

## Workflow States

| Status | Meaning |
|--------|---------|
| Incomplete | At least one mandatory item is Pending |
| Complete | All mandatory items are Completed (none Waived) |
| Overridden | All mandatory items are done, but at least one was Waived |

## Permissions

| Component | Roles Required |
|-----------|---------------|
| Create/complete checklist | IPD Admission Officer, Nursing User |
| Waive mandatory item | Healthcare Administrator only |
| View checklist | IPD Admission Officer, Nursing User, Healthcare Administrator |
| Template management | Healthcare Administrator |

## Validation Logic

1. One checklist per Inpatient Record (unique constraint)
2. Cannot waive item unless `can_override` is true on template item
3. Waive requires Healthcare Administrator role
4. Waive requires a non-empty reason
5. Cannot complete or waive an already-completed/waived item
6. Cannot modify a checklist that is already Complete or Overridden
7. Template items must have unique labels

## Notifications

- Timeline comment on IR when checklist is created
- Timeline comment on checklist when item is waived (includes reason)
- Checklist status banner on IR form during Admission Scheduled state
- Warning gate before bed allocation if checklist is Incomplete

## Reporting Impact

- Admission Checklist list view shows status per admission
- Incomplete checklists can be filtered to identify bottlenecks

## Test Cases

See [testing/us-d2-admission-checklist.md](../testing/us-d2-admission-checklist.md).

## Open Questions / Assumptions

1. Template selection priority: exact payer_type match > payer-specific default > universal default > any active template.
2. The checklist gate before bed allocation is advisory (warn) not blocking (strict). Users can proceed after confirmation.
3. Non-mandatory items do not affect the overall checklist status.
4. Evidence attachment is optional for all items.
