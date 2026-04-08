# US-F3: Support Radiology and Procedure Orders

## Purpose

Enable doctors to place radiology investigations and clinical procedures as tracked service orders with consistent lifecycle and SLA management.

## Scope

- Radiology and procedure order creation with preparation instructions
- Consistent model with medication and lab order types
- Support for bedside vs. department execution
- Department notification and SLA tracking

## Reused Doctypes

- **Clinical Procedure Template** — linked via `procedure_template`
- **Clinical Procedure** — linked via `linked_clinical_procedure` for execution tracking
- **Patient Encounter** — source via `procedure_prescription` child table

## Fields (Radiology/Procedure-specific)

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| procedure_template | Link (Clinical Procedure Template) | No | Standard template |
| procedure_name | Data | Yes | Investigation/procedure name |
| body_site | Data | No | Anatomical location |
| is_bedside | Check | No | Bedside vs. department |
| prep_instructions | Small Text | No | Patient preparation notes |
| linked_clinical_procedure | Link (Clinical Procedure) | No | Read-only execution link |

## Order Type Distinction

- `order_type = "Radiology"` — for imaging investigations (X-Ray, CT, MRI, USG)
- `order_type = "Procedure"` — for clinical procedures (Central Line, Lumbar Puncture, etc.)

Both share the same field set; the distinction allows different SLA configurations and queue routing.

## Test Cases

- Procedure order creation with body_site
- Radiology order with urgent urgency
- PE procedure_prescription auto-creates orders
- Procedure name required validation
