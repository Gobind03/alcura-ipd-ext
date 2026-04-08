"""Protocol Compliance Report — shows compliance by bundle type, ward, and date."""

from __future__ import annotations

import frappe
from frappe import _


def execute(filters=None):
	columns = get_columns()
	data = get_data(filters or {})
	return columns, data


def get_columns():
	return [
		{
			"fieldname": "active_bundle",
			"label": _("Active Bundle"),
			"fieldtype": "Link",
			"options": "Active Protocol Bundle",
			"width": 140,
		},
		{
			"fieldname": "protocol_bundle",
			"label": _("Protocol"),
			"fieldtype": "Link",
			"options": "Monitoring Protocol Bundle",
			"width": 200,
		},
		{
			"fieldname": "category",
			"label": _("Category"),
			"fieldtype": "Data",
			"width": 100,
		},
		{
			"fieldname": "patient",
			"label": _("Patient"),
			"fieldtype": "Link",
			"options": "Patient",
			"width": 140,
		},
		{
			"fieldname": "ward",
			"label": _("Ward"),
			"fieldtype": "Link",
			"options": "Hospital Ward",
			"width": 120,
		},
		{
			"fieldname": "status",
			"label": _("Status"),
			"fieldtype": "Data",
			"width": 100,
		},
		{
			"fieldname": "compliance_score",
			"label": _("Compliance %"),
			"fieldtype": "Percent",
			"width": 110,
		},
		{
			"fieldname": "total_steps",
			"label": _("Total Steps"),
			"fieldtype": "Int",
			"width": 90,
		},
		{
			"fieldname": "completed_steps",
			"label": _("Completed"),
			"fieldtype": "Int",
			"width": 90,
		},
		{
			"fieldname": "missed_steps",
			"label": _("Missed"),
			"fieldtype": "Int",
			"width": 80,
		},
		{
			"fieldname": "activated_at",
			"label": _("Activated"),
			"fieldtype": "Datetime",
			"width": 160,
		},
	]


def get_data(filters):
	conditions = []
	values = {}

	if filters.get("protocol_bundle"):
		conditions.append("apb.protocol_bundle = %(protocol_bundle)s")
		values["protocol_bundle"] = filters["protocol_bundle"]

	if filters.get("status"):
		conditions.append("apb.status = %(status)s")
		values["status"] = filters["status"]

	if filters.get("from_date"):
		conditions.append("apb.activated_at >= %(from_date)s")
		values["from_date"] = filters["from_date"]

	if filters.get("to_date"):
		conditions.append("apb.activated_at <= %(to_date)s")
		values["to_date"] = filters["to_date"]

	where = " AND ".join(conditions) if conditions else "1=1"

	bundles = frappe.db.sql(
		f"""
		SELECT
			apb.name AS active_bundle,
			apb.protocol_bundle,
			mpb.category,
			apb.patient,
			apb.inpatient_record,
			apb.status,
			apb.compliance_score,
			apb.activated_at
		FROM `tabActive Protocol Bundle` apb
		LEFT JOIN `tabMonitoring Protocol Bundle` mpb
			ON mpb.name = apb.protocol_bundle
		WHERE {where}
		ORDER BY apb.activated_at DESC
		""",
		values,
		as_dict=True,
	)

	for row in bundles:
		row["ward"] = frappe.db.get_value(
			"Inpatient Record",
			row.get("inpatient_record"),
			"custom_current_ward",
		)

		step_counts = frappe.db.sql(
			"""
			SELECT
				COUNT(*) AS total,
				SUM(CASE WHEN status = 'Completed' THEN 1 ELSE 0 END) AS completed,
				SUM(CASE WHEN status = 'Missed' THEN 1 ELSE 0 END) AS missed
			FROM `tabProtocol Step Tracker`
			WHERE parent = %(bundle)s
			""",
			{"bundle": row["active_bundle"]},
			as_dict=True,
		)
		if step_counts:
			row["total_steps"] = step_counts[0].total or 0
			row["completed_steps"] = step_counts[0].completed or 0
			row["missed_steps"] = step_counts[0].missed or 0

		if filters.get("ward") and row["ward"] != filters["ward"]:
			continue

	if filters.get("ward"):
		bundles = [r for r in bundles if r.get("ward") == filters["ward"]]

	return bundles
