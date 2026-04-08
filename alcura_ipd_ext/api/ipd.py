"""
Whitelisted API methods for IPD workflows.

Usage from client:
    frappe.call("alcura_ipd_ext.api.ipd.get_active_ipd_records", patient="PAT-001")
"""

import frappe


@frappe.whitelist()
def get_active_ipd_records(patient: str | None = None) -> list[dict]:
	"""Return active Inpatient records, optionally filtered by patient."""
	filters = {"status": "Admitted"}
	if patient:
		filters["patient"] = patient

	return frappe.get_all(
		"Inpatient Record",
		filters=filters,
		fields=["name", "patient", "patient_name", "admitted_datetime", "expected_discharge"],
		order_by="admitted_datetime desc",
	)
