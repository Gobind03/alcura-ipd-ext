"""Whitelisted API endpoints for IPD Intake Assessment workflows.

Usage from client:
	frappe.call("alcura_ipd_ext.api.intake.create_intake_assessment", {
		inpatient_record: "IP-00001"
	})
	frappe.call("alcura_ipd_ext.api.intake.save_responses", {
		assessment: "IPD-IA-2026-00001",
		responses: [{idx: 1, text_value: "Chest pain"}]
	})
	frappe.call("alcura_ipd_ext.api.intake.complete_assessment", {
		assessment: "IPD-IA-2026-00001"
	})
	frappe.call("alcura_ipd_ext.api.intake.get_assessments_for_ir", {
		inpatient_record: "IP-00001"
	})
"""

from __future__ import annotations

import json

import frappe

from alcura_ipd_ext.services.intake_assessment_service import (
	complete_intake_assessment,
	create_intake_assessment as _create,
	get_intake_assessments_for_ir,
	get_pending_scored_assessments,
	save_responses as _save,
)


@frappe.whitelist()
def create_intake_assessment(
	inpatient_record: str,
	template_name: str | None = None,
) -> dict:
	"""Create an IPD Intake Assessment for an Inpatient Record."""
	frappe.has_permission("IPD Intake Assessment", "create", throw=True)

	return _create(
		inpatient_record=inpatient_record,
		template_name=template_name,
	)


@frappe.whitelist()
def save_responses(assessment: str, responses: str | list) -> dict:
	"""Bulk-save response values for an intake assessment.

	Args:
		assessment: Name of the IPD Intake Assessment.
		responses: JSON string or list of dicts with ``idx`` and value fields.
	"""
	frappe.has_permission("IPD Intake Assessment", "write", throw=True)

	if isinstance(responses, str):
		responses = json.loads(responses)

	return _save(assessment_name=assessment, responses=responses)


@frappe.whitelist()
def complete_assessment(assessment: str) -> dict:
	"""Validate mandatory fields and mark assessment as Completed."""
	frappe.has_permission("IPD Intake Assessment", "write", throw=True)

	return complete_intake_assessment(assessment_name=assessment)


@frappe.whitelist()
def get_assessments_for_ir(inpatient_record: str) -> list[dict]:
	"""Return all intake assessments for an Inpatient Record."""
	frappe.has_permission("IPD Intake Assessment", "read", throw=True)

	return get_intake_assessments_for_ir(inpatient_record)


@frappe.whitelist()
def get_pending_scored(assessment: str) -> list[dict]:
	"""Return scored Patient Assessments still in Draft for this intake."""
	frappe.has_permission("Patient Assessment", "read", throw=True)

	return get_pending_scored_assessments(assessment_name=assessment)
