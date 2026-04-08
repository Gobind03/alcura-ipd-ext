"""SLA Breach Report.

Shows orders that have breached their SLA targets with breach details,
grouped by order type with breach counts.
"""

from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import time_diff_in_seconds


def execute(filters=None):
	filters = filters or {}
	columns = _get_columns()
	data = _get_data(filters)
	return columns, data


def _get_columns():
	return [
		{"fieldname": "name", "label": _("Order"), "fieldtype": "Link", "options": "IPD Clinical Order", "width": 160},
		{"fieldname": "patient_name", "label": _("Patient"), "fieldtype": "Data", "width": 150},
		{"fieldname": "order_type", "label": _("Type"), "fieldtype": "Data", "width": 100},
		{"fieldname": "urgency", "label": _("Urgency"), "fieldtype": "Data", "width": 90},
		{"fieldname": "status", "label": _("Status"), "fieldtype": "Data", "width": 100},
		{"fieldname": "ward", "label": _("Ward"), "fieldtype": "Link", "options": "Hospital Ward", "width": 120},
		{"fieldname": "ordering_practitioner_name", "label": _("Doctor"), "fieldtype": "Data", "width": 140},
		{"fieldname": "ordered_at", "label": _("Ordered At"), "fieldtype": "Datetime", "width": 160},
		{"fieldname": "sla_breach_count", "label": _("Breach Count"), "fieldtype": "Int", "width": 100},
		{"fieldname": "breached_milestone", "label": _("Breached Milestone"), "fieldtype": "Data", "width": 150},
		{"fieldname": "target_time", "label": _("Target"), "fieldtype": "Datetime", "width": 160},
		{"fieldname": "delay_minutes", "label": _("Delay (min)"), "fieldtype": "Float", "width": 100},
	]


def _get_data(filters):
	conditions = {"is_sla_breached": 1}

	if filters.get("from_date"):
		conditions["ordered_at"] = (">=", filters["from_date"])
	if filters.get("to_date"):
		conditions["ordered_at"] = ("<=", filters["to_date"] + " 23:59:59")
	if filters.get("order_type"):
		conditions["order_type"] = filters["order_type"]
	if filters.get("urgency"):
		conditions["urgency"] = filters["urgency"]
	if filters.get("ward"):
		conditions["ward"] = filters["ward"]

	orders = frappe.get_all(
		"IPD Clinical Order",
		filters=conditions,
		fields=[
			"name", "patient_name", "order_type", "urgency", "status", "ward",
			"ordering_practitioner_name", "ordered_at",
			"sla_breach_count",
		],
		order_by="ordered_at desc",
		limit_page_length=500,
	)

	result = []
	for order in orders:
		milestones = frappe.get_all(
			"IPD Order SLA Milestone",
			filters={"parent": order.name, "is_breached": 1},
			fields=["milestone", "target_at", "actual_at"],
			order_by="idx asc",
		)

		if milestones:
			for ms in milestones:
				row = dict(order)
				row["breached_milestone"] = ms.milestone
				row["target_time"] = ms.target_at
				if ms.actual_at and ms.target_at:
					row["delay_minutes"] = round(
						time_diff_in_seconds(ms.actual_at, ms.target_at) / 60, 1
					)
				elif ms.target_at:
					from frappe.utils import now_datetime

					row["delay_minutes"] = round(
						time_diff_in_seconds(now_datetime(), ms.target_at) / 60, 1
					)
				result.append(row)
		else:
			order["breached_milestone"] = ""
			order["target_time"] = None
			order["delay_minutes"] = None
			result.append(order)

	return result
