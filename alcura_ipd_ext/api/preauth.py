"""Whitelisted API endpoints for TPA Pre-authorization.

Usage from client:
	frappe.call("alcura_ipd_ext.api.preauth.create_preauth_from_admission", ...)
	frappe.call("alcura_ipd_ext.api.preauth.create_preauth_from_order", ...)
"""

from __future__ import annotations

import frappe
from frappe import _


@frappe.whitelist()
def create_preauth_from_admission(inpatient_record: str) -> str:
	"""Create a TPA Preauth Request pre-filled from an Inpatient Record.

	Returns the name of the newly created (Draft) preauth request.
	"""
	frappe.has_permission("TPA Preauth Request", "create", throw=True)

	ir = frappe.get_doc("Inpatient Record", inpatient_record)
	payer_profile_name = ir.get("custom_patient_payer_profile")
	if not payer_profile_name:
		frappe.throw(
			_("No payer profile linked to Inpatient Record {0}").format(inpatient_record),
			title=_("Missing Payer Profile"),
		)

	profile = frappe.get_doc("Patient Payer Profile", payer_profile_name)
	if profile.payer_type == "Cash":
		frappe.throw(
			_("Pre-authorization is not applicable for Cash payer type"),
			title=_("Invalid Payer Type"),
		)

	practitioner = ir.get("primary_practitioner") or ""
	department = ""
	if practitioner:
		department = frappe.db.get_value(
			"Healthcare Practitioner", practitioner, "department"
		) or ""

	doc = frappe.new_doc("TPA Preauth Request")
	doc.update({
		"patient": ir.patient,
		"inpatient_record": ir.name,
		"patient_payer_profile": payer_profile_name,
		"company": ir.company,
		"treating_practitioner": practitioner,
		"treating_department": department,
		"admission_type": ir.get("custom_admission_priority") or "Planned",
		"expected_los_days": ir.get("custom_expected_los_days") or 0,
		"primary_diagnosis": ir.get("admission_instruction") or "",
	})
	doc.insert()
	return doc.name


@frappe.whitelist()
def create_preauth_from_order(clinical_order: str) -> str:
	"""Create a TPA Preauth Request pre-filled from an IPD Clinical Order.

	Intended for procedure/radiology orders that require separate pre-auth.
	Returns the name of the newly created (Draft) preauth request.
	"""
	frappe.has_permission("TPA Preauth Request", "create", throw=True)

	order = frappe.get_doc("IPD Clinical Order", clinical_order)
	if order.order_type not in ("Procedure", "Radiology"):
		frappe.throw(
			_("Pre-auth from order is only supported for Procedure/Radiology orders"),
			title=_("Invalid Order Type"),
		)

	ir = frappe.get_doc("Inpatient Record", order.inpatient_record)
	payer_profile_name = ir.get("custom_patient_payer_profile")
	if not payer_profile_name:
		frappe.throw(
			_("No payer profile linked to Inpatient Record {0}").format(order.inpatient_record),
			title=_("Missing Payer Profile"),
		)

	profile = frappe.get_doc("Patient Payer Profile", payer_profile_name)
	if profile.payer_type == "Cash":
		frappe.throw(
			_("Pre-authorization is not applicable for Cash payer type"),
			title=_("Invalid Payer Type"),
		)

	doc = frappe.new_doc("TPA Preauth Request")
	doc.update({
		"patient": order.patient,
		"inpatient_record": order.inpatient_record,
		"patient_payer_profile": payer_profile_name,
		"company": order.company,
		"treating_practitioner": order.ordering_practitioner or "",
		"treating_department": order.target_department or order.ordering_department or "",
		"procedure_name": order.procedure_name or order.lab_test_name or "",
		"primary_diagnosis": order.indication or order.clinical_notes or "",
	})
	doc.insert()
	return doc.name


@frappe.whitelist()
def get_preauth_summary(inpatient_record: str) -> list[dict]:
	"""Return summary of all preauth requests for an inpatient record."""
	frappe.has_permission("TPA Preauth Request", "read", throw=True)

	return frappe.db.get_all(
		"TPA Preauth Request",
		filters={"inpatient_record": inpatient_record},
		fields=[
			"name", "status", "requested_amount", "approved_amount",
			"preauth_reference_number", "valid_from", "valid_to",
			"treating_practitioner_name", "procedure_name",
		],
		order_by="creation desc",
	)
