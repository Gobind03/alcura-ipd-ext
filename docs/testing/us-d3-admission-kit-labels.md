# US-D3: Admission Kit and Labels — Test Scenarios

## Test File

`alcura_ipd_ext/tests/test_label_helpers.py`

## Test Cases

### Label Helpers

| # | Test | Description |
|---|------|-------------|
| 1 | `test_generate_qr_svg_returns_img_or_placeholder` | QR generation returns `<img>` or `[QR:...]` placeholder |
| 2 | `test_qr_svg_encodes_data` | QR output contains base64 data or plaintext fallback |
| 3 | `test_generate_barcode_svg_returns_svg_or_placeholder` | Barcode returns `<svg>` or monospace text |
| 4 | `test_format_allergy_markers_empty_for_no_patient` | Returns empty for None/empty patient |
| 5 | `test_format_allergy_markers_for_patient_without_allergies` | Returns string (possibly empty) |
| 6 | `test_get_admission_label_context_returns_dict` | Context has all expected keys |
| 7 | `test_label_context_patient_fields` | Patient demographics populated correctly |
| 8 | `test_label_context_bedside_url` | Bedside URL formatted with IR name |

### Bedside Profile

| # | Test | Description |
|---|------|-------------|
| 9 | `test_bedside_context_requires_ir_param` | Missing IR param raises ValidationError |
| 10 | `test_bedside_context_builds_for_valid_ir` | Context populates for valid IR |
| 11 | `test_bedside_rejects_nonexistent_ir` | Invalid IR name raises DoesNotExistError |

## Coverage Areas

- **QR/Barcode**: graceful degradation without optional libraries
- **Context builder**: data aggregation from IR, Patient, bed hierarchy
- **Bedside profile**: authentication, authorization, error handling
- **Print formats**: tested indirectly via context builder
