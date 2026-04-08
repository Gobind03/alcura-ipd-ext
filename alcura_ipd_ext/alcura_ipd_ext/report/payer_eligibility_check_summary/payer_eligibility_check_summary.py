"""Payer Eligibility Check Summary — Script Report.

Shows eligibility verification records with filters for status,
payer type, company, and date range.
"""

from __future__ import annotations

import frappe
from frappe import _


def execute(filters=None):
	filters = filters or {}
	columns = _get_columns()
	data = _get_data(filters)
	return columns, data


def _get_columns() -> list[dict]:
	return [
		{
			"fieldname": "name",
			"label": _("Check ID"),
			"fieldtype": "Link",
			"options": "Payer Eligibility Check",
			"width": 160,
		},
		{
			"fieldname": "patient",
			"label": _("Patient"),
			"fieldtype": "Link",
			"options": "Patient",
			"width": 140,
		},
		{
			"fieldname": "patient_name",
			"label": _("Patient Name"),
			"fieldtype": "Data",
			"width": 160,
		},
		{
			"fieldname": "patient_payer_profile",
			"label": _("Payer Profile"),
			"fieldtype": "Link",
			"options": "Patient Payer Profile",
			"width": 160,
		},
		{
			"fieldname": "payer_type",
			"label": _("Payer Type"),
			"fieldtype": "Data",
			"width": 120,
		},
		{
			"fieldname": "verification_status",
			"label": _("Status"),
			"fieldtype": "Data",
			"width": 100,
		},
		{
			"fieldname": "approved_amount",
			"label": _("Approved Amount"),
			"fieldtype": "Currency",
			"width": 130,
		},
		{
			"fieldname": "reference_number",
			"label": _("Pre-Auth Ref"),
			"fieldtype": "Data",
			"width": 130,
		},
		{
			"fieldname": "verified_by",
			"label": _("Verified By"),
			"fieldtype": "Link",
			"options": "User",
			"width": 140,
		},
		{
			"fieldname": "verification_datetime",
			"label": _("Verified On"),
			"fieldtype": "Datetime",
			"width": 160,
		},
		{
			"fieldname": "valid_to",
			"label": _("Valid To"),
			"fieldtype": "Date",
			"width": 110,
		},
		{
			"fieldname": "inpatient_record",
			"label": _("Inpatient Record"),
			"fieldtype": "Link",
			"options": "Inpatient Record",
			"width": 140,
		},
		{
			"fieldname": "company",
			"label": _("Company"),
			"fieldtype": "Link",
			"options": "Company",
			"width": 140,
		},
	]


def _get_data(filters: dict) -> list[dict]:
	conditions = []
	params: dict = {}

	if filters.get("verification_status"):
		conditions.append("pec.verification_status = %(verification_status)s")
		params["verification_status"] = filters["verification_status"]

	if filters.get("payer_type"):
		conditions.append("pec.payer_type = %(payer_type)s")
		params["payer_type"] = filters["payer_type"]

	if filters.get("company"):
		conditions.append("pec.company = %(company)s")
		params["company"] = filters["company"]

	if filters.get("from_date"):
		conditions.append("pec.creation >= %(from_date)s")
		params["from_date"] = filters["from_date"]

	if filters.get("to_date"):
		conditions.append("pec.creation <= %(to_date)s")
		params["to_date"] = filters["to_date"]

	where = " AND ".join(conditions) if conditions else "1=1"

	return frappe.db.sql(
		f"""
		SELECT
			pec.name,
			pec.patient,
			pec.patient_name,
			pec.patient_payer_profile,
			pec.payer_type,
			pec.verification_status,
			pec.approved_amount,
			pec.reference_number,
			pec.verified_by,
			pec.verification_datetime,
			pec.valid_to,
			pec.inpatient_record,
			pec.company
		FROM `tabPayer Eligibility Check` pec
		WHERE {where}
		ORDER BY pec.modified DESC
		""",
		params,
		as_dict=True,
	)
