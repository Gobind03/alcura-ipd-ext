# ICU Monitoring Profile

## Purpose

Maps a ward classification to a set of IPD Chart Templates that should
be auto-started when a patient is admitted to or transferred into that
unit type.

## Naming

`field:profile_name` — e.g. "ICU Standard Profile"

## Key Fields

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| profile_name | Data | Yes | Unique |
| unit_type | Select | Yes | Matches Hospital Ward.ward_classification |
| is_active | Check | No | Default 1 |
| company | Link (Company) | No | Company-specific override |
| description | Small Text | No | |
| chart_templates | Table | Yes | At least one row |

## Child Table: ICU Monitoring Profile Template

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| chart_template | Link (IPD Chart Template) | Yes | Must be active |
| frequency_override | Int | No | Overrides template default |
| is_mandatory | Check | No | For compliance tracking |
| auto_start | Check | No | Default 1 |
| display_order | Int | No | |

## Validation

- Unique (unit_type, company) pair among active profiles
- Chart templates must be active
- No duplicate templates in a single profile
- Frequency override >= 1 when set

## Permissions

| Role | CRUD |
|------|------|
| Healthcare Administrator | Full |
| ICU Administrator | Create/Read/Write |
| Nursing User | Read |
| Physician | Read |

## Related DocTypes

- IPD Chart Template (referenced)
- IPD Bedside Chart (auto-started, `source_profile` back-link)
- Hospital Ward (classification determines profile)
