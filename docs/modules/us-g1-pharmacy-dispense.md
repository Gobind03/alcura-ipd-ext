# US-G1: Pharmacy Dispense Workflow

## Purpose

Enable pharmacy users to acknowledge medication orders, verify stock availability, dispense medications (full or partial), request substitutions when stock is unavailable, and track the complete dispense lifecycle with SLA and audit trail.

## Scope

- Dispense tracking for IPD medication orders
- Stock verification against ERPNext `Bin`
- Partial and full dispensing with batch/warehouse tracking
- Substitution request → approval/rejection workflow
- Dispense return handling
- Real-time notifications to nursing and ordering practitioners

## Reused Standard DocTypes

| DocType | Usage |
|---------|-------|
| Item | Medication items for stock lookup |
| Bin | Stock level verification via `tabBin` |
| Warehouse | Pharmacy warehouse for dispense source |

## New Custom DocTypes

| DocType | Purpose |
|---------|---------|
| IPD Dispense Entry | Tracks each dispense event (partial/full) against a medication order |

## New Fields on IPD Clinical Order

| Field | Type | Notes |
|-------|------|-------|
| dispense_status | Select (Pending / Partially Dispensed / Fully Dispensed) | Computed, read-only |
| total_dispensed_qty | Float | Aggregate of active dispense entries |
| substitution_status | Select (None / Requested / Approved / Rejected) | Tracks substitution flow |

## Workflow

```
Order Acknowledged → Stock Verified → Dispense (Full/Partial) → Completed
                                   ↳ Substitution Requested → Approved → Dispense
                                                             → Rejected → Original item
```

### Dispense Status Transitions

- **Pending**: No dispense entries yet
- **Partially Dispensed**: Some qty dispensed, but less than ordered
- **Fully Dispensed**: Total dispensed >= ordered qty

### Substitution Flow

1. Pharmacist requests substitution (order goes On Hold)
2. Ordering practitioner receives notification
3. Doctor approves or rejects substitution
4. On approval: order resumes, pharmacist dispenses substitute
5. On rejection: order resumes with original item

## Permissions

| Role | Create | Read | Write | Delete |
|------|--------|------|-------|--------|
| Pharmacy User | ✓ | ✓ | ✓ | |
| Nursing User | | ✓ | | |
| Physician | | ✓ | | |
| Healthcare Administrator | ✓ | ✓ | ✓ | ✓ |

## Validation Logic

- Dispensed qty must be > 0
- Cannot dispense against Cancelled or Draft orders
- Substitution requires reason and approval by practitioner
- Double return is prevented

## Notifications

| Event | Recipients | Method |
|-------|-----------|--------|
| Dispense completed | Nursing User, ordering practitioner | Notification Log + realtime |
| Substitution requested | Ordering practitioner, Physicians | Notification Log + realtime |
| Substitution approved/rejected | Pharmacy User | Notification Log |

## SLA Milestones

1. Acknowledged
2. Stock Verified
3. Dispensed
4. Received at Ward

## API Endpoints

| Endpoint | Method |
|----------|--------|
| `alcura_ipd_ext.api.pharmacy.verify_stock` | GET |
| `alcura_ipd_ext.api.pharmacy.dispense_medication` | POST |
| `alcura_ipd_ext.api.pharmacy.request_substitution` | POST |
| `alcura_ipd_ext.api.pharmacy.approve_substitution` | POST |
| `alcura_ipd_ext.api.pharmacy.reject_substitution` | POST |
| `alcura_ipd_ext.api.pharmacy.return_dispense` | POST |
| `alcura_ipd_ext.api.pharmacy.get_dispense_history` | GET |

## Test Cases

See `docs/testing/us-g1-tests.md` and `tests/test_pharmacy_dispense_service.py`.
