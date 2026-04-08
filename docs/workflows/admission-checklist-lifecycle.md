# Admission Checklist Lifecycle

## States

```
[Created] → Incomplete → Complete
                       → Overridden
```

## Transitions

| From | To | Trigger |
|------|----|---------|
| (new) | Incomplete | Checklist created from template |
| Incomplete | Incomplete | Individual item completed (mandatory items still pending) |
| Incomplete | Complete | Last mandatory item completed (no waivers) |
| Incomplete | Overridden | Last mandatory item resolved via waiver |

## Terminal States

- **Complete**: all mandatory items done without waivers
- **Overridden**: all mandatory items resolved, at least one waived

Once Complete or Overridden, the checklist cannot be further modified.

## Integration Points

- **Inpatient Record**: `custom_checklist_status` is synced on every status change
- **Bed Allocation Gate**: if checklist exists and is Incomplete, the user receives a confirmation prompt before proceeding with bed allocation
- **Timeline**: waiver actions create audit comments on the checklist document

## Role Requirements

- **Complete item**: IPD Admission Officer, Nursing User, Healthcare Administrator
- **Waive item**: Healthcare Administrator only
- **Override rule**: template item must have `can_override = 1`
