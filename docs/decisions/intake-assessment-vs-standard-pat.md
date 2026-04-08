# ADR: Intake Assessment Architecture — Standard Extension vs Custom DocType

## Status

Accepted

## Context

US-E1 requires digital intake assessment forms for IPD admissions. The standard Healthcare module provides:

- **Patient Assessment Template**: defines a flat list of parameters with a numeric score scale (min/max)
- **Patient Assessment**: records scored parameter values per patient, designed for rehabilitation assessments

IPD intake forms require:
- Multi-section structured forms (Vitals, History, Systems Review, etc.)
- Mixed field types (text, select, check, numeric, long text) — not just scores
- Specialty-based template routing (Medicine, Surgery, ICU, etc.)
- Role-specific templates (nurse vs doctor assessments)
- Template versioning for audit
- Linkage to the inpatient journey

## Decision

**Hybrid approach: extend standard for scored components, create custom for structured forms.**

1. **Reuse** standard Patient Assessment Template / Patient Assessment for scored clinical scales (GCS, Pain NRS, Morse Fall Scale, Braden, MUST). Add custom fields for IPD context (`custom_specialty`, `custom_inpatient_record`, `custom_intake_assessment`, `custom_assessment_context`).

2. **Create** custom IPD Intake Assessment Template / IPD Intake Assessment doctypes for the structured, multi-section intake form. These support varied field types, section grouping, role visibility, and specialty routing — capabilities that do not fit the standard scored-parameter model.

3. **Link** the two systems: IPD Intake Assessment Template can reference standard Patient Assessment Templates via a child table. When an intake assessment is created, the linked scored assessments are automatically created as standard Patient Assessment documents and back-linked.

## Alternatives Considered

### A. Force everything into standard Patient Assessment

Rejected because:
- Standard template only supports scored parameters (numeric scale)
- No section grouping in the standard template
- No support for text, select, or checkbox field types
- Would require heavy custom fields on both template and assessment child tables, making the standard UI confusing
- The standard assessment form would show irrelevant columns for non-scored fields

### B. Fully custom system ignoring standard doctypes

Rejected because:
- Would duplicate scored assessment functionality already in standard
- Loses compatibility with standard Healthcare reports and features
- Violates the requirement to "extend standard assessment framework first"

### C. Web Form approach

Rejected because:
- Web Forms are portal-facing, not ideal for Desk workflows
- Limited programmability for status transitions and audit
- Harder to link to the Inpatient Record lifecycle

## Consequences

**Positive:**
- Standard scored assessments remain clean and compatible with Healthcare module
- Intake forms get purpose-built structure without compromising the standard
- Scored assessments are automatically created and linked — single workflow for both
- Template system is flexible enough for any specialty
- Clean app isolation — no modification of standard doctypes beyond custom fields

**Negative:**
- Two template systems to manage (standard Patient Assessment Template for scores + IPD Intake Assessment Template for forms)
- Slight learning curve for administrators setting up both
- Fixture data is needed to pre-populate standard parameters and templates

## Related Documents

- [modules/us-e1-intake-assessment.md](../modules/us-e1-intake-assessment.md)
- [doctypes/ipd-intake-assessment-template.md](../doctypes/ipd-intake-assessment-template.md)
- [doctypes/ipd-intake-assessment.md](../doctypes/ipd-intake-assessment.md)
