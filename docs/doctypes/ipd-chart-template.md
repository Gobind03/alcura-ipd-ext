# IPD Chart Template

## Purpose

Master definition for parameter-based bedside charts. Defines what parameters to record, their types, validation ranges, critical thresholds, and default recording frequency.

## Type

Regular DocType (not submittable). Named by `template_name` field.

## Key Fields

| Field | Type | Notes |
|-------|------|-------|
| template_name | Data | Unique name, e.g. "General Ward — Vitals" |
| chart_type | Select | Vitals / Glucose / Pain / Ventilator / Custom |
| default_frequency_minutes | Int | Default recording interval |
| is_active | Check | Only active templates can be used |
| applicable_unit_types | Small Text | Comma-separated ward types; blank = all |
| parameters | Table: IPD Chart Template Parameter | Required, at least one row |

## Child Table: IPD Chart Template Parameter

| Field | Type | Notes |
|-------|------|-------|
| parameter_name | Data | e.g. "Temperature", "SpO2" |
| parameter_type | Select | Numeric / Select / Text / Check |
| uom | Data | Unit of measure |
| options | Small Text | For Select type (one per line) |
| min_value / max_value | Float | Validation range |
| critical_low / critical_high | Float | Alert thresholds |
| is_mandatory | Check | |
| display_order | Int | Ordering within the form |

## Validation

- At least one parameter required
- No duplicate parameter names (case-insensitive)
- Select parameters must have options
- min_value < max_value when both set
- Frequency must be >= 1

## Permissions

Full CRUD: Healthcare Administrator. Read-only: Nursing User, Physician.

## Fixture Data

Five templates created on install: General Ward Vitals, ICU Vitals, Glucose Monitoring, Pain Assessment, Ventilator Monitoring.
