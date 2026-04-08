"""Whitelisted API endpoints for doctor round sheets (US-E5).

Usage from client:
	frappe.call("alcura_ipd_ext.api.round_sheet.get_census", {
		practitioner: "HP-00001", company: "My Hospital"
	})
	frappe.call("alcura_ipd_ext.api.round_sheet.get_round_summary", {
		inpatient_record: "IP-00001"
	})
	frappe.call("alcura_ipd_ext.api.round_sheet.add_problem", {
		inpatient_record: "IP-00001",
		problem_description: "Uncontrolled DM Type 2"
	})
"""

from __future__ import annotations

import frappe


@frappe.whitelist()
def get_census(
	practitioner: str,
	company: str | None = None,
	ward: str | None = None,
) -> list[dict]:
	"""Return admitted patient census for a practitioner."""
	frappe.has_permission("Inpatient Record", "read", throw=True)

	from alcura_ipd_ext.services.round_sheet_service import get_doctor_census

	return get_doctor_census(
		practitioner=practitioner,
		company=company or None,
		ward=ward or None,
	)


@frappe.whitelist()
def get_round_summary(inpatient_record: str) -> dict:
	"""Return comprehensive patient round summary."""
	frappe.has_permission("Inpatient Record", "read", throw=True)

	from alcura_ipd_ext.services.round_sheet_service import get_patient_round_summary

	return get_patient_round_summary(inpatient_record)


@frappe.whitelist()
def get_problems(inpatient_record: str) -> list[dict]:
	"""Return active problems for an admission."""
	frappe.has_permission("Inpatient Record", "read", throw=True)

	from alcura_ipd_ext.services.round_sheet_service import get_active_problems

	return get_active_problems(inpatient_record)


@frappe.whitelist()
def add_problem(
	inpatient_record: str,
	problem_description: str,
	onset_date: str | None = None,
	severity: str | None = None,
	icd_code: str | None = None,
	practitioner: str | None = None,
) -> dict:
	"""Add a new problem to the patient's problem list."""
	frappe.has_permission("IPD Problem List Item", "create", throw=True)

	from alcura_ipd_ext.services.round_sheet_service import (
		add_problem as _add_problem,
	)

	return _add_problem(
		inpatient_record=inpatient_record,
		problem_description=problem_description,
		onset_date=onset_date or None,
		severity=severity or None,
		icd_code=icd_code or None,
		practitioner=practitioner or None,
	)


@frappe.whitelist()
def resolve_problem(
	problem_name: str,
	resolution_notes: str = "",
	practitioner: str | None = None,
) -> dict:
	"""Mark a problem as resolved."""
	frappe.has_permission("IPD Problem List Item", "write", throw=True)

	from alcura_ipd_ext.services.round_sheet_service import (
		resolve_problem as _resolve,
	)

	return _resolve(
		problem_name=problem_name,
		resolution_notes=resolution_notes,
		practitioner=practitioner or None,
	)


@frappe.whitelist()
def create_round_note(
	inpatient_record: str,
	practitioner: str | None = None,
) -> dict:
	"""Create a Progress Note encounter pre-populated with round context."""
	frappe.has_permission("Inpatient Record", "read", throw=True)
	frappe.has_permission("Patient Encounter", "create", throw=True)

	from alcura_ipd_ext.services.round_sheet_service import (
		create_progress_note_encounter,
	)

	return create_progress_note_encounter(
		inpatient_record=inpatient_record,
		practitioner=practitioner or None,
	)
