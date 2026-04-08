# US-I2: Payer-Specific Billing Rules

## Purpose

Enable configurable payer-specific billing rules so that room rent, consumables, procedures, pharmacy, investigations, doctor visits, and package exclusions follow payer rules accurately, producing correct patient liability and insurer liability splits.

## Scope

- Configurable rule sets per payer/payer type
- Rule types: Non-Payable, Co-Pay Override, Sub-Limit, Package Inclusion, Excluded Consumable, Room Rent Cap
- Bill split computation service
- Integration with Patient Payer Profile and TPA Preauth

## Reused Standard DocTypes

- Item, Item Group, Price List, Customer, Insurance Payor

## Reused Custom DocTypes

- Patient Payer Profile (co-pay %, deductible, room entitlement)
- Room Tariff Mapping (room tariffs)
- TPA Preauth Request (approved amount)

## New Custom DocTypes

- **Payer Billing Rule Set** — master rule configuration per payer
- **Payer Billing Rule Item** — child table defining individual rules

## Architecture

Three-layer resolution:

1. **Payer Billing Rule Set** — rule-type-specific configs per payer or payer type
2. **Patient Payer Profile** — patient-level co-pay %, deductible
3. **TPA Preauth Request** — approved amount cap

## Resolution Priority

1. Non-payable / excluded consumable → full patient liability
2. Package inclusion → zero separate charge
3. Sub-limit per charge category → cap payer amount
4. Co-pay (item-level override or profile-level default)
5. Deductible (profile-level, applied once across bill)
6. Room rent cap → proportional deduction

## Permissions

| Role | Create | Read | Write | Delete |
|------|--------|------|-------|--------|
| Healthcare Administrator | Yes | Yes | Yes | Yes |
| System Manager | Yes | Yes | Yes | Yes |
| TPA Desk User | No | Yes | Yes | No |
| Accounts User | No | Yes | No | No |

## Test Cases

See `docs/testing/us-i2-payer-billing-rules.md`

## Assumptions

- Rule sets use date-based validity for versioning
- When no rule set matches, profile-level co-pay % is used as the only split logic
- Cash patients bypass the rules engine entirely
