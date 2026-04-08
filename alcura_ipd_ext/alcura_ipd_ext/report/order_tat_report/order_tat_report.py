"""Order TAT (Turnaround Time) Report.

Shows turnaround time analysis for IPD Clinical Orders with filters
for date range, order type, urgency, ward, and consultant.
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
		{"fieldname": "acknowledged_at", "label": _("Acknowledged At"), "fieldtype": "Datetime", "width": 160},
		{"fieldname": "completed_at", "label": _("Completed At"), "fieldtype": "Datetime", "width": 160},
		{"fieldname": "tat_minutes", "label": _("TAT (min)"), "fieldtype": "Float", "width": 100},
		{"fieldname": "ack_tat_minutes", "label": _("Ack TAT (min)"), "fieldtype": "Float", "width": 110},
		{"fieldname": "is_sla_breached", "label": _("SLA Breached"), "fieldtype": "Check", "width": 100},
	]


def _get_data(filters):
	conditions = {}

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
	if filters.get("consultant"):
		conditions["ordering_practitioner"] = filters["consultant"]
	if filters.get("status"):
		conditions["status"] = filters["status"]

	orders = frappe.get_all(
		"IPD Clinical Order",
		filters=conditions,
		fields=[
			"name", "patient_name", "order_type", "urgency", "status", "ward",
			"ordering_practitioner_name",
			"ordered_at", "acknowledged_at", "completed_at",
			"is_sla_breached",
		],
		order_by="ordered_at desc",
		limit_page_length=1000,
	)

	for row in orders:
		if row.ordered_at and row.completed_at:
			row["tat_minutes"] = round(time_diff_in_seconds(row.completed_at, row.ordered_at) / 60, 1)
		else:
			row["tat_minutes"] = None

		if row.ordered_at and row.acknowledged_at:
			row["ack_tat_minutes"] = round(time_diff_in_seconds(row.acknowledged_at, row.ordered_at) / 60, 1)
		else:
			row["ack_tat_minutes"] = None

	return orders
