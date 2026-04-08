"""Bedside profile page controller.

QR target page that displays privacy-conscious patient bedside information.
Requires login with appropriate healthcare role.
"""

from __future__ import annotations

import frappe
from frappe import _

no_cache = 1


def get_context(context):
	ir_name = frappe.form_dict.get("ir")

	if not ir_name:
		frappe.throw(_("Missing Inpatient Record parameter."), frappe.ValidationError)

	if frappe.session.user == "Guest":
		frappe.throw(_("Login required to view bedside profile."), frappe.PermissionError)

	user_roles = frappe.get_roles()
	allowed_roles = {"Nursing User", "Healthcare Administrator", "Physician", "Administrator"}
	if not allowed_roles.intersection(set(user_roles)):
		frappe.throw(
			_("You do not have permission to view bedside profiles."),
			frappe.PermissionError,
		)

	if not frappe.db.exists("Inpatient Record", ir_name):
		frappe.throw(_("Inpatient Record {0} not found.").format(ir_name), frappe.DoesNotExistError)

	ir = frappe.get_doc("Inpatient Record", ir_name)

	patient_doc = frappe.get_doc("Patient", ir.patient) if ir.patient else frappe._dict()

	practitioner_name = ""
	if ir.primary_practitioner:
		practitioner_name = frappe.db.get_value(
			"Healthcare Practitioner",
			ir.primary_practitioner,
			"practitioner_name",
		) or ir.primary_practitioner

	ward_name = ""
	if ir.get("custom_current_ward"):
		ward_name = frappe.db.get_value(
			"Hospital Ward", ir.custom_current_ward, "ward_name"
		) or ""

	bed_label = ""
	if ir.get("custom_current_bed"):
		bed_label = frappe.db.get_value(
			"Hospital Bed", ir.custom_current_bed, "bed_label"
		) or ir.custom_current_bed

	from alcura_ipd_ext.utils.label_helpers import format_allergy_markers

	context.update({
		"title": _("Bedside Profile"),
		"ir_name": ir.name,
		"patient_name": ir.patient_name or "",
		"sex": patient_doc.get("sex", ""),
		"status": ir.status,
		"practitioner": practitioner_name,
		"department": ir.medical_department or "",
		"ward_name": ward_name,
		"bed_label": bed_label,
		"room": ir.get("custom_current_room", ""),
		"allergy_html": format_allergy_markers(ir.patient),
		"admission_date": frappe.utils.format_date(ir.admitted_datetime) if ir.admitted_datetime else "",
	})
