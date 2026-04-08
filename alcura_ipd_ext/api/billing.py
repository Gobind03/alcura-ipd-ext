"""Whitelisted API endpoints for IPD billing operations.

Covers billing rule resolution, interim bill generation, and
bill split computation.
"""

from __future__ import annotations

import json

import frappe
from frappe import _


@frappe.whitelist()
def get_bill_split(
	line_items: str | list,
	patient_payer_profile: str,
	company: str | None = None,
	preauth_name: str | None = None,
) -> dict:
	"""Compute payer/patient/excluded split for a list of line items.

	Each line_item must have: item_code, item_group, charge_category, gross_amount.
	"""
	frappe.has_permission("Patient Payer Profile", "read", throw=True)

	if isinstance(line_items, str):
		line_items = json.loads(line_items)

	from alcura_ipd_ext.services.billing_rule_service import compute_bill_split

	return compute_bill_split(
		line_items=line_items,
		patient_payer_profile=patient_payer_profile,
		company=company,
		preauth_name=preauth_name,
	)


@frappe.whitelist()
def get_interim_bill(inpatient_record: str, as_of_date: str | None = None) -> dict:
	"""Generate an interim bill snapshot for an inpatient record."""
	frappe.has_permission("Inpatient Record", "read", throw=True)

	from alcura_ipd_ext.services.interim_bill_service import generate_interim_bill

	return generate_interim_bill(inpatient_record, as_of_date=as_of_date)
