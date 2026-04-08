"""Service for IPD Intake Assessment creation and lifecycle management.

Handles:
- Template selection based on specialty and target role
- Assessment creation from a template for a given Inpatient Record
- Response saving with type coercion
- Completion validation (mandatory fields) and status transition
- Scored Patient Assessment auto-creation and status tracking
"""

from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import now_datetime


# ── Template Selection ───────────────────────────────────────────────


def select_template(
	specialty: str | None = None,
	target_role: str = "Both",
) -> "frappe.Document | None":
	"""Find the best-matching active IPD Intake Assessment Template.

	Priority:
	1. Exact specialty + exact target_role match
	2. Exact specialty + target_role = "Both"
	3. No specialty (universal) + exact target_role
	4. No specialty + target_role = "Both"
	"""
	candidates = [
		{"specialty": specialty, "target_role": target_role},
		{"specialty": specialty, "target_role": "Both"},
		{"specialty": ("in", ["", None]), "target_role": target_role},
		{"specialty": ("in", ["", None]), "target_role": "Both"},
	]

	if not specialty:
		candidates = candidates[2:]

	for filters in candidates:
		name = frappe.db.get_value(
			"IPD Intake Assessment Template",
			{**filters, "is_active": 1},
			"name",
		)
		if name:
			return frappe.get_doc("IPD Intake Assessment Template", name)

	return None


# ── Assessment Creation ──────────────────────────────────────────────


def create_intake_assessment(
	inpatient_record: str,
	template_name: str | None = None,
) -> dict:
	"""Create an IPD Intake Assessment from the best-matching template.

	If ``template_name`` is not supplied, auto-selects using the IR's
	medical department.

	Returns:
		Dict with ``assessment`` (name), ``status``, and ``template`` keys.

	Raises:
		frappe.ValidationError: If no matching template is found.
	"""
	ir_doc = frappe.get_doc("Inpatient Record", inpatient_record)

	if template_name:
		template = frappe.get_doc("IPD Intake Assessment Template", template_name)
	else:
		specialty = ir_doc.medical_department or ""
		template = select_template(specialty=specialty)

	if not template:
		frappe.throw(
			_("No active Intake Assessment Template found for specialty '{0}'. "
			  "Please create a template first.").format(
				ir_doc.medical_department or "All"
			),
			exc=frappe.ValidationError,
		)

	_check_duplicate(inpatient_record, template.name)

	assessment = _build_from_template(ir_doc, template)

	# Link first assessment to IR for quick access
	if not ir_doc.get("custom_intake_assessment"):
		ir_doc.db_set(
			"custom_intake_assessment", assessment.name, update_modified=False
		)

	ir_doc.add_comment(
		"Info",
		_("Intake Assessment {0} created from template {1}.").format(
			frappe.bold(assessment.name), frappe.bold(template.name)
		),
	)

	scored_assessments = _create_scored_assessments(ir_doc, template, assessment)

	return {
		"assessment": assessment.name,
		"status": assessment.status,
		"template": template.name,
		"scored_assessments": scored_assessments,
	}


def _check_duplicate(inpatient_record: str, template_name: str):
	"""Prevent creating two assessments for the same IR + template pair."""
	existing = frappe.db.exists(
		"IPD Intake Assessment",
		{"inpatient_record": inpatient_record, "template": template_name},
	)
	if existing:
		frappe.throw(
			_("An Intake Assessment already exists for {0} with template {1}: {2}").format(
				frappe.bold(inpatient_record),
				frappe.bold(template_name),
				frappe.bold(existing),
			),
			exc=frappe.ValidationError,
		)


def _build_from_template(
	ir_doc: "frappe.Document",
	template: "frappe.Document",
) -> "frappe.Document":
	"""Construct the assessment document from a template."""
	doc = frappe.get_doc({
		"doctype": "IPD Intake Assessment",
		"patient": ir_doc.patient,
		"inpatient_record": ir_doc.name,
		"template": template.name,
		"template_version": template.version or 1,
		"company": ir_doc.company,
		"specialty": template.specialty,
		"assessment_datetime": now_datetime(),
		"status": "Draft",
	})

	for field in sorted(template.form_fields or [], key=lambda f: f.display_order or 0):
		doc.append("responses", {
			"section_label": field.section_label,
			"field_label": field.field_label,
			"field_type": field.field_type,
			"text_value": field.default_value if field.field_type not in ("Check", "Int", "Float") else "",
			"numeric_value": 0,
			"check_value": 0,
			"is_mandatory": field.is_mandatory,
		})

	doc.insert(ignore_permissions=True)
	return doc


