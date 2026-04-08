# US-D3: Admission Kit and Labels

## Purpose

Generate wristband labels, bed tags, and patient file covers for reliable bedside identification. Support barcode/QR codes for digital lookup and include a privacy-conscious bedside profile web page.

## Scope

- Three Jinja-based print formats for Inpatient Record: Wristband Label, Bed Tag, File Cover
- QR code and barcode generation helpers registered as Jinja methods
- Bedside profile web page (QR scan target) with role-based access
- "Print Labels" dropdown on the Inpatient Record form when status is "Admitted"
- Admission label context builder consolidating data from IR, Patient, and bed hierarchy

## Reused Standard DocTypes

| DocType | How Used |
|---------|----------|
| Inpatient Record | Target doctype for all print formats |
| Patient | Demographics: name, DOB, sex, blood group, allergies, mobile |
| Healthcare Practitioner | Consultant name on labels |
| Hospital Bed | Bed label |
| Hospital Room | Room name |
| Hospital Ward | Ward name |

## New Custom DocTypes

None.

## Print Formats

### IPD Wristband Label

- **Size**: ~200mm x 25mm (wristband strip)
- **Content**: Patient name, MR number, DOB/Age, sex, blood group, allergy marker, consultant, ward/bed, QR code (bedside profile URL), IR name, admission date
- **File**: `print_format/ipd_wristband_label/`

### IPD Bed Tag

- **Size**: ~100mm x 70mm (card)
- **Content**: Patient name (large), MR number, age/sex, consultant, ward/room/bed (large), admission date, blood group, allergy alert, payer, company, IR name
- **File**: `print_format/ipd_bed_tag/`

### IPD File Cover

- **Size**: A4
- **Content**: Full patient demographics, admission details (IPD number, date, consultant, department, ward/room/bed, priority, payer), barcode (IR name), QR code (bedside profile), sticker area
- **File**: `print_format/ipd_file_cover/`

## Helper Code

### `utils/label_helpers.py`

| Function | Purpose |
|----------|---------|
| `generate_qr_svg(data, box_size)` | QR code as inline PNG data URI; fallback to text |
| `generate_barcode_svg(data, type)` | Code128 barcode as inline SVG; fallback to monospace |
| `format_allergy_markers(patient)` | HTML snippet with allergy alerts from Patient allergies |
| `get_admission_label_context(ir)` | Complete context dict for all print formats |

All four functions are registered as Jinja methods in `hooks.py`.

## Bedside Profile Page

- **URL**: `/bedside_profile?ir=<inpatient_record_name>`
- **Access**: requires login with Nursing User, Healthcare Administrator, or Physician role
- **Content**: Patient name (no DOB), sex, IPD number, consultant, department, ward, bed, admission date, allergy alert
- **Privacy**: no financial, diagnostic, or full demographic data shown
- **Files**: `www/bedside_profile.py`, `www/bedside_profile.html`

## Permissions

| Component | Roles Required |
|-----------|---------------|
| Print labels | Read on Inpatient Record |
| View bedside profile | Nursing User, Healthcare Administrator, Physician |

## Validation Logic

- Bedside profile rejects unauthenticated (Guest) users
- Bedside profile validates IR existence before rendering
- QR/barcode helpers gracefully degrade if optional libraries are missing

## Notifications

None (print formats are on-demand).

## Reporting Impact

None directly. Print formats enhance operational workflows.

## Test Cases

See [testing/us-d3-admission-kit-labels.md](../testing/us-d3-admission-kit-labels.md).

## Open Questions / Assumptions

1. QR code generation depends on the `qrcode` Python library (with PIL). If not installed, a text placeholder is shown.
2. Barcode generation depends on `python-barcode`. If not installed, the IR name is shown in monospace.
3. Wristband dimensions assume a standard thermal label printer. Hospitals may need to adjust CSS for their specific printer model.
4. The bedside profile page uses Frappe's web template system and inherits the site's authentication.
