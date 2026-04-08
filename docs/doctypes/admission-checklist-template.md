# Admission Checklist Template

## Purpose

Reusable master defining the items required for an IPD admission checklist. Templates can be scoped to specific payer types and care settings.

## Fields

| Fieldname | Type | Notes |
|-----------|------|-------|
| `template_name` | Data | Required, unique, used as document name |
| `payer_type` | Select | Cash/Corporate/Insurance TPA/PSU/Government Scheme; blank = all |
| `care_setting` | Select | All/General Ward/ICU/HDU/Isolation |
| `is_default` | Check | Fallback when no specific match exists |
| `is_active` | Check | Default 1 |
| `checklist_items` | Table → Admission Checklist Template Item | At least one required |

## Child Table: Admission Checklist Template Item

| Fieldname | Type | Notes |
|-----------|------|-------|
| `item_label` | Data | Required, must be unique within template |
| `category` | Select | Consent/Identity/Financial/Clinical/Personal/Other |
| `is_mandatory` | Check | Default 1 |
| `can_override` | Check | Default 0; allows authorized waiver |
| `sort_order` | Int | Display ordering |
| `instructions` | Small Text | Guidance for the admission officer |

## Permissions

- Healthcare Administrator: full CRUD
- Nursing User: read only
- IPD Admission Officer: read only

## Validation

- At least one checklist item required
- No duplicate item labels within a template
- Only one default template per payer_type + care_setting combination

## Module

Alcura IPD Extensions
