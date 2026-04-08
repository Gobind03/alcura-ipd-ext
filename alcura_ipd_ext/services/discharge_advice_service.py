"""Discharge advice service.

Provides domain logic for creating and managing IPD Discharge Advice
documents, bridging the doctor's discharge decision to downstream
departments (billing, nursing, pharmacy, TPA).
"""

from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import now_datetime


def create_discharge_advice(
	inpatient_record: str,
	consultant: str,
	expected_discharge_datetime: str,
	discharge_type: str = "Normal",
	condition_at_discharge: str = "",
	primary_diagnosis: str = "",
	secondary_diagnoses: str = "",
	discharge_medications: str = "",
	follow_up_instructions: str = "",
	follow_up_date: str = "",
	follow_up_practitioner: str = "",
	diet_instructions: str = "",
	activity_restrictions: str = "",
	warning_signs: str = "",
	additional_instructions: str = "",
) -> str:
	"""Create and submit a discharge advice for an admitted patient.

	Returns the name of the created IPD Discharge Advice.
	"""
	ir_doc = frappe.get_doc("Inpatient Record", inpatient_record)

	if ir_doc.status not in ("Admitted", "Discharge Scheduled"):
		frappe.throw(
			_("Cannot raise discharge advice: Inpatient Record {0} has status {1}.").format(
				frappe.bold(inpatient_record), frappe.bold(ir_doc.status)
			),
			exc=frappe.ValidationError,
		)

	existing = frappe.db.get_value(
		"IPD Discharge Advice",
		{
			"inpatient_record": inpatient_record,
			"status": ("not in", ("Cancelled", "Completed")),
		},
		"name",
	)
	if existing:
		frappe.throw(
			_("An active discharge advice {0} already exists for this admission.").format(
				frappe.bold(existing)
			),
			exc=frappe.ValidationError,
		)

	doc = frappe.new_doc("IPD Discharge Advice")
	doc.update({
		"inpatient_record": inpatient_record,
		"patient": ir_doc.patient,
		"company": ir_doc.company,
		"consultant": consultant,
		"expected_discharge_datetime": expected_discharge_datetime,
		"discharge_type": discharge_type,
		"condition_at_discharge": condition_at_discharge,
		"primary_diagnosis": primary_diagnosis,
		"secondary_diagnoses": secondary_diagnoses,
		"discharge_medications": discharge_medications,
		"follow_up_instructions": follow_up_instructions,
		"follow_up_date": follow_up_date or None,
		"follow_up_practitioner": follow_up_practitioner or None,
		"diet_instructions": diet_instructions,
		"activity_restrictions": activity_restrictions,
		"warning_signs": warning_signs,
		"additional_instructions": additional_instructions,
	})
	doc.insert(ignore_permissions=True)

	doc.submit_advice()

	return doc.name


def acknowledge_advice(advice_name: str) -> None:
	"""Acknowledge a discharge advice (typically by nursing/front desk)."""
	doc = frappe.get_doc("IPD Discharge Advice", advice_name)
	doc.acknowledge()


def cancel_advice(advice_name: str, reason: str) -> None:
	"""Cancel a discharge advice with mandatory reason."""
	doc = frappe.get_doc("IPD Discharge Advice", advice_name)
	doc.cancel_advice(reason=reason)


def complete_advice(advice_name: str) -> None:
	"""Mark discharge advice as completed (final discharge)."""
	doc = frappe.get_doc("IPD Discharge Advice", advice_name)
	doc.complete()


def get_discharge_status(inpatient_record: str) -> dict:
	"""Return aggregate discharge readiness status for an admission.

	Checks discharge advice, billing checklist, and nursing checklist
	to provide a unified view.
	"""
	result = {
		"inpatient_record": inpatient_record,
		"advice": None,
		"billing_checklist": None,
		"nursing_checklist": None,
		"ready_to_vacate": False,
	}

	advice = frappe.db.get_value(
		"IPD Discharge Advice",
		{"inpatient_record": inpatient_record, "status": ("not in", ("Cancelled",))},
		["name", "status", "expected_discharge_datetime"],
		as_dict=True,
		order_by="creation desc",
	)
	if advice:
		result["advice"] = {
			"name": advice.name,
			"status": advice.status,
			"expected_discharge_datetime": str(advice.expected_discharge_datetime) if advice.expected_discharge_datetime else None,
		}

	billing = frappe.db.get_value(
		"Discharge Billing Checklist",
		{"inpatient_record": inpatient_record},
		["name", "status"],
		as_dict=True,
	)
	if billing:
		result["billing_checklist"] = {
			"name": billing.name,
			"status": billing.status,
		}

	nursing = frappe.db.get_value(
		"Nursing Discharge Checklist",
		{"inpatient_record": inpatient_record},
		["name", "status"],
		as_dict=True,
	)
	if nursing:
		result["nursing_checklist"] = {
			"name": nursing.name,
			"status": nursing.status,
		}

	advice_ok = advice and advice.status in ("Acknowledged", "Completed")
	billing_ok = billing and billing.status in ("Cleared", "Overridden")
	nursing_ok = nursing and nursing.status == "Completed"
	result["ready_to_vacate"] = bool(advice_ok and billing_ok and nursing_ok)

	return result
