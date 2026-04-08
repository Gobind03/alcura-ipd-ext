"""Whitelisted API endpoints for Patient registration workflows."""

from __future__ import annotations

import frappe


@frappe.whitelist()
def check_patient_duplicates(
	mobile: str | None = None,
	aadhaar: str | None = None,
	abha: str | None = None,
	mr_number: str | None = None,
	first_name: str | None = None,
	dob: str | None = None,
	exclude_patient: str | None = None,
) -> list[dict]:
	"""Check for duplicate patients before saving.

	Called from the Patient form client script to show a warning dialog
	when potential duplicates are found.

	Returns a list of dicts, each with: patient, patient_name, mobile,
	dob, and match_reasons.
	"""
	from alcura_ipd_ext.services.patient_duplicate_service import check_duplicates

	return check_duplicates(
		mobile=mobile,
		aadhaar=aadhaar,
		abha=abha,
		mr_number=mr_number,
		first_name=first_name,
		dob=dob,
		exclude_patient=exclude_patient,
	)
