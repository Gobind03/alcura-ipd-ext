"""TPA Preauth Status — Script Report.

Provides a filterable overview of all TPA pre-authorization requests
with status, amounts, and turnaround metrics.
"""

from __future__ import annotations

import frappe
from frappe import _


def execute(filters: dict | None = None):
	filters = filters or {}
	columns = _get_columns()
	data = _get_data(filters)
	return columns, data


def _get_columns() -> list[dict]:
	return [
		{"fieldname": "name", "label": _("ID"), "fieldtype": "Link", "options": "TPA Preauth Request", "width": 150},
		{"fieldname": "patient_name", "label": _("Patient"), "fieldtype": "Data", "width": 160},
		{"fieldname": "inpatient_record", "label": _("IP Record"), "fieldtype": "Link", "options": "Inpatient Record", "width": 130},
		{"fieldname": "payer_type", "label": _("Payer Type"), "fieldtype": "Data", "width": 120},
		{"fieldname": "insurance_payor", "label": _("Insurance Payor"), "fieldtype": "Link", "options": "Insurance Payor", "width": 140},
		{"fieldname": "status", "label": _("Status"), "fieldtype": "Data", "width": 130},
		{"fieldname": "requested_amount", "label": _("Requested"), "fieldtype": "Currency", "width": 120},
		{"fieldname": "approved_amount", "label": _("Approved"), "fieldtype": "Currency", "width": 120},
		{"fieldname": "preauth_reference_number", "label": _("Ref No."), "fieldtype": "Data", "width": 120},
		{"fieldname": "treating_practitioner_name", "label": _("Practitioner"), "fieldtype": "Data", "width": 150},
		{"fieldname": "primary_diagnosis", "label": _("Diagnosis"), "fieldtype": "Data", "width": 200},
		{"fieldname": "submitted_on", "label": _("Submitted On"), "fieldtype": "Datetime", "width": 160},
		{"fieldname": "approved_on", "label": _("Approved On"), "fieldtype": "Datetime", "width": 160},
		{"fieldname": "valid_from", "label": _("Valid From"), "fieldtype": "Date", "width": 110},
		{"fieldname": "valid_to", "label": _("Valid To"), "fieldtype": "Date", "width": 110},
	]


def _get_data(filters: dict) -> list[dict]:
	conditions: dict = {}

	if filters.get("status"):
		conditions["status"] = filters["status"]
	if filters.get("payer_type"):
		conditions["payer_type"] = filters["payer_type"]
	if filters.get("insurance_payor"):
		conditions["insurance_payor"] = filters["insurance_payor"]
	if filters.get("company"):
		conditions["company"] = filters["company"]
	if filters.get("treating_practitioner"):
		conditions["treating_practitioner"] = filters["treating_practitioner"]
	if filters.get("from_date"):
		conditions["creation"] = (">=", filters["from_date"])
	if filters.get("to_date"):
		conditions["creation"] = ("<=", filters["to_date"])

	return frappe.db.get_all(
		"TPA Preauth Request",
		filters=conditions,
		fields=[
			"name", "patient_name", "inpatient_record", "payer_type",
			"insurance_payor", "status", "requested_amount", "approved_amount",
			"preauth_reference_number", "treating_practitioner_name",
			"primary_diagnosis", "submitted_on", "approved_on",
			"valid_from", "valid_to",
		],
		order_by="creation desc",
		limit=500,
	)
