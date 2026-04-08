"""TPA Claim Pack Status — Script Report.

Provides a filterable overview of all TPA claim packs with
submission and settlement tracking.
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
		{"fieldname": "name", "label": _("ID"), "fieldtype": "Link", "options": "TPA Claim Pack", "width": 150},
		{"fieldname": "patient_name", "label": _("Patient"), "fieldtype": "Data", "width": 160},
		{"fieldname": "inpatient_record", "label": _("IP Record"), "fieldtype": "Link", "options": "Inpatient Record", "width": 130},
		{"fieldname": "insurance_payor", "label": _("Insurance Payor"), "fieldtype": "Link", "options": "Insurance Payor", "width": 140},
		{"fieldname": "status", "label": _("Status"), "fieldtype": "Data", "width": 120},
		{"fieldname": "submission_date", "label": _("Submitted"), "fieldtype": "Date", "width": 110},
		{"fieldname": "submission_reference", "label": _("Ref No."), "fieldtype": "Data", "width": 120},
		{"fieldname": "settlement_amount", "label": _("Settled"), "fieldtype": "Currency", "width": 120},
		{"fieldname": "settlement_date", "label": _("Settled On"), "fieldtype": "Date", "width": 110},
		{"fieldname": "disallowance_amount", "label": _("Disallowed"), "fieldtype": "Currency", "width": 120},
		{"fieldname": "prepared_by", "label": _("Prepared By"), "fieldtype": "Link", "options": "User", "width": 140},
	]


def _get_data(filters: dict) -> list[dict]:
	conditions: dict = {}

	if filters.get("status"):
		conditions["status"] = filters["status"]
	if filters.get("insurance_payor"):
		conditions["insurance_payor"] = filters["insurance_payor"]
	if filters.get("company"):
		conditions["company"] = filters["company"]
	if filters.get("from_date"):
		conditions["submission_date"] = (">=", filters["from_date"])
	if filters.get("to_date"):
		conditions["submission_date"] = ("<=", filters["to_date"])

	return frappe.db.get_all(
		"TPA Claim Pack",
		filters=conditions,
		fields=[
			"name", "patient_name", "inpatient_record", "insurance_payor",
			"status", "submission_date", "submission_reference",
			"settlement_amount", "settlement_date", "disallowance_amount",
			"prepared_by",
		],
		order_by="creation desc",
		limit=500,
	)
