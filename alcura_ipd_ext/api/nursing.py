"""Whitelisted API endpoints for nursing risk assessment workflows.

Usage from client:
	frappe.call("alcura_ipd_ext.api.nursing.get_risk_summary", {
		inpatient_record: "IP-00001"
	})
	frappe.call("alcura_ipd_ext.api.nursing.get_ward_risk_overview", {
		ward: "WARD-001"
	})
	frappe.call("alcura_ipd_ext.api.nursing.recalculate_risks", {
		inpatient_record: "IP-00001"
	})
"""

from __future__ import annotations

import frappe

from alcura_ipd_ext.services.nursing_risk_service import (
	get_risk_summary as _get_risk_summary,
	get_ward_risk_overview as _get_ward_overview,
	update_risk_flags,
)


@frappe.whitelist()
def get_risk_summary(inpatient_record: str) -> dict:
	"""Return current nursing risk flags for an Inpatient Record."""
	frappe.has_permission("Inpatient Record", "read", doc=inpatient_record, throw=True)
	return _get_risk_summary(inpatient_record)


@frappe.whitelist()
def get_ward_risk_overview(
	ward: str | None = None,
	company: str | None = None,
) -> list[dict]:
	"""Return risk overview for all admitted patients in a ward."""
	frappe.has_permission("Inpatient Record", "read", throw=True)
	return _get_ward_overview(ward=ward, company=company)


@frappe.whitelist()
def recalculate_risks(inpatient_record: str) -> dict:
	"""Manually trigger risk flag recalculation for an Inpatient Record."""
	frappe.has_permission("Inpatient Record", "write", doc=inpatient_record, throw=True)
	return update_risk_flags(inpatient_record)
