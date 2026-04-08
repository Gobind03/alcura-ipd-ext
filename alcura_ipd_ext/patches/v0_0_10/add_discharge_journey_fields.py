"""Add discharge journey custom fields and IPD Bed Policy extensions.

Applies for US-J1 (Discharge Advice), US-J2 (Nursing Discharge Checklist),
and US-J3 (Housekeeping SLA multipliers).
"""

from __future__ import annotations

import frappe


def execute():
	_add_custom_fields()
	_add_bed_policy_defaults()


def _add_custom_fields():
	"""Create custom fields on Inpatient Record for discharge journey."""
	from alcura_ipd_ext.setup.custom_fields import get_custom_fields
	from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

	all_fields = get_custom_fields()
	ir_fields = all_fields.get("Inpatient Record", [])

	discharge_fieldnames = {
		"custom_discharge_journey_section",
		"custom_discharge_advice",
		"custom_discharge_advice_status",
		"custom_expected_discharge_datetime",
		"custom_column_break_discharge_1",
		"custom_nursing_discharge_checklist",
		"custom_nursing_discharge_status",
	}

	discharge_fields = [f for f in ir_fields if f["fieldname"] in discharge_fieldnames]
	if discharge_fields:
		create_custom_fields({"Inpatient Record": discharge_fields}, update=True)
		frappe.db.commit()


def _add_bed_policy_defaults():
	"""Set defaults for new SLA multiplier fields on IPD Bed Policy."""
	if not frappe.db.exists("DocType", "IPD Bed Policy"):
		return

	policy_name = "IPD Bed Policy"
	if not frappe.db.exists(policy_name, policy_name):
		return

	updates = {}
	current = frappe.db.get_value(
		policy_name, policy_name,
		["deep_clean_sla_multiplier", "isolation_clean_sla_multiplier"],
		as_dict=True,
	)

	if current and not current.get("deep_clean_sla_multiplier"):
		updates["deep_clean_sla_multiplier"] = 2.0

	if current and not current.get("isolation_clean_sla_multiplier"):
		updates["isolation_clean_sla_multiplier"] = 3.0

	if updates:
		frappe.db.set_value(policy_name, policy_name, updates, update_modified=False)
		frappe.db.commit()
