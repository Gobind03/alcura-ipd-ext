"""Service for creating IPD admission orders from Patient Encounter.

Handles the practitioner-initiated admission workflow:
1. Validates the encounter is submitted and patient is valid
2. Creates an Inpatient Record with standard + custom fields
3. Links the IR back to the encounter
4. Records timeline comments on both documents
"""

from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import add_days, getdate, today


def create_admission_from_encounter(
	encounter: str,
	*,
	admission_priority: str = "Routine",
	requested_ward: str | None = None,
	expected_los_days: int | None = None,
	admission_notes: str | None = None,
) -> dict:
	"""Create an Inpatient Record from a submitted Patient Encounter.

	Args:
		encounter: Name of the Patient Encounter (must be submitted).
		admission_priority: Routine / Urgent / Emergency.
		requested_ward: Optional Hospital Ward name.
		expected_los_days: Expected length of stay in days.
		admission_notes: Free-text notes from the practitioner.

	Returns:
		Dict with ``inpatient_record``, ``patient``, and ``status`` keys.

	Raises:
		frappe.ValidationError: If encounter is invalid or admission
			has already been ordered from this encounter.
	"""
	enc_doc = frappe.get_doc("Patient Encounter", encounter)
	_validate_encounter(enc_doc)

	ir_doc = _create_inpatient_record(
		enc_doc,
		admission_priority=admission_priority,
		requested_ward=requested_ward,
		expected_los_days=expected_los_days,
		admission_notes=admission_notes,
	)

	_link_encounter_to_ir(enc_doc, ir_doc)
	_add_timeline_comments(enc_doc, ir_doc)

	return {
		"inpatient_record": ir_doc.name,
		"patient": ir_doc.patient,
		"status": ir_doc.status,
	}


# ── Validation ───────────────────────────────────────────────────────


def _validate_encounter(enc_doc) -> None:
	if enc_doc.docstatus != 1:
		frappe.throw(
			_("Patient Encounter {0} must be submitted before ordering admission.").format(
				frappe.bold(enc_doc.name)
			),
			exc=frappe.ValidationError,
		)

	if enc_doc.custom_ipd_admission_ordered:
		frappe.throw(
			_("An IPD admission has already been ordered from Encounter {0} "
			  "(Inpatient Record: {1}).").format(
				frappe.bold(enc_doc.name),
				frappe.bold(enc_doc.custom_ipd_inpatient_record or ""),
			),
			exc=frappe.ValidationError,
		)

	if not enc_doc.patient:
		frappe.throw(
			_("Patient Encounter {0} has no linked patient.").format(
				frappe.bold(enc_doc.name)
			),
			exc=frappe.ValidationError,
		)


# ── IR creation ──────────────────────────────────────────────────────


def _create_inpatient_record(
	enc_doc,
	*,
	admission_priority: str,
	requested_ward: str | None,
	expected_los_days: int | None,
	admission_notes: str | None,
) -> "frappe.Document":
	expected_discharge = None
	if expected_los_days and expected_los_days > 0:
		expected_discharge = add_days(getdate(today()), expected_los_days)

	ir_values = {
		"doctype": "Inpatient Record",
		"patient": enc_doc.patient,
		"company": enc_doc.company,
		"medical_department": enc_doc.medical_department,
		"primary_practitioner": enc_doc.practitioner,
		"admission_instruction": enc_doc.custom_ipd_admission_notes if hasattr(enc_doc, "custom_ipd_admission_notes") else None,
		"scheduled_date": today(),
		"status": "Admission Scheduled",
		# Custom fields
		"custom_requesting_encounter": enc_doc.name,
		"custom_admission_priority": admission_priority or "Routine",
		"custom_expected_los_days": expected_los_days or 0,
		"custom_requested_ward": requested_ward or None,
		"custom_admission_notes": admission_notes or None,
	}

	if expected_discharge:
		ir_values["expected_discharge"] = expected_discharge

	# Carry over standard encounter fields if available
	if enc_doc.get("admission_service_unit_type"):
		ir_values["admission_service_unit_type"] = enc_doc.admission_service_unit_type

	# Carry over payer profile from patient default if available
	patient_payer = frappe.db.get_value(
		"Patient", enc_doc.patient, "custom_default_payer_profile"
	)
	if patient_payer:
		ir_values["custom_patient_payer_profile"] = patient_payer

	ir_doc = frappe.get_doc(ir_values)
	ir_doc.insert(ignore_permissions=True)

	return ir_doc


# ── Back-link ────────────────────────────────────────────────────────


def _link_encounter_to_ir(enc_doc, ir_doc) -> None:
	"""Mark the encounter as having an admission ordered and link the IR."""
	enc_doc.db_set({
		"custom_ipd_admission_ordered": 1,
		"custom_ipd_inpatient_record": ir_doc.name,
	}, update_modified=False)


# ── Timeline ─────────────────────────────────────────────────────────


def _add_timeline_comments(enc_doc, ir_doc) -> None:
	priority_label = ir_doc.custom_admission_priority or "Routine"
	ward_label = ir_doc.custom_requested_ward or _("Not specified")

	msg = _(
		"IPD Admission ordered ({priority}) — Inpatient Record {ir}. "
		"Requested ward: {ward}."
	).format(
		priority=frappe.bold(priority_label),
		ir=frappe.bold(ir_doc.name),
		ward=frappe.bold(ward_label),
	)

	ir_doc.add_comment("Info", msg)

	try:
		enc_doc.add_comment("Info", msg)
	except Exception:
		pass

	try:
		patient_doc = frappe.get_doc("Patient", enc_doc.patient)
		patient_doc.add_comment("Info", msg)
	except Exception:
		pass
