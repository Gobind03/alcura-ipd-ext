# US-A5: Configure Hospital Bed Policies

## Purpose

Provide a centralized, hospital-wide configuration for bed operation policies that govern availability computation, gender enforcement, housekeeping SLAs, payer eligibility filtering, and reservation rules across the IPD module.

## Scope

- Define availability exclusion rules (dirty, cleaning, maintenance, infection-blocked beds)
- Define gender enforcement level (Strict / Advisory / Ignore)
- Configure cleaning turnaround SLA and auto-dirty-on-discharge behaviour
- Configure reservation timeout (future use)
- Configure payer eligibility enforcement level
- Configure minimum buffer beds per ward (future use)
- Single settings document — site-wide, not per-ward or per-company

## Reused Standard DocTypes

None. This is a standalone settings DocType that does not extend or link to standard Healthcare/ERPNext doctypes.

## New Custom DocTypes

| DocType | Module | Purpose |
|---------|--------|---------|
| IPD Bed Policy | Alcura IPD Extensions | Single (settings) DocType holding hospital-wide bed operation policies |

## Fields Added to Standard DocTypes

None.

## Workflow States

Not applicable. This is a Single settings document with no workflow.

## Permissions

| Role | Read | Write |
|------|------|-------|
| Healthcare Administrator | Yes | Yes |
| Nursing User | Yes | No |
| Physician | Yes | No |

## Validation Logic

1. **Non-negative integers**: `cleaning_turnaround_sla_minutes`, `reservation_timeout_minutes`, and `min_buffer_beds_per_ward` must be >= 0.
2. **Select fields**: `gender_enforcement` and `enforce_payer_eligibility` are constrained to their option lists by the DocType schema.

## Notifications

None for this story.

## Reporting Impact

The IPD Bed Policy settings are consumed by the Live Bed Board report (US-B1) and future bed allocation workflows. Policy changes take effect immediately for subsequent queries (cache is cleared on save).

## Test Cases

See [docs/testing/us-a5-bed-policies.md](../testing/us-a5-bed-policies.md).

## Open Questions / Assumptions

1. **Site-wide scope**: The policy is a Single DocType, applying to all wards and companies on the site. Per-ward or per-company overrides may be added in a future story if needed.
2. **Future fields**: `reservation_timeout_minutes` and `min_buffer_beds_per_ward` are defined now but will be consumed by future bed allocation stories (US-B2+).
3. **No scheduler dependency**: Policy enforcement is query-time; no background job is needed for US-A5.
