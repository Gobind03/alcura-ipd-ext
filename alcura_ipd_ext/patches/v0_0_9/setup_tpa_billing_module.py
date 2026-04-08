"""Patch: Setup TPA billing module (US-I1 through US-I5).

Creates the IPD Billing User role and installs new custom fields for
TPA preauth, discharge checklist, and claim pack on Inpatient Record.
"""

from __future__ import annotations

import frappe


def execute():
	_setup_billing_role()
	_setup_custom_fields()


def _setup_billing_role():
	if not frappe.db.exists("Role", "IPD Billing User"):
		doc = frappe.new_doc("Role")
		doc.update({
			"role_name": "IPD Billing User",
			"desk_access": 1,
			"is_custom": 1,
			"search_bar": 1,
			"notifications": 1,
		})
		doc.insert(ignore_permissions=True)
		frappe.logger("alcura_ipd_ext").info("Created role: IPD Billing User")


def _setup_custom_fields():
	from alcura_ipd_ext.setup.custom_fields import setup_custom_fields

	setup_custom_fields()
