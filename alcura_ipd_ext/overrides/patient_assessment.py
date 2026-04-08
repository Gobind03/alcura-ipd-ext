"""Event hooks for the standard Patient Assessment doctype.

Syncs IPD context fields from the linked assessment template when the
assessment is validated, and triggers nursing risk flag recalculation
on submit.
"""

from __future__ import annotations

import frappe


def validate(doc, method=None):
	"""Populate custom assessment context from template custom fields."""
	if not doc.assessment_template:
		return

	if doc.get("custom_assessment_context"):
		return

	context = frappe.db.get_value(
		"Patient Assessment Template",
		doc.assessment_template,
		"custom_assessment_context",
	)
	if context:
		doc.custom_assessment_context = context


def on_submit(doc, method=None):
	"""Recalculate nursing risk flags when a scored assessment is submitted."""
	if not doc.get("custom_inpatient_record"):
		return

	from alcura_ipd_ext.services.nursing_risk_service import update_risk_flags

	update_risk_flags(doc.custom_inpatient_record)
