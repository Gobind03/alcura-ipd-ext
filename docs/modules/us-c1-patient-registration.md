# US-C1: Patient Registration with Demographic and Statutory Details

## Purpose

Provide a single patient master record that captures Indian statutory identifiers (Aadhaar, ABHA, PAN), hospital MR number, emergency contact, and consent information. Duplicate detection prevents accidental creation of redundant patient records.

## Scope

- Extend the standard Patient doctype with custom fields
- Server-side validation for Indian ID formats (Aadhaar Verhoeff, PAN, ABHA)
- Duplicate detection by mobile, Aadhaar, ABHA, MR number, and fuzzy name+DOB
- Client-side warning UX for potential duplicates
- Consent and privacy acknowledgment tracking with auto-timestamps
- MR number uniqueness enforcement

## Reused Standard DocTypes

| DocType | How Used |
|---------|----------|
| Patient | Extended with custom fields via `setup/custom_fields.py` |
| Customer | Standard Patient-to-Customer link (unchanged) |

## New Custom DocTypes

None. All functionality is delivered through custom fields on the standard Patient doctype and supporting Python/JS modules.

## Fields Added

### Indian Statutory Identifiers (Section, after `uid`)

| Fieldname | Type | Label | Indexed | Notes |
|-----------|------|-------|---------|-------|
| `custom_aadhaar_number` | Data | Aadhaar Number | Yes | 12-digit, Verhoeff-validated |
| `custom_abha_number` | Data | ABHA Number | Yes | 14-digit ABHA health ID |
| `custom_abha_address` | Data | ABHA Address | No | Format: username@abdm |
| `custom_pan_number` | Data | PAN Number | No | AAAAA9999A format, auto-uppercased |
| `custom_mr_number` | Data | MR Number | Yes | Hospital medical record number, unique |

### Emergency Contact (Section, after `phone`)

| Fieldname | Type | Label | Notes |
|-----------|------|-------|-------|
| `custom_emergency_contact_name` | Data | Emergency Contact Name | |
| `custom_emergency_contact_relation` | Select | Relation | Parent/Spouse/Child/Sibling/Guardian/Other |
| `custom_emergency_contact_phone` | Data | Emergency Contact Phone | Validated as Indian mobile |
| `custom_emergency_contact_address` | Small Text | Emergency Contact Address | |

### Consent and Privacy (Section, collapsible)

| Fieldname | Type | Label | Notes |
|-----------|------|-------|-------|
| `custom_consent_collected` | Check | Consent Collected | |
| `custom_consent_datetime` | Datetime | Consent Date/Time | Read-only, auto-set on consent toggle |
| `custom_consent_given_by` | Data | Consent Given By | Name if not the patient |
| `custom_privacy_notice_acknowledged` | Check | Privacy Notice Acknowledged | |

## Workflow States

Not applicable. Patient is a non-submittable master document. The standard Patient `status` field (Active/Disabled) is unchanged.

## Permissions

No permission changes. Existing Patient permissions apply. The custom fields inherit the Patient doctype's role-based access.

## Validation Logic

### Server-side (overrides/patient.py)

1. **Aadhaar**: 12-digit, cannot start with 0 or 1, Verhoeff checksum
2. **PAN**: AAAAA9999A regex, auto-normalised to uppercase
3. **ABHA Number**: 14-digit numeric
4. **ABHA Address**: username@abdm format
5. **Emergency Contact Phone**: Valid Indian mobile (10-digit, starts with 6-9)
6. **Consent timestamp**: Auto-set when consent is collected, cleared when unchecked
7. **MR Number uniqueness**: Explicit check with user-friendly error message

### Client-side (public/js/patient.js)

1. Inline validation hints for Aadhaar, PAN, ABHA (non-blocking)
2. Consent datetime auto-set on toggle
3. Duplicate check triggered on mobile/Aadhaar field change (debounced 600ms)
4. Duplicate warning dialog on `before_save` with option to proceed

## Duplicate Detection

### Strategy

| Check Type | Field(s) | Confidence |
|-----------|----------|-----------|
| Exact mobile | `mobile` | High |
| Exact Aadhaar | `custom_aadhaar_number` | High |
| Exact ABHA | `custom_abha_number` | High |
| Exact MR Number | `custom_mr_number` | High |
| Fuzzy name+DOB | `first_name` + `dob` via SOUNDEX | Medium |

### Behaviour

- Advisory only: user sees a warning dialog and can proceed
- Results sorted by number of matching reasons (most matches first)
- Deduplication across match types (same patient matched by mobile AND Aadhaar shows once with both reasons)

### API Endpoint

`alcura_ipd_ext.api.patient.check_patient_duplicates` (whitelisted)

## Notifications

None for this story. Future stories may add notifications for registration events.

## Reporting Impact

Patient registration fields enable future reports:
- Registration volume by date/source
- Consent compliance tracking
- Duplicate detection audit log

## Test Cases

See [docs/testing/us-c1-patient-registration.md](../testing/us-c1-patient-registration.md).

## Open Questions / Assumptions

1. **`insert_after` field names**: Based on standard Frappe Healthcare Patient schema. The `uid` field is assumed to exist. If Marley Health has renamed it, `insert_after` values need adjustment at install time.
2. **No MR number auto-generation**: MR number is manual entry in this story. Auto-generation (e.g. `MR-{year}-{sequence}`) is a follow-up.
3. **SOUNDEX for fuzzy matching**: MySQL/MariaDB SOUNDEX is used for name similarity. Works reasonably for transliterated Indian names. Metaphone can replace it later.
4. **No ABHA API integration**: ABHA number/address are stored as data fields. ABDM API verification is out of scope.
5. **Patient remains non-submittable**: We do not change the doctype's submission workflow.
6. **Duplicate policy is advisory**: No hard block. Configurable policy (warn/soft-block/hard-block) can be added in a future story.
