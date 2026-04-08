# US-C3: Verify Payer Eligibility Before Admission

## Purpose

Capture digital eligibility verification for payer profiles before patient admission, so the hospital knows whether cash deposit or pre-authorization is required. This prevents revenue leakage from unverified insurance/TPA admissions and provides an audit trail of all verification attempts.

## Scope

- Create a `Payer Eligibility Check` doctype to record verification outcomes
- Build a status lifecycle: Pending / Verified / Conditional / Rejected / Expired
- Provide a service layer to fetch the latest active eligibility for a patient
- Integrate eligibility checks into the admission workflow via IPD Bed Policy enforcement
- Add pre-flight eligibility check to the "Allocate Bed" flow on Inpatient Record
- Send notifications on Rejected and Expired status changes
- Build a summary report for TPA desk and administrators
- Add eligibility tracking custom fields on Inpatient Record

## Reused Standard DocTypes

| DocType | How Used |
|---------|----------|
| Patient | Linked as the subject of the eligibility check |
| Inpatient Record | Optionally linked; custom fields added for eligibility tracking |
| Company | Scoping eligibility checks to a company |
| User | Audit trail (verified_by, submitted_by) |

## Reused Custom DocTypes (from this app)

| DocType | How Used |
|---------|----------|
| Patient Payer Profile | Required link — the payer profile being verified |
| IPD Bed Policy | Extended with `enforce_eligibility_verification` field |

## New Custom DocTypes

| DocType | Purpose |
|---------|---------|
| Payer Eligibility Check | Records the outcome of payer eligibility verification |

## Fields Added

### Custom Fields on Inpatient Record

| Fieldname | Type | Label | Notes |
|-----------|------|-------|-------|
| `custom_payer_eligibility_check` | Link | Payer Eligibility Check | Read-only, indexed |
| `custom_eligibility_status` | Data | Eligibility Status | Read-only, fetched from check |

### New Field on IPD Bed Policy

| Fieldname | Type | Label | Default |
|-----------|------|-------|---------|
| `enforce_eligibility_verification` | Select | Enforce Eligibility Verification | Advisory |

Options: Strict / Advisory / Ignore

## Workflow States

Status lifecycle managed via explicit `verification_status` field (not a Frappe Workflow DocType):

```
Pending ──► Verified ──► Expired
   │             ▲           │
   ├──► Conditional ──┤      │
   │         │        ▼      │
   └──► Rejected ◄────┘      │
        │                    │
        └──► Pending ◄───────┘
```

### Allowed Transitions

| From | To |
|------|----|
| Pending | Verified, Conditional, Rejected |
| Verified | Expired |
| Conditional | Verified, Rejected, Expired |
| Rejected | Pending |
| Expired | Pending |

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

## Validation Logic

### Server-side (payer_eligibility_check.py)

1. **Date range**: `valid_from` must be <= `valid_to` (when both set)
2. **Profile ownership**: Payer profile must belong to the same patient
3. **Status transitions**: Only allowed transitions are permitted; invalid transitions throw `ValidationError`
4. **Audit fields**: `submitted_by`/`submitted_on` set on insert; `verified_by`/`verification_datetime` set when moving to Verified/Conditional/Rejected; `last_status_change_by`/`on` set on every status change

### Server-side (eligibility_service.py)

1. `get_latest_active_eligibility()`: Returns latest Verified/Conditional check; excludes checks past their `valid_to` date
2. `check_admission_eligibility()`: Checks policy enforcement level, skips Cash payers, returns eligibility result dict

### Server-side (bed_allocation_service.py)

1. `_validate_eligibility()`: Called during `allocate_bed_on_admission()`; throws on Strict enforcement when no eligibility exists

### Client-side (payer_eligibility_check.js)

1. Status color indicators on form
2. Contextual action buttons for status transitions
3. Prompt for reference number when verifying
4. Patient-filtered queries for payer profile and inpatient record

### Client-side (inpatient_record.js)

1. Eligibility banner shown on Admission Scheduled status
2. "Create Eligibility Check" button
3. Pre-flight eligibility check before "Allocate Bed" dialog
4. Strict: blocks with error message; Advisory: shows confirm dialog

## Notifications

- **Timeline comments**: On Patient and Inpatient Record whenever eligibility status changes
- **On Rejected**: In-app notification to Healthcare Receptionist and TPA Desk User roles
- **On Expired**: In-app notification to TPA Desk User role

## Reporting Impact

### New Report: Payer Eligibility Check Summary

- Script Report on Payer Eligibility Check
- Filters: verification_status, payer_type, company, from_date, to_date
- Color-coded status indicators
- Available to: Healthcare Administrator, TPA Desk User, Accounts User

### Impact on Existing Reports

- Live Bed Board: No direct change
- Payer Profile Expiry: No change

## Test Cases

See [docs/testing/us-c3-payer-eligibility-check.md](../testing/us-c3-payer-eligibility-check.md).

## Migration / Patch Notes

- No data migration patches required
- IPD Bed Policy gains a new field (`enforce_eligibility_verification`) with default "Advisory" — safe for existing installations
- Two new custom fields on Inpatient Record created via `setup/custom_fields.py` on install

## Open Questions / Assumptions

1. **Cash payers do not require eligibility verification** — by definition, Cash patients pay directly
2. **Multiple eligibility checks per admission are allowed** — the service always fetches the latest one, supporting re-verification scenarios
3. **Expired status is set manually** — auto-expiry via scheduler is a follow-up enhancement
4. **Pre-auth reference number** is a free-text field, not validated against external TPA systems
5. **`enforce_eligibility_verification` is distinct from `enforce_payer_eligibility`** — the former is about TPA verification, the latter about tariff-based bed filtering
6. **Attachments** use Frappe's built-in file attachment mechanism (no custom attachment field)
