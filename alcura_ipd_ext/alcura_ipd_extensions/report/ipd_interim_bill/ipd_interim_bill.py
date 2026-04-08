"""IPD Interim Bill — Script Report.

Generates a tabular interim bill for an active inpatient record,
showing charge breakdown with payer splits.
"""

from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import flt


def execute(filters: dict | None = None):
	filters = filters or {}
	if not filters.get("inpatient_record"):
		return _get_columns(), []

	from alcura_ipd_ext.services.interim_bill_service import generate_interim_bill

	bill = generate_interim_bill(
		inpatient_record=filters["inpatient_record"],
		as_of_date=filters.get("as_of_date"),
	)

	columns = _get_columns()
	data = _build_rows(bill)
	message = _build_message(bill)

	return columns, data, message


def _get_columns() -> list[dict]:
	return [
		{"fieldname": "charge_category", "label": _("Category"), "fieldtype": "Data", "width": 130},
		{"fieldname": "description", "label": _("Description"), "fieldtype": "Data", "width": 250},
		{"fieldname": "qty", "label": _("Qty"), "fieldtype": "Float", "width": 70},
		{"fieldname": "rate", "label": _("Rate"), "fieldtype": "Currency", "width": 110},
		{"fieldname": "gross_amount", "label": _("Gross Amount"), "fieldtype": "Currency", "width": 120},
		{"fieldname": "payer_amount", "label": _("Payer Amount"), "fieldtype": "Currency", "width": 120},
		{"fieldname": "patient_amount", "label": _("Patient Amount"), "fieldtype": "Currency", "width": 120},
		{"fieldname": "excluded_amount", "label": _("Excluded"), "fieldtype": "Currency", "width": 110},
		{"fieldname": "rule_applied", "label": _("Rule"), "fieldtype": "Data", "width": 150},
	]


def _build_rows(bill: dict) -> list[dict]:
	summary = bill.get("bill_summary", {})
	lines = summary.get("lines", [])
	rows = []

	for line in lines:
		rows.append({
			"charge_category": line.get("charge_category", ""),
			"description": line.get("description", ""),
			"qty": flt(line.get("qty", 0)),
			"rate": flt(line.get("rate", 0)),
			"gross_amount": flt(line.get("gross_amount", 0)),
			"payer_amount": flt(line.get("payer_amount", 0)),
			"patient_amount": flt(line.get("patient_amount", 0)),
			"excluded_amount": flt(line.get("excluded_amount", 0)),
			"rule_applied": line.get("rule_applied", ""),
		})

	return rows


def _build_message(bill: dict) -> str:
	summary = bill.get("bill_summary", {})
	deposits = bill.get("deposits", {})
	parts = [
		f"<b>{_('Gross Total')}:</b> {_fmt(summary.get('gross_total', 0))}",
		f"<b>{_('Payer Total')}:</b> {_fmt(summary.get('payer_total', 0))}",
		f"<b>{_('Patient Total')}:</b> {_fmt(summary.get('patient_total', 0))}",
	]
	if summary.get("deductible_applied"):
		parts.append(f"<b>{_('Deductible Applied')}:</b> {_fmt(summary['deductible_applied'])}")
	if summary.get("preauth_approved_amount"):
		parts.append(f"<b>{_('Preauth Approved')}:</b> {_fmt(summary['preauth_approved_amount'])}")
	if summary.get("preauth_overshoot"):
		parts.append(f"<b>{_('Preauth Overshoot')}:</b> {_fmt(summary['preauth_overshoot'])}")
	if deposits.get("total"):
		parts.append(f"<b>{_('Deposits')}:</b> {_fmt(deposits['total'])}")
	parts.append(f"<b>{_('Balance Due')}:</b> {_fmt(bill.get('balance_due', 0))}")
	parts.append(f"<i>{_('Generated at')}:</i> {bill.get('generated_at', '')}")

	return " | ".join(parts)


def _fmt(value) -> str:
	return frappe.format_value(flt(value), {"fieldtype": "Currency"})