def _create_scored_assessments(
	ir_doc: "frappe.Document",
	template: "frappe.Document",
	intake_doc: "frappe.Document",
) -> list[dict]:
	"""Create standard Patient Assessment docs for each scored assessment
	linked in the template."""
	created = []

	for scored in template.scored_assessments or []:
		pa_template = frappe.get_doc(
			"Patient Assessment Template", scored.assessment_template
		)

		pa = frappe.get_doc({
			"doctype": "Patient Assessment",
			"patient": ir_doc.patient,
			"assessment_template": scored.assessment_template,
			"assessment_datetime": now_datetime(),
			"company": ir_doc.company,
			"custom_inpatient_record": ir_doc.name,
			"custom_intake_assessment": intake_doc.name,
		})

		for detail in pa_template.parameters or []:
			score_options = "\n".join(
				str(i)
				for i in range(
					pa_template.scale_min or 0,
					(pa_template.scale_max or 5) + 1,
				)
			)
			pa.append("assessment_sheet", {
				"parameter": detail.assessment_parameter,
				"score": str(pa_template.scale_min or 0),
			})
			# Frappe sets score options dynamically via JS; we set the default

		pa.insert(ignore_permissions=True)

		created.append({
			"name": pa.name,
			"template": scored.assessment_template,
			"section_label": scored.section_label,
		})

	return created


# ── Response Saving ──────────────────────────────────────────────────


def save_responses(assessment_name: str, responses: list[dict]) -> dict:
	"""Bulk-save response values for an intake assessment.

	Args:
		assessment_name: Name of the IPD Intake Assessment.
		responses: List of dicts with ``idx`` (1-based), and one or more of
			``text_value``, ``numeric_value``, ``check_value``.

	Returns:
		Dict with ``assessment`` and ``status`` keys.
	"""
	doc = frappe.get_doc("IPD Intake Assessment", assessment_name)

	if doc.status == "Completed":
		frappe.throw(
			_("Assessment {0} is already Completed and cannot be modified.").format(
				frappe.bold(doc.name)
			),
			exc=frappe.ValidationError,
		)

	response_map = {r.idx: r for r in doc.responses}

	for entry in responses:
		idx = entry.get("idx")
		row = response_map.get(idx)
		if not row:
			continue

		if "text_value" in entry:
			row.text_value = entry["text_value"]
		if "numeric_value" in entry:
			row.numeric_value = entry["numeric_value"]
		if "check_value" in entry:
			row.check_value = entry["check_value"]

	doc.save(ignore_permissions=True)

	return {"assessment": doc.name, "status": doc.status}


# ── Completion ───────────────────────────────────────────────────────


def complete_intake_assessment(assessment_name: str) -> dict:
	"""Validate and transition assessment to Completed.

	Returns:
		Dict with ``assessment``, ``status``, ``completed_by``, ``completed_on``.
	"""
	doc = frappe.get_doc("IPD Intake Assessment", assessment_name)

	if doc.status == "Completed":
		frappe.throw(
			_("Assessment {0} is already Completed.").format(frappe.bold(doc.name)),
			exc=frappe.ValidationError,
		)

	doc.complete()

	return {
		"assessment": doc.name,
		"status": doc.status,
		"completed_by": doc.completed_by,
		"completed_on": str(doc.completed_on),
	}


# ── Scored Assessment Status ─────────────────────────────────────────


def get_pending_scored_assessments(assessment_name: str) -> list[dict]:
	"""Return scored Patient Assessments linked to this intake that are
	still in Draft (not yet submitted)."""
	return frappe.get_all(
		"Patient Assessment",
		filters={
			"custom_intake_assessment": assessment_name,
			"docstatus": 0,
		},
		fields=["name", "assessment_template", "patient", "assessment_datetime"],
	)


def get_intake_assessments_for_ir(inpatient_record: str) -> list[dict]:
	"""Return all intake assessments for an Inpatient Record."""
	return frappe.get_all(
		"IPD Intake Assessment",
		filters={"inpatient_record": inpatient_record},
		fields=[
			"name", "template", "specialty", "status",
			"assessed_by", "assessment_datetime",
			"completed_by", "completed_on",
		],
		order_by="creation asc",
	)
