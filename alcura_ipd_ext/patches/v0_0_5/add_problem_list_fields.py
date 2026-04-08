"""Patch: Add US-E5 custom fields for problem list and progress notes.

Adds new custom fields to Patient Encounter and Inpatient Record for
doctor progress notes and problem list tracking.
"""

import frappe


def execute():
	from alcura_ipd_ext.setup.custom_fields import setup_custom_fields

	setup_custom_fields()
	frappe.db.commit()
