"""Seed default SLA configurations for IPD Clinical Orders.

Creates sensible SLA targets for each order type / urgency combination.
Safe to re-run — skips existing configs.
"""

from __future__ import annotations

import frappe

# (order_type, urgency, [(milestone, sequence, target_minutes, escalation_role)])
_SLA_SEED_DATA = [
	("Medication", "STAT", [
		("Acknowledged", 1, 10, "Pharmacy User"),
		("Dispensed", 2, 30, "Healthcare Administrator"),
	]),
	("Medication", "Emergency", [
		("Acknowledged", 1, 5, "Pharmacy User"),
		("Dispensed", 2, 15, "Healthcare Administrator"),
	]),
	("Medication", "Urgent", [
		("Acknowledged", 1, 15, "Pharmacy User"),
		("Dispensed", 2, 60, "Healthcare Administrator"),
	]),
	("Medication", "Routine", [
		("Acknowledged", 1, 30, "Pharmacy User"),
		("Dispensed", 2, 120, "Healthcare Administrator"),
	]),
	("Lab Test", "STAT", [
		("Acknowledged", 1, 10, "Laboratory User"),
		("Sample Collected", 2, 30, "Nursing User"),
		("Result Published", 3, 120, "Healthcare Administrator"),
	]),
	("Lab Test", "Emergency", [
		("Acknowledged", 1, 5, "Laboratory User"),
		("Sample Collected", 2, 15, "Nursing User"),
		("Result Published", 3, 60, "Healthcare Administrator"),
	]),
	("Lab Test", "Urgent", [
		("Acknowledged", 1, 30, "Laboratory User"),
		("Sample Collected", 2, 60, "Nursing User"),
		("Result Published", 3, 240, "Healthcare Administrator"),
	]),
	("Lab Test", "Routine", [
		("Acknowledged", 1, 60, "Laboratory User"),
		("Sample Collected", 2, 180, "Nursing User"),
		("Result Published", 3, 480, "Healthcare Administrator"),
	]),
	("Radiology", "STAT", [
		("Acknowledged", 1, 15, "Physician"),
		("Performed", 2, 60, "Healthcare Administrator"),
		("Report Published", 3, 120, "Healthcare Administrator"),
	]),
	("Radiology", "Routine", [
		("Acknowledged", 1, 60, "Physician"),
		("Performed", 2, 240, "Healthcare Administrator"),
		("Report Published", 3, 480, "Healthcare Administrator"),
	]),
	("Procedure", "STAT", [
		("Acknowledged", 1, 15, "Physician"),
		("Prepared", 2, 30, "Nursing User"),
		("Performed", 3, 120, "Healthcare Administrator"),
	]),
	("Procedure", "Routine", [
		("Acknowledged", 1, 60, "Physician"),
		("Prepared", 2, 120, "Nursing User"),
		("Performed", 3, 480, "Healthcare Administrator"),
	]),
]


def execute():
	for order_type, urgency, milestones in _SLA_SEED_DATA:
		config_name = f"{order_type}-{urgency}"
		if frappe.db.exists("IPD Order SLA Config", config_name):
			continue

		doc = frappe.get_doc({
			"doctype": "IPD Order SLA Config",
			"order_type": order_type,
			"urgency": urgency,
			"is_active": 1,
			"milestones": [
				{
					"milestone": m[0],
					"sequence": m[1],
					"target_minutes": m[2],
					"escalation_role": m[3],
				}
				for m in milestones
			],
		})
		doc.insert(ignore_permissions=True)

	frappe.db.commit()
	frappe.logger("alcura_ipd_ext").info("Seeded IPD Order SLA Config defaults.")
