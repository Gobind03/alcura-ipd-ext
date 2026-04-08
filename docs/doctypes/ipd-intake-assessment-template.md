# IPD Intake Assessment Template

## Purpose

Master template defining the structure of a specialty's intake assessment form. Each template contains structured form fields grouped by section, plus links to scored Patient Assessment Templates (e.g. GCS, Pain Scale) that should be completed alongside.

## Module

Alcura IPD Extensions

## Naming

`autoname: field:template_name` — named by the unique template name.

## Fields

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| template_name | Data | Yes | Unique template identifier |
| specialty | Link → Medical Department | No | Specialty association for auto-selection |
| target_role | Select | Yes | Nursing User / Physician / Both |
| version | Int | No | Default 1; increment on template updates |
| is_active | Check | No | Default 1; inactive templates are skipped |
| description | Small Text | No | Human-readable description |
| form_fields | Table → IPD Intake Template Field | No | Structured form field definitions |
| scored_assessments | Table → IPD Intake Scored Assessment | No | Links to scored Patient Assessment Templates |

## Child Tables

### IPD Intake Template Field

| Field | Type | Notes |
|-------|------|-------|
| section_label | Data | Visual section grouping |
| field_label | Data (required) | Label shown to user |
| field_type | Select | Text / Long Text / Small Text / Select / Check / Int / Float / Date / Rating |
| options | Small Text | Newline-separated options for Select type |
| is_mandatory | Check | Whether response is required for completion |
| display_order | Int | Rendering order |
| role_visibility | Select | All / Nursing User / Physician |
| default_value | Data | Pre-populated default |

### IPD Intake Scored Assessment

| Field | Type | Notes |
|-------|------|-------|
| assessment_template | Link → Patient Assessment Template (required) | Standard scored template to include |
| section_label | Data | Section grouping for display |
| is_mandatory | Check | Whether this scored assessment must be completed |
| display_order | Int | Rendering order |

## Validations

1. Must have at least one form field or scored assessment
2. Field labels must be unique within a section
3. Select fields must have non-empty options

## Permissions

| Role | Access |
|------|--------|
| Healthcare Administrator | Full CRUD |
| Nursing User | Read only |
| Physician | Read only |
| IPD Admission Officer | Read only |

## Indexes

- `specialty` (for template selection queries)

## US-E2 Enhancements

The common nursing intake fields (`_COMMON_NURSING_FIELDS`) were expanded with three new sections:

- **Diet & Nutrition**: Current Diet, Dietary Restrictions, Swallowing Difficulty, Feeding Assistance
- **Elimination**: Bowel Pattern, Last Bowel Movement, Bladder Function, Urinary Catheter, Catheter Details
- **Device Lines & Access**: Expanded from 2 fields to 9 fields covering IV access, central lines, arterial lines, nasogastric tubes, drains, and other devices

Migration patch `v0_0_3/enhance_nursing_intake_fields` adds these fields to existing templates.

See [modules/us-e2-nursing-admission-assessment.md](../modules/us-e2-nursing-admission-assessment.md).

## Related DocTypes

- Patient Assessment Template (standard, linked via scored_assessments)
- IPD Intake Assessment (instances created from this template)
- Medical Department (standard, linked via specialty)
