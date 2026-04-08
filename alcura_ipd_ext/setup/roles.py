"""Custom role definitions for alcura_ipd_ext.

Creates application-specific roles during install and removes them
during uninstall.
"""

from __future__ import annotations

import frappe

CUSTOM_ROLES = [
	{
		"role_name": "TPA Desk User",
		"desk_access": 1,
		"is_custom": 1,
		"search_bar": 1,
		"notifications": 1,
	},
	{
		"role_name": "IPD Admission Officer",
		"desk_access": 1,
		"is_custom": 1,
		"search_bar": 1,
		"notifications": 1,
	},
	{
		"role_name": "Pharmacy User",
		"desk_access": 1,
		"is_custom": 1,
		"search_bar": 1,
		"notifications": 1,
	},
	{
		"role_name": "ICU Administrator",
		"desk_access": 1,
		"is_custom": 1,
		"search_bar": 1,
		"notifications": 1,
	},
	{
		"role_name": "Device Integration User",
		"desk_access": 1,
		"is_custom": 1,
		"search_bar": 1,
		"notifications": 1,
	},
	{
		"role_name": "IPD Billing User",
		"desk_access": 1,
		"is_custom": 1,
		"search_bar": 1,
		"notifications": 1,
	},
]


def setup_roles():
	"""Create custom roles. Safe to call repeatedly."""
	for role_def in CUSTOM_ROLES:
		if not frappe.db.exists("Role", role_def["role_name"]):
			doc = frappe.new_doc("Role")
			doc.update(role_def)
			doc.insert(ignore_permissions=True)
			frappe.logger("alcura_ipd_ext").info(
				f"Created role: {role_def['role_name']}"
			)


def teardown_roles():
	"""Remove custom roles (used during uninstall)."""
	for role_def in CUSTOM_ROLES:
		if frappe.db.exists("Role", role_def["role_name"]):
			frappe.delete_doc("Role", role_def["role_name"], force=True)
			frappe.logger("alcura_ipd_ext").info(
				f"Removed role: {role_def['role_name']}"
			)
