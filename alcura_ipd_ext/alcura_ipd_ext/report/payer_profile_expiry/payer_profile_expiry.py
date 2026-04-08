"""Payer Profile Expiry Report.

Shows active Patient Payer Profiles expiring within a configurable number
of days, grouped by payer type. Useful for TPA desk and operations teams
to proactively renew or update profiles before they lapse.
"""

from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import add_days, getdate, today


def execute(filters=None):
	filters = filters or {}
	columns = _get_columns()
	data = _get_data(filters)
	return columns, data


def _get_columns() -> list[dict]:
	return [
		{
			"fieldname": "name",
			"label": _("Profile ID"),
			"fieldtype": "Link",
			"options": "Patient Payer Profile",
			"width": 140,
		},
		{
			"fieldname": "patient",
			"label": _("Patient"),
			"fieldtype": "Link",
			"options": "Patient",
			"width": 130,
		},
		{
			"fieldname": "patient_name",
			"label": _("Patient Name"),
			"fieldtype": "Data",
			"width": 160,
		},
		{
			"fieldname": "payer_type",
			"label": _("Payer Type"),
			"fieldtype": "Data",
			"width": 130,
		},
		{
			"fieldname": "insurance_payor",
			"label": _("Insurance Payor"),
			"fieldtype": "Link",
			"options": "Insurance Payor",
			"width": 150,
		},
		{
			"fieldname": "payer",
			"label": _("Payer (Customer)"),
			"fieldtype": "Link",
			"options": "Customer",
			"width": 150,
		},
		{
			"fieldname": "policy_number",
			"label": _("Policy Number"),
			"fieldtype": "Data",
			"width": 130,
		},
		{
			"fieldname": "valid_from",
			"label": _("Valid From"),
			"fieldtype": "Date",
			"width": 110,
		},
		{
			"fieldname": "valid_to",
			"label": _("Valid To"),
			"fieldtype": "Date",
			"width": 110,
		},
		{
			"fieldname": "days_until_expiry",
			"label": _("Days Until Expiry"),
			"fieldtype": "Int",
			"width": 120,
		},
		{
			"fieldname": "sum_insured",
			"label": _("Sum Insured"),
			"fieldtype": "Currency",
			"width": 120,
		},
	]


def _get_data(filters: dict) -> list[dict]:
	expiry_within_days = filters.get("expiry_within_days", 30)
	cutoff_date = add_days(today(), int(expiry_within_days))

	db_filters = {
		"is_active": 1,
		"valid_to": ["<=", cutoff_date],
		"valid_to": ["is", "set"],
	}

	if filters.get("payer_type"):
		db_filters["payer_type"] = filters["payer_type"]
	if filters.get("insurance_payor"):
		db_filters["insurance_payor"] = filters["insurance_payor"]
	if filters.get("company"):
		db_filters["company"] = filters["company"]

	profiles = frappe.db.get_all(
		"Patient Payer Profile",
		filters=db_filters,
		fields=[
			"name",
			"patient",
			"patient_name",
			"payer_type",
			"insurance_payor",
			"payer",
			"policy_number",
			"valid_from",
			"valid_to",
			"sum_insured",
		],
		order_by="valid_to asc",
	)

	today_date = getdate(today())
	for row in profiles:
		row["days_until_expiry"] = (getdate(row["valid_to"]) - today_date).days

	return profiles
