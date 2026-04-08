# Testing: US-C1 Patient Registration

## Test Files

| File | Type | Description |
|------|------|-------------|
| `alcura_ipd_ext/tests/test_indian_id_validators.py` | Unit | Pure-function validators (no DB) |
| `alcura_ipd_ext/tests/test_patient_duplicate_service.py` | Integration | Duplicate detection with real Patient records |
| `alcura_ipd_ext/tests/test_patient_registration.py` | Integration | Full save flow: validation, consent, MR uniqueness |

## Test Framework

- **Unit tests**: pytest (no Frappe site dependency)
- **Integration tests**: pytest with `conftest.py` fixtures (`admin_session`, `rollback_db`)

## Test Scenarios

### Indian ID Validators (`test_indian_id_validators.py`)

#### Aadhaar

| # | Scenario | Expected |
|---|----------|----------|
| 1 | None/empty value | Valid (no error) |
| 2 | Valid 12-digit Aadhaar (499118665246) | Valid |
| 3 | Valid with spaces (4991 1866 5246) | Valid (stripped) |
| 4 | Valid with dashes | Valid (stripped) |
| 5 | Too short (5 digits) | Invalid: "12 digits" |
| 6 | Too long (13 digits) | Invalid |
| 7 | Non-numeric characters | Invalid |
| 8 | Starts with 0 | Invalid: "cannot start with 0" |
| 9 | Starts with 1 | Invalid: "cannot start with" |
| 10 | Bad Verhoeff checksum | Invalid: "checksum" |

#### PAN

| # | Scenario | Expected |
|---|----------|----------|
| 1 | None/empty | Valid |
| 2 | Valid PAN (ABCDE1234F) | Valid |
| 3 | Valid lowercase (abcde1234f) | Valid (uppercased) |
| 4 | Too short | Invalid |
| 5 | Wrong format (digits first) | Invalid |
| 6 | All letters | Invalid |
| 7 | Contains spaces | Invalid |

#### ABHA Number

| # | Scenario | Expected |
|---|----------|----------|
| 1 | None/empty | Valid |
| 2 | Valid 14-digit | Valid |
| 3 | Valid with spaces | Valid (stripped) |
| 4 | Too short (10 digits) | Invalid: "14 digits" |
| 5 | Non-numeric | Invalid |

#### ABHA Address

| # | Scenario | Expected |
|---|----------|----------|
| 1 | None/empty | Valid |
| 2 | Valid (username@abdm) | Valid |
| 3 | Dots and underscores | Valid |
| 4 | Wrong domain (@gmail.com) | Invalid |
| 5 | No @ sign | Invalid |
| 6 | Uppercase (normalised) | Valid |

#### Indian Mobile

| # | Scenario | Expected |
|---|----------|----------|
| 1 | None/empty | Valid |
| 2 | 10-digit starting with 9 | Valid |
| 3 | With +91 prefix | Valid |
| 4 | With 91 prefix (12 digits) | Valid |
| 5 | With 0 prefix | Valid |
| 6 | With spaces | Valid |
| 7 | Starts with 5 | Invalid |
| 8 | Too short | Invalid |
| 9 | Non-numeric | Invalid |

### Duplicate Detection Service (`test_patient_duplicate_service.py`)

| # | Scenario | Expected |
|---|----------|----------|
| 1 | Exact mobile match | Returns patient with "mobile" reason |
| 2 | No match on different mobile | Empty list |
| 3 | Exclude self by patient name | Self not in results |
| 4 | Exact Aadhaar match | Returns patient with "Aadhaar" reason |
| 5 | Aadhaar with whitespace normalised | Still matches |
| 6 | Exact ABHA match | Returns patient with "ABHA Number" reason |
| 7 | Exact MR number match | Returns patient with "MR Number" reason |
| 8 | Same DOB + similar name (SOUNDEX) | Returns patient with "Similar Name + Same DOB" |
| 9 | Same DOB + completely different name | No match |
| 10 | Same name + different DOB | No match |
| 11 | Multiple reasons for same patient | Match has 2+ reasons |
| 12 | Results sorted by match count desc | First result has most reasons |
| 13 | Completely distinct patients | Empty list |
| 14 | Empty inputs | Empty list |

### Patient Registration Flow (`test_patient_registration.py`)

#### Custom Field Definitions

| # | Scenario | Expected |
|---|----------|----------|
| 1 | Patient key exists in get_custom_fields() | Present |
| 2-5 | Each ID field defined | In field list |
| 6 | Emergency contact fields defined | All 3 in field list |
| 7 | Consent fields defined | All 4 in field list |
| 8 | MR number has unique flag | unique=1 |
| 9 | Aadhaar has search_index | search_index=1 |

#### Save Validation

| # | Scenario | Expected |
|---|----------|----------|
| 1 | Valid Aadhaar saves | Success |
| 2 | Invalid Aadhaar rejects | ValidationError |
| 3 | No Aadhaar saves | Success |
| 4 | Valid PAN saves | Success |
| 5 | PAN normalised to uppercase | ABCDE1234F |
| 6 | Invalid PAN rejects | ValidationError |
| 7 | Valid ABHA saves | Success |
| 8 | Invalid ABHA rejects | ValidationError |
| 9 | Valid emergency phone | Success |
| 10 | Invalid emergency phone rejects | ValidationError |

#### Consent

| # | Scenario | Expected |
|---|----------|----------|
| 1 | Consent collected -> datetime auto-set | Not None |
| 2 | Consent unchecked -> datetime cleared | None |
| 3 | Re-save with consent -> datetime preserved | Same timestamp |

#### MR Uniqueness

| # | Scenario | Expected |
|---|----------|----------|
| 1 | Unique MR number saves | Success |
| 2 | Duplicate MR number rejects | ValidationError "Duplicate MR Number" |
| 3 | Same patient can keep its MR on re-save | Success |

## Coverage Summary

| Category | Tests |
|----------|-------|
| Aadhaar validation | 10 |
| PAN validation | 7 |
| ABHA Number validation | 5 |
| ABHA Address validation | 6 |
| Mobile validation | 9 |
| Duplicate by mobile | 3 |
| Duplicate by Aadhaar | 2 |
| Duplicate by ABHA | 1 |
| Duplicate by MR | 1 |
| Fuzzy name+DOB | 3 |
| Multiple reasons | 2 |
| No false positives | 2 |
| Custom field definitions | 9 |
| Aadhaar save validation | 3 |
| PAN save validation | 3 |
| ABHA save validation | 2 |
| Emergency phone validation | 2 |
| Consent timestamp | 3 |
| MR uniqueness | 3 |
| **Total** | **76** |

## Running Tests

### Unit tests only (no Frappe site needed)

```bash
cd /path/to/frappe-bench/apps/alcura_ipd_ext
pytest alcura_ipd_ext/tests/test_indian_id_validators.py -v
```

### Integration tests (requires test site)

```bash
cd /path/to/frappe-bench/apps/alcura_ipd_ext
pytest alcura_ipd_ext/tests/test_patient_duplicate_service.py -v
pytest alcura_ipd_ext/tests/test_patient_registration.py -v
```

### All US-C1 tests

```bash
pytest alcura_ipd_ext/tests/test_indian_id_validators.py \
       alcura_ipd_ext/tests/test_patient_duplicate_service.py \
       alcura_ipd_ext/tests/test_patient_registration.py -v
```
