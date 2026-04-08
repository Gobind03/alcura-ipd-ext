# US-H1: Configure ICU Monitoring Profiles

## Purpose

Allow critical care administrators to define per-unit-type monitoring
templates so that the correct set of bedside charts is automatically
started when a patient is admitted to or transferred into a specific
ICU/HDU ward.

## Scope

- Define monitoring profiles by ward classification (ICU, MICU, CICU, NICU, PICU, SICU, HDU, etc.)
- Specify which chart templates are required and at what frequency
- Auto-start charts on admission and transfer
- Swap profile charts when ward classification changes
- Track compliance with mandatory chart coverage

## Reused Standard DocTypes

| DocType | Usage |
|---------|-------|
| Hospital Ward | `ward_classification` determines which profile applies |
| Inpatient Record | `custom_current_ward` used for compliance checking |

## Reused Custom DocTypes

| DocType | Usage |
|---------|-------|
| IPD Chart Template | Referenced by profile rows |
| IPD Bedside Chart | Auto-started by profile; `source_profile` tracks origin |

## New Custom DocTypes

### ICU Monitoring Profile

Master configuration mapping a ward classification to chart templates.

| Field | Type | Notes |
|-------|------|-------|
| profile_name | Data | Primary key, unique |
| unit_type | Select | Same options as Hospital Ward.ward_classification |
| is_active | Check | Only one active profile per (unit_type, company) |
| company | Link (Company) | Optional; company-specific profiles override global |
| description | Small Text | |
| chart_templates | Table (ICU Monitoring Profile Template) | At least one required |

### ICU Monitoring Profile Template (child table)

| Field | Type | Notes |
|-------|------|-------|
| chart_template | Link (IPD Chart Template) | Must be active |
| frequency_override | Int | Overrides template default if set (min 1) |
| is_mandatory | Check | Compliance tracking |
| auto_start | Check | Default 1; if set, chart auto-starts |
| display_order | Int | |

## Fields Added to Existing DocTypes

### IPD Bedside Chart

| Field | Type | Notes |
|-------|------|-------|
| source_profile | Link (ICU Monitoring Profile) | Read-only; set when auto-started |
| missed_count | Int | Read-only; updated by scheduled task |

## Workflow States

ICU Monitoring Profile is a configuration document with no workflow.
Its `is_active` flag controls whether it is applied.

## Permissions

| Role | Create | Read | Write | Delete |
|------|--------|------|-------|--------|
| Healthcare Administrator | Yes | Yes | Yes | Yes |
| ICU Administrator | Yes | Yes | Yes | No |
| Nursing User | No | Yes | No | No |
| Physician | No | Yes | No | No |

## Validation Logic

- Unique (unit_type, company) pair per active profile
- All referenced chart templates must be active
- At least one template row required
- No duplicate templates within a profile
- Frequency override must be >= 1 if set

## Auto-Application Logic

### On Admission (bed_allocation_service)

After bed allocation succeeds:
1. Resolve ward classification from the allocated bed's ward
2. Find the active monitoring profile for that classification
3. Start all `auto_start` charts, skipping any already active
4. Set `source_profile` on each started chart

### On Transfer (bed_transfer_service)

After patient transfer succeeds:
1. Compare old and new ward classifications
2. If different, discontinue charts from old profile (`source_profile` match)
3. Apply new profile

### Compliance Checking

`get_compliance_for_ir(inpatient_record)` checks whether all mandatory
chart templates from the applicable profile have active charts.

## Notifications

- Timeline comment on IR when profile is applied or removed
- No email/push notifications (profile application is automated)

## Reporting Impact

- Compliance data available via `get_compliance_for_ir` API
- Can feed into ICU dashboard and ward-level compliance reports

## Test Cases

See `tests/test_monitoring_profile_service.py`:
- Profile validation (empty, duplicate templates, inactive templates, duplicate unit_type)
- Profile resolution (global, company-specific, no match)
- Auto-application (starts charts, skips existing, skips non-autostart, no-op for missing profile)
- Profile removal (discontinues profile charts, preserves manual charts)
- Profile swap (on classification change, no-op for same classification)
- Compliance (compliant when all mandatory active, non-compliant when missing)

## Fixtures

Seed profiles created for ICU, MICU, CICU, SICU, NICU, HDU.
See `setup/monitoring_profile_fixtures.py`.

## Open Questions / Assumptions

- Profiles are per ward classification, not per individual ward
- Company-specific profiles take priority over global ones
- Auto-application is best-effort; failures are logged but do not block admission/transfer
- Ventilator monitoring is not auto-started by default (requires explicit clinical decision)
