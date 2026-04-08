# US-C2: Capture TPA/Corporate Insurance Details at Registration

## Purpose

Provide a unified payer abstraction for IPD patients that covers Cash, Corporate, Insurance TPA, PSU, and Government Scheme payer types. This enables admission and billing workflows to consistently reference a patient's active payer profile regardless of payer type.

## Scope

- Create a standalone `Patient Payer Profile` doctype linked to Patient
- Support five payer types: Cash, Corporate, Insurance TPA, PSU, Government Scheme
- Integrate with Marley Health's Insurance Payor and Patient Insurance Policy for TPA cases
- Add custom fields to Patient (default payer profile) and Inpatient Record (active payer tracking)
- Align payer_type options across Room Tariff Mapping and Bed Reservation
- Provide a migration patch for the "TPA" → "Insurance TPA" rename
- Build a Payer Profile Expiry script report
- Add dashboard integration on the Patient form
- Schedule daily expiry notifications

## Reused Standard DocTypes

| DocType | How Used |
|---------|----------|
| Patient | Extended with `custom_default_payer_profile` link field |
| Customer | Used as the payer entity for Corporate, PSU payer types |
| Insurance Payor | Linked from profile for Insurance TPA type (Marley Health) |
| Patient Insurance Policy | Optionally linked for TPA profiles (Marley Health) |
| Inpatient Record | Extended with payer profile/type/display custom fields |
| Price List | Linked as applicable price list on profile |

## New Custom DocTypes

| DocType | Purpose |
|---------|---------|
| Patient Payer Profile | Standalone payer abstraction per patient, covering all payer types |

## Fields Added

### Patient Payer Profile (new doctype)

See [docs/doctypes/patient-payer-profile.md](../doctypes/patient-payer-profile.md) for the full field spec.

### Custom Fields on Patient

| Fieldname | Type | Label | Notes |
|-----------|------|-------|-------|
| `custom_payer_profile_section` | Section Break | Default Payer | Collapsible |
| `custom_default_payer_profile` | Link | Default Payer Profile | → Patient Payer Profile, filtered to active profiles for the patient |

### Custom Fields on Inpatient Record

| Fieldname | Type | Label | Notes |
|-----------|------|-------|-------|
| `custom_payer_section` | Section Break | Payer Details | |
| `custom_patient_payer_profile` | Link | Patient Payer Profile | → Patient Payer Profile |
| `custom_payer_type` | Data | Payer Type | Read-only, fetched from profile |
| `custom_column_break_payer_1` | Column Break | | |
| `custom_payer_display` | Data | Payer | Read-only, computed display name |

## Workflow States

Not applicable. Patient Payer Profile is a non-submittable doctype. Lifecycle is managed via:
- `is_active` flag (active/inactive)
- `valid_from` / `valid_to` date range
- Timeline comments on the linked Patient for audit

## Permissions

| Role | Read | Write | Create | Delete |
|------|------|-------|--------|--------|
| Healthcare Administrator | Y | Y | Y | Y |
| System Manager | Y | Y | Y | Y |
| TPA Desk User | Y | Y | Y | N |
| Healthcare Receptionist | Y | Y | Y | N |
| Nursing User | Y | N | N | N |
| Physician | Y | N | N | N |
| Accounts User | Y | N | N | N |

**TPA Desk User** is a new custom role created via `setup/roles.py` during install.

## Validation Logic

### Server-side (patient_payer_profile.py controller)

1. **Date range**: `valid_from` must be ≤ `valid_to` (if set)
2. **Insurance TPA**: `insurance_payor` is mandatory
3. **Corporate / PSU**: `payer` (Customer) is mandatory
4. **Insurance policy cross-validation**: If linked, must belong to same patient and insurance payor
5. **Expired profile warning**: Warns (does not block) when saving an active profile whose valid_to is in the past
6. **Duplicate active profile warning**: Warns if another active profile exists for the same patient + payer_type + payer combination

### Client-side (patient_payer_profile.js)

1. Conditional field visibility based on payer_type
2. Auto-clear irrelevant fields when payer_type changes
3. Auto-fetch policy_number and valid_to from linked Insurance Policy
4. Expiry indicator on dashboard headline
5. Insurance Policy filtered by patient and insurance_payor

## Notifications

- **Timeline comment on Patient**: Added when a payer profile is created, activated, or deactivated
- **Daily scheduled task**: Sends in-app Notification Log to TPA Desk User and Healthcare Administrator roles for profiles expiring within 7 days

## Reporting Impact

### New Report: Payer Profile Expiry

- Script Report on Patient Payer Profile
- Filters: expiry_within_days, payer_type, insurance_payor, company
- Shows: profile ID, patient, payer type, policy number, validity dates, days until expiry, sum insured
- Available to: Healthcare Administrator, TPA Desk User, Healthcare Receptionist, Accounts User

### Impact on Existing Reports

- Live Bed Board: No direct change. Payer information can be joined via Bed Reservation → Patient Payer Profile in future enhancements.

## Test Cases

See [docs/testing/us-c2-patient-payer-profile.md](../testing/us-c2-patient-payer-profile.md).

## Migration / Patch Notes

- **`rename_tpa_to_insurance_tpa`** (post_model_sync): Renames `payer_type = "TPA"` to `"Insurance TPA"` in Room Tariff Mapping and Bed Reservation tables
- Must run after model sync since the DocType JSON now has the new option values

## Open Questions / Assumptions

1. **Cash payer profile**: Lightweight, no payer/policy details needed. Created for consistency so every admission can reference a profile, but not mandatory.
2. **balance_available**: Manually maintained for now. Automated decrement on billing is a follow-up.
3. **TPA Desk User role**: Created by fixture. Not assigned by default; hospitals configure this per their needs.
4. **Insurance Policy linkage is optional**: Not all TPA patients will have a Marley Health Patient Insurance Policy at registration time.
5. **Payer type rename**: "TPA" → "Insurance TPA" is a breaking change for existing data. The migration patch handles this.
6. **Government Scheme payer**: Does not require a Customer link. The scheme_name field captures the specific programme (CGHS, ECHS, Ayushman Bharat, etc.).
