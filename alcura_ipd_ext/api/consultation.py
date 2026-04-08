"""Whitelisted API endpoints for IPD consultant clinical documentation.

US-E3: Provides endpoints for creating IPD consultation encounters and
retrieving clinical context data for display on encounter forms.

Usage from client:
	frappe.call("alcura_ipd_ext.api.consultation.create_admission_note", {
		inpatient_record: "IP-00001",
		note_type: "Admission Note",
		practitioner: "HP-00001"
	})
	frappe.call("alcura_ipd_ext.api.consultation.get_clinical_context", {
		inpatient_record: "IP-00001"
	})
"""

from __future__ import annotations

import frappe


@frappe.whitelist()
def create_admission_note(
	inpatient_record: str,
	note_type: str = "Admission Note",
	practitioner: str | None = None,
) -> dict:
	"""Create a draft Patient Encounter linked to the Inpatient Record.

	Returns dict with ``encounter``, ``patient``, and ``note_type`` keys.
	"""
	frappe.has_permission("Inpatient Record", "read", throw=True)
	frappe.has_permission("Patient Encounter", "create", throw=True)

	from alcura_ipd_ext.services.consultation_note_service import (
		create_consultation_encounter,
	)

	return create_consultation_encounter(
		inpatient_record=inpatient_record,
		note_type=note_type,
		practitioner=practitioner or None,
	)


@frappe.whitelist()
def get_clinical_context(inpatient_record: str) -> dict:
	"""Return clinical context for display on IPD encounter forms.

	Returns dict with allergy flags, risk indicators, bed location,
	recent encounters, and intake history data.
	"""
	frappe.has_permission("Inpatient Record", "read", throw=True)

	from alcura_ipd_ext.services.consultation_note_service import (
		get_ipd_clinical_context,
	)

	return get_ipd_clinical_context(inpatient_record)
