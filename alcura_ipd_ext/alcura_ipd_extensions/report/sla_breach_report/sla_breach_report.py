"""SLA Breach Report (US-L3).

Shows orders that have breached their SLA targets with breach details,
department breakdown, and summary metrics.
"""

from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import now_datetime, time_diff_in_seconds


def execute(filters=None):
	filters = filters or {}
	columns = _get_columns()
	data = _get_data(filters)
	report_summary = _get_report_summary(data)
	chart = _get_chart(data)
	return columns, data, None, chart, report_summary


def _get_columns():
	return [
		{"fieldname": "name", "label": _("Order"), "fieldtype": "Link", "options": "IPD Clinical Order", "width": 160},
		{"fieldname": "patient_name", "label": _("Patient"), "fieldtype": "Data", "width": 150},
		{"fieldname": "order_type", "label": _("Type"), "fieldtype": "Data", "width": 100},
		{"fieldname": "urgency", "label": _("Urgency"), "fieldtype": "Data", "width": 90},
		{"fieldname": "status", "label": _("Status"), "fieldtype": "Data", "width": 100},
		{"fieldname": "ward", "label": _("Ward"), "fieldtype": "Link", "options": "Hospital Ward", "width": 120},
		{"fieldname": "target_department", "label": _("Department"), "fieldtype": "Link", "options": "Medical Department", "width": 130},
		{"fieldname": "ordering_practitioner_name", "label": _("Doctor"), "fieldtype": "Data", "width": 140},
		{"fieldname": "ordered_at", "label": _("Ordered At"), "fieldtype": "Datetime", "width": 160},
		{"fieldname": "sla_breach_count", "label": _("Breach Count"), "fieldtype": "Int", "width": 100},
		{"fieldname": "breached_milestone", "label": _("Breached Milestone"), "fieldtype": "Data", "width": 150},
		{"fieldname": "target_time", "label": _("Target"), "fieldtype": "Datetime", "width": 160},
		{"fieldname": "delay_minutes", "label": _("Delay (min)"), "fieldtype": "Float", "width": 100},
	]


def _get_data(filters):
	cond_parts = ["co.is_sla_breached = 1"]
	values = {}

	if filters.get("from_date"):
		cond_parts.append("co.ordered_at >= %(from_date)s")
		values["from_date"] = filters["from_date"]
	if filters.get("to_date"):
		cond_parts.append("co.ordered_at <= %(to_date_end)s")
		values["to_date_end"] = filters["to_date"] + " 23:59:59"
	if filters.get("order_type"):
		cond_parts.append("co.order_type = %(order_type)s")
		values["order_type"] = filters["order_type"]
	if filters.get("urgency"):
		cond_parts.append("co.urgency = %(urgency)s")
		values["urgency"] = filters["urgency"]
	if filters.get("ward"):
		cond_parts.append("co.ward = %(ward)s")
		values["ward"] = filters["ward"]
	if filters.get("department"):
		cond_parts.append("co.target_department = %(department)s")
		values["department"] = filters["department"]

	where = " AND ".join(cond_parts)

	orders = frappe.db.sql(
		f"""
		SELECT
			co.name, co.patient_name, co.order_type, co.urgency,
			co.status, co.ward, co.target_department,
			co.ordering_practitioner_name, co.ordered_at,
			co.sla_breach_count
		FROM `tabIPD Clinical Order` co
		WHERE {where}
		ORDER BY co.ordered_at DESC
		LIMIT 1000
		""",
		values,
		as_dict=True,
	)

	result = []
	now = now_datetime()

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
					row["delay_minutes"] = round(
						time_diff_in_seconds(now, ms.target_at) / 60, 1
					)
				result.append(row)
		else:
			order["breached_milestone"] = ""
			order["target_time"] = None
			order["delay_minutes"] = None
			result.append(order)

	return result


def _get_report_summary(data: list[dict]) -> list[dict]:
	if not data:
		return []

	unique_orders = {r["name"] for r in data}
	total_breaches = len(data)
	delays = [r["delay_minutes"] for r in data if r.get("delay_minutes") is not None]
	avg_delay = round(sum(delays) / len(delays), 1) if delays else 0
	max_delay = round(max(delays), 1) if delays else 0

	return [
		{"value": len(unique_orders), "label": _("Breached Orders"), "datatype": "Int", "indicator": "red"},
		{"value": total_breaches, "label": _("Total Breaches"), "datatype": "Int"},
		{"value": avg_delay, "label": _("Avg Delay (min)"), "datatype": "Float"},
		{"value": max_delay, "label": _("Max Delay (min)"), "datatype": "Float", "indicator": "red"},
	]


def _get_chart(data: list[dict]) -> dict | None:
	if not data:
		return None

	type_counts: dict[str, int] = {}
	for row in data:
		ot = row.get("order_type") or "Unknown"
		type_counts[ot] = type_counts.get(ot, 0) + 1

	labels = sorted(type_counts.keys())
	values = [type_counts[ot] for ot in labels]

	return {
		"data": {
			"labels": labels,
			"datasets": [{"name": _("Breach Count"), "values": values}],
		},
		"type": "bar",
		"colors": ["#ff5858"],
	}
