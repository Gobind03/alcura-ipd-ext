"""Whitelisted API endpoints for payer eligibility verification.

Usage from client:
	frappe.call("alcura_ipd_ext.api.eligibility.check_for_admission", {
		inpatient_record: "IP-00001"
	})
	frappe.call("alcura_ipd_ext.api.eligibility.get_latest_for_patient", {
		patient: "PAT-00001", patient_payer_profile: "PPP-2026-00001"
	})
"""

from __future__ import annotations

import frappe

from alcura_ipd_ext.services.eligibility_service import (
	check_admission_eligibility,
	get_latest_active_eligibility,
)


@frappe.whitelist()
def check_for_admission(inpatient_record: str) -> dict:
	"""Pre-flight eligibility check for an admission.

	Returns a dict describing whether admission can proceed under
	the current IPD Bed Policy enforcement level.
	"""
	frappe.has_permission("Inpatient Record", "read", throw=True)
	return check_admission_eligibility(inpatient_record)


@frappe.whitelist()
def get_latest_for_patient(
	patient: str,
	patient_payer_profile: str | None = None,
	company: str | None = None,
) -> dict | None:
	"""Return the latest active eligibility check for a patient.

	Used by the front desk to display eligibility status on forms.
	"""
	frappe.has_permission("Payer Eligibility Check", "read", throw=True)
	return get_latest_active_eligibility(
		patient=patient,
		patient_payer_profile=patient_payer_profile or None,
		company=company or None,
	)
