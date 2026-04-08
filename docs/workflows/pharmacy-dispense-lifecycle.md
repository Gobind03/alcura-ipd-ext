# Pharmacy Dispense Lifecycle

## States

```
Order Placed → Acknowledged → Stock Verified → Dispensed (Full/Partial) → Completed
                                             ↳ Substitution Requested
                                               → Approved → Dispensed
                                               → Rejected → Original item
```

## Dispense Status on Order

| Status | Meaning |
|--------|---------|
| Pending | No dispense entries yet |
| Partially Dispensed | Some qty dispensed < ordered qty |
| Fully Dispensed | Total dispensed >= ordered qty |

## Substitution Flow

1. **Pharmacist** clicks "Substitute" on Pharmacy Queue
2. Order transitions to **On Hold**; `substitution_status` = "Requested"
3. **Notification** sent to ordering practitioner and Physician role
4. **Doctor** approves or rejects via Clinical Order form or notification action
5. On **approval**: order resumes; pharmacist can dispense the substitute
6. On **rejection**: order resumes with original medication

## Dispense Return

- Pharmacist can return a dispensed entry (e.g., patient discharged before administration)
- Sets `status = "Returned"` on the IPD Dispense Entry
- Recalculates order dispense totals

## Audit Fields

| Field | Purpose |
|-------|---------|
| dispensed_by | Who dispensed |
| dispensed_at | When dispensed |
| verified_by | Double-check verification |
| verified_at | Verification timestamp |
| substitution_approved_by | Doctor who approved substitution |
| substitution_approved_at | Approval timestamp |

## SLA Integration

Dispense is tracked as an SLA milestone on the parent Clinical Order.
The "Dispensed" milestone is recorded on each dispense event.

## Notification Events

| Event | Recipients |
|-------|-----------|
| Dispense completed | Nursing User, ordering practitioner |
| Substitution requested | Ordering practitioner, Physicians |
| Substitution approved/rejected | Pharmacy User |
