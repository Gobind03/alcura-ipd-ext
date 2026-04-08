"""Payer eligibility verification service.

Provides domain logic for querying the latest active eligibility check
and determining whether a patient's admission satisfies payer eligibility
requirements according to the current IPD Bed Policy.
"""

from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import getdate, today

from alcura_ipd_ext.alcura_ipd_ext.doctype.ipd_bed_policy.ipd_bed_policy import (
	get_policy,
)
from alcura_ipd_ext.utils.constants import PAYER_TYPES_NON_CASH


def get_latest_active_eligibility(
	patient: str,
	patient_payer_profile: str | None = None,
	company: str | None = None,
) -> dict | None:
	"""Return the latest Verified or Conditional eligibility check.

	Args:
		patient: Patient name (required).
		patient_payer_profile: Filter by specific payer profile.
		company: Filter by company.

	Returns:
		Dict with eligibility check fields, or None if no active check found.
	"""
	filters: dict = {
		"patient": patient,
		"verification_status": ("in", ("Verified", "Conditional")),
	}

	if patient_payer_profile:
		filters["patient_payer_profile"] = patient_payer_profile

	if company:
		filters["company"] = company

	checks = frappe.db.get_all(
		"Payer Eligibility Check",
		filters=filters,
		fields=[
			"name",
			"verification_status",
			"patient_payer_profile",
			"payer_type",
			"approved_amount",
			"approved_room_category",
			"approved_duration_days",
			"reference_number",
			"valid_from",
			"valid_to",
			"exclusions",
			"conditions",
			"verified_by",
			"verification_datetime",
		],
		order_by="verification_datetime desc, modified desc",
		limit=1,
	)

	if not checks:
		return None

	check = checks[0]

	if check.valid_to and getdate(check.valid_to) < getdate(today()):
		return None

	return check


def check_admission_eligibility(inpatient_record: str) -> dict:
	"""Determine if an admission satisfies payer eligibility requirements.

	Args:
		inpatient_record: Name of the Inpatient Record.

	Returns:
		Dict with keys:
			- eligible (bool): Whether admission can proceed
			- enforcement (str): Policy level — Strict, Advisory, or Ignore
			- status (str): Eligibility status description
			- message (str): Human-readable message
			- eligibility_check (str|None): Name of the eligibility check, if found
	"""
	policy = get_policy()
	enforcement = policy.get("enforce_eligibility_verification", "Advisory")

	result_base = {
		"enforcement": enforcement,
		"eligibility_check": None,
	}

	if enforcement == "Ignore":
		return {
			**result_base,
			"eligible": True,
			"status": "Skipped",
			"message": _("Eligibility verification is not enforced."),
		}

	payer_profile_name = frappe.db.get_value(
		"Inpatient Record", inpatient_record, "custom_patient_payer_profile"
	)

	if not payer_profile_name:
		return {
			**result_base,
			"eligible": True,
			"status": "No Profile",
			"message": _("No payer profile linked. Treating as Cash admission."),
		}

	payer_type = frappe.db.get_value(
		"Patient Payer Profile", payer_profile_name, "payer_type"
	)

	if payer_type and payer_type not in PAYER_TYPES_NON_CASH:
		return {
			**result_base,
			"eligible": True,
			"status": "Cash",
			"message": _("Cash payer — eligibility verification not required."),
		}

	patient = frappe.db.get_value("Inpatient Record", inpatient_record, "patient")
	company = frappe.db.get_value("Inpatient Record", inpatient_record, "company")

	check = get_latest_active_eligibility(
		patient=patient,
		patient_payer_profile=payer_profile_name,
		company=company,
	)

	if check:
		status_label = check.verification_status
		msg = _("Eligibility {0} — Pre-Auth: {1}, Approved: {2}").format(
			status_label,
			check.reference_number or _("N/A"),
			frappe.format_value(check.approved_amount, {"fieldtype": "Currency"})
			if check.approved_amount
			else _("N/A"),
		)
		return {
			**result_base,
			"eligible": True,
			"status": status_label,
			"message": msg,
			"eligibility_check": check.name,
		}

	# No valid eligibility check found
	eligible = enforcement != "Strict"
	msg = _(
		"No verified eligibility check found for payer profile {0} ({1})."
	).format(payer_profile_name, payer_type)

	if not eligible:
		msg += " " + _("Admission is blocked by Strict eligibility enforcement policy.")

	return {
		**result_base,
		"eligible": eligible,
		"status": "Not Verified",
		"message": msg,
	}
