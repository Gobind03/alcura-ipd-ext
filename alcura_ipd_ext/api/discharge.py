"""Whitelisted API endpoints for IPD discharge journey.

Covers discharge advice lifecycle, aggregate status, bed vacate,
and housekeeping operations.
"""

from __future__ import annotations

import frappe
from frappe import _


@frappe.whitelist()
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
) -> dict:
	"""Create and submit a discharge advice."""
	from alcura_ipd_ext.services.discharge_advice_service import (
		create_discharge_advice as _create,
	)

	name = _create(
		inpatient_record=inpatient_record,
		consultant=consultant,
		expected_discharge_datetime=expected_discharge_datetime,
		discharge_type=discharge_type,
		condition_at_discharge=condition_at_discharge,
		primary_diagnosis=primary_diagnosis,
		secondary_diagnoses=secondary_diagnoses,
		discharge_medications=discharge_medications,
		follow_up_instructions=follow_up_instructions,
		follow_up_date=follow_up_date,
		follow_up_practitioner=follow_up_practitioner,
		diet_instructions=diet_instructions,
		activity_restrictions=activity_restrictions,
		warning_signs=warning_signs,
		additional_instructions=additional_instructions,
	)
	return {"advice": name}


@frappe.whitelist()
def acknowledge_discharge_advice(advice_name: str) -> dict:
	"""Acknowledge a discharge advice."""
	from alcura_ipd_ext.services.discharge_advice_service import acknowledge_advice

	acknowledge_advice(advice_name)
	return {"status": "Acknowledged"}


@frappe.whitelist()
def cancel_discharge_advice(advice_name: str, reason: str = "") -> dict:
	"""Cancel a discharge advice."""
	from alcura_ipd_ext.services.discharge_advice_service import cancel_advice

	cancel_advice(advice_name, reason)
	return {"status": "Cancelled"}


@frappe.whitelist()
def get_discharge_status(inpatient_record: str) -> dict:
	"""Get aggregate discharge readiness status."""
	from alcura_ipd_ext.services.discharge_advice_service import (
		get_discharge_status as _get_status,
	)

	return _get_status(inpatient_record)


@frappe.whitelist()
def vacate_bed(inpatient_record: str) -> dict:
	"""Process bed vacate for a discharged patient."""
	from alcura_ipd_ext.services.discharge_service import process_bed_vacate

	return process_bed_vacate(inpatient_record)


@frappe.whitelist()
def start_cleaning(task_name: str) -> dict:
	"""Start housekeeping cleaning for a bed."""
	from alcura_ipd_ext.services.housekeeping_service import start_cleaning

	start_cleaning(task_name)
	return {"status": "In Progress"}


@frappe.whitelist()
def complete_cleaning(task_name: str) -> dict:
	"""Complete housekeeping cleaning for a bed."""
	from alcura_ipd_ext.services.housekeeping_service import complete_cleaning

	result = complete_cleaning(task_name)
	return result


@frappe.whitelist()
def create_nursing_checklist(inpatient_record: str, discharge_advice: str = "") -> dict:
	"""Create a nursing discharge checklist."""
	from alcura_ipd_ext.services.nursing_discharge_service import create_nursing_checklist

	name = create_nursing_checklist(
		inpatient_record=inpatient_record,
		discharge_advice=discharge_advice or None,
	)
	return {"checklist": name}
