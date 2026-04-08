# DocType: Patient Payer Profile

## Purpose

Standalone doctype that captures a patient's payer/insurance/corporate/government-scheme details. Acts as a unified payer abstraction for IPD workflows, supporting five payer types and integrating with Marley Health's insurance module for TPA cases.

## Module

Alcura IPD Extensions

## Naming

`PPP-.YYYY.-.#####` (auto-generated naming series)

## Submittable

No. Lifecycle managed via `is_active` flag and `valid_from`/`valid_to` date range.

## Fields

### Identity Section

| Fieldname | Type | Label | Required | Indexed | Notes |
|-----------|------|-------|----------|---------|-------|
| `patient` | Link → Patient | Patient | Yes | Yes | |
| `patient_name` | Data | Patient Name | No | No | Fetched from patient |
| `payer_type` | Select | Payer Type | Yes | Yes | Cash / Corporate / Insurance TPA / PSU / Government Scheme |
| `company` | Link → Company | Company | Yes | Yes | Default from session |

### Payer Details Section (hidden for Cash)

| Fieldname | Type | Label | Required | Indexed | Notes |
|-----------|------|-------|----------|---------|-------|
| `payer` | Link → Customer | Payer (Customer) | Conditional | Yes | Required for Corporate, PSU |
| `insurance_payor` | Link → Insurance Payor | Insurance Payor | Conditional | Yes | Required for Insurance TPA |
| `insurance_policy` | Link → Patient Insurance Policy | Insurance Policy | No | No | Optional for Insurance TPA |
| `employer_name` | Data | Employer / Organization | No | No | Shown for Corporate, PSU, Government Scheme |
| `scheme_name` | Data | Scheme Name | No | No | Shown for Government Scheme |
| `tpa_name` | Data | TPA Name | No | No | Read-only, fetched from Insurance Payor |

### Member Details Section (hidden for Cash)

| Fieldname | Type | Label | Notes |
|-----------|------|-------|-------|
| `policy_number` | Data | Policy / Card Number | |
| `member_id` | Data | Member ID | |
| `relationship_to_primary` | Select | Relationship to Primary Holder | Self / Spouse / Child / Parent / Sibling / Dependent / Other |
| `primary_holder_name` | Data | Primary Holder Name | Hidden when Self |

### Validity & Coverage Section

| Fieldname | Type | Label | Required | Indexed | Notes |
|-----------|------|-------|----------|---------|-------|
| `valid_from` | Date | Valid From | Yes | Yes | |
| `valid_to` | Date | Valid To | No | Yes | Blank = open-ended |
| `sum_insured` | Currency | Sum Insured / Credit Limit | No | No | |
| `balance_available` | Currency | Balance Available | No | No | Manually maintained |
| `sub_limit_per_visit` | Currency | Sub-Limit Per Visit | No | No | |
| `room_category_entitlement` | Select | Room Category Entitlement | No | No | Same options as IPD Room Category |

### Billing Rules Section (collapsible)

| Fieldname | Type | Label | Notes |
|-----------|------|-------|-------|
| `preauth_required` | Check | Pre-authorization Required | |
| `co_pay_percent` | Percent | Co-pay % | |
| `deductible_amount` | Currency | Deductible Amount | |
| `default_price_list` | Link → Price List | Applicable Price List | |

### Status Section

| Fieldname | Type | Label | Notes |
|-----------|------|-------|-------|
| `is_active` | Check | Active | Default 1 |
| `notes` | Small Text | Notes | |

## Permissions

| Role | Read | Write | Create | Delete |
|------|------|-------|--------|--------|
| Healthcare Administrator | Yes | Yes | Yes | Yes |
| System Manager | Yes | Yes | Yes | Yes |
| TPA Desk User | Yes | Yes | Yes | No |
| Healthcare Receptionist | Yes | Yes | Yes | No |
| Nursing User | Yes | No | No | No |
| Physician | Yes | No | No | No |
| Accounts User | Yes | No | No | No |

## Validations

1. `valid_from` ≤ `valid_to` (when valid_to is set)
2. Insurance TPA requires `insurance_payor`
3. Corporate / PSU requires `payer` (Customer)
4. Insurance policy must belong to same patient and insurance payor
5. Warn on expired active profile
6. Warn on duplicate active profile for same patient + payer_type + payer

## Dashboard Links

- Appears on Patient dashboard under "Payer Profiles" group
- Links via `patient` field

## Related DocTypes

- Patient (parent link)
- Customer (payer for Corporate/PSU)
- Insurance Payor (Marley Health, for TPA)
- Patient Insurance Policy (Marley Health, optional for TPA)
- Bed Reservation (references via `patient_payer_profile` field)
- Inpatient Record (references via `custom_patient_payer_profile` custom field)
