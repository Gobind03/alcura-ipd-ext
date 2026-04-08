# Billing Rules Engine Architecture

## Overview

The billing rules engine resolves payer-specific rules and computes payer/patient/excluded liability splits for IPD charges.

## Data Flow

```
Patient Payer Profile
    ├── co_pay_percent (default)
    ├── deductible_amount
    └── payer_type + payer/insurance_payor
           │
           ▼
    Payer Billing Rule Set (matched by payer type/payer/date)
    ├── Non-Payable rules
    ├── Excluded Consumable rules
    ├── Package Inclusion rules
    ├── Co-Pay Override rules
    ├── Sub-Limit rules
    └── Room Rent Cap rules
           │
           ▼
    TPA Preauth Request (optional)
    └── approved_amount (overall cap)
           │
           ▼
    compute_bill_split()
    ├── Per-line split: payer_amount, patient_amount, excluded_amount
    ├── Category sub-totals with sub-limit enforcement
    ├── Deductible application (once across bill)
    └── Preauth overshoot calculation
```

## Resolution Priority (per line item)

1. **Non-Payable / Excluded Consumable**: item fully patient-liable
2. **Package Inclusion**: item has zero separate charge
3. **Sub-Limit**: cumulative payer amount per category capped
4. **Co-Pay**: item-level override > profile-level default
5. **Deductible**: applied once across the full bill
6. **Room Rent Cap**: per-line cap on room rent charges

## Key Service Functions

- `resolve_billing_rules()` — finds matching rule set, builds ResolvedRules
- `compute_line_split()` — single line item payer/patient split
- `compute_bill_split()` — full bill with all rules, sub-limits, deductible

## Performance

- Rule set lookup uses indexed payer_type, payer, insurance_payor, valid_from
- Child table items loaded once per bill computation
- No N+1 queries: rules loaded in batch, applied in-memory
