# Monitoring Protocol Bundle

## Purpose

Master configuration for care protocols (sepsis bundle, ventilator
bundle, DKA protocol, etc.) that define required actions and timing.

## Naming

`field:bundle_name` — e.g. "Sepsis Bundle - 1 Hour"

## Key Fields

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| bundle_name | Data | Yes | Unique |
| bundle_code | Data | No | Unique short code |
| category | Select | Yes | Clinical category |
| is_active | Check | No | Default 1 |
| steps | Table | Yes | At least one step |

## Validation

- At least one step required
- No duplicate step names (case-insensitive)
- No duplicate sequence numbers
- Non-negative timing and weight values
- Compliance target between 0 and 100

## Permissions

| Role | CRUD |
|------|------|
| Healthcare Administrator | Full |
| ICU Administrator | Create/Read/Write |
| Physician | Read |
| Nursing User | Read |
