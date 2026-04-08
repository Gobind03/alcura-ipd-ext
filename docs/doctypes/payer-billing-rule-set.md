# Payer Billing Rule Set

## Purpose

Master document defining billing rules for a specific payer or payer type. Controls how charges are split between payer and patient.

## Module

Alcura IPD Extensions

## Naming

`PBRS-.#####` (e.g., PBRS-00001)

## Key Fields

| Field | Type | Required | Indexed | Notes |
|-------|------|----------|---------|-------|
| rule_set_name | Data | Yes | Yes (unique) | Human-readable identifier |
| payer_type | Select | No | Yes | Cash/Corporate/Insurance TPA/PSU/Government Scheme |
| payer | Link (Customer) | Conditional | Yes | Required for Corporate/PSU |
| insurance_payor | Link (Insurance Payor) | Conditional | Yes | Required for Insurance TPA |
| company | Link (Company) | Yes | Yes | |
| valid_from | Date | Yes | Yes | |
| valid_to | Date | No | Yes | Open-ended if blank |
| is_active | Check | No | No | |

## Child Table: rules (Payer Billing Rule Item)

| Field | Type | Notes |
|-------|------|-------|
| rule_type | Select | Non-Payable / Co-Pay Override / Sub-Limit / Package Inclusion / Excluded Consumable / Room Rent Cap |
| applies_to | Select | Item / Item Group / Charge Category |
| item_code | Link (Item) | When applies_to = Item |
| item_group | Link (Item Group) | When applies_to = Item Group |
| charge_category | Select | When applies_to = Charge Category |
| co_pay_percent | Percent | For Co-Pay Override rules |
| sub_limit_amount | Currency | For Sub-Limit rules |
| cap_amount | Currency | For Room Rent Cap rules |

## Resolution Logic

1. Specific payer match (payer_type + payer/insurance_payor) takes priority
2. Generic payer type match (payer_type only, no specific payer)
3. Date-range validation: valid_from <= today AND (valid_to IS NULL OR valid_to >= today)
