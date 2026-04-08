"""Order TAT (Turnaround Time) Report (US-L3).

Shows turnaround time analysis for IPD Clinical Orders with filters
for date range, order type, urgency, ward, department, and consultant.
Includes summary metrics, SLA target comparison, and chart.
"""

from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import time_diff_in_seconds


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
		{"fieldname": "acknowledged_at", "label": _("Acknowledged At"), "fieldtype": "Datetime", "width": 160},
		{"fieldname": "completed_at", "label": _("Completed At"), "fieldtype": "Datetime", "width": 160},
		{"fieldname": "tat_minutes", "label": _("TAT (min)"), "fieldtype": "Float", "width": 100},
		{"fieldname": "ack_tat_minutes", "label": _("Ack TAT (min)"), "fieldtype": "Float", "width": 110},
		{"fieldname": "sla_target_minutes", "label": _("SLA Target (min)"), "fieldtype": "Float", "width": 120},
		{"fieldname": "is_sla_breached", "label": _("SLA Breached"), "fieldtype": "Check", "width": 100},
	]


def _get_data(filters):
	cond_parts = []
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
	if filters.get("consultant"):
		cond_parts.append("co.ordering_practitioner = %(consultant)s")
		values["consultant"] = filters["consultant"]
	if filters.get("status"):
		cond_parts.append("co.status = %(status)s")
		values["status"] = filters["status"]
	if filters.get("department"):
		cond_parts.append("co.target_department = %(department)s")
		values["department"] = filters["department"]

	where = " AND ".join(cond_parts) if cond_parts else "1=1"

	orders = frappe.db.sql(
		f"""
		SELECT
			co.name, co.patient_name, co.order_type, co.urgency,
			co.status, co.ward, co.target_department,
			co.ordering_practitioner_name,
			co.ordered_at, co.acknowledged_at, co.completed_at,
			co.is_sla_breached
		FROM `tabIPD Clinical Order` co
		WHERE {where}
		ORDER BY co.ordered_at DESC
		LIMIT 2000
		""",
		values,
		as_dict=True,
	)

	sla_targets = _get_sla_targets()

	for row in orders:
		if row.ordered_at and row.completed_at:
			row["tat_minutes"] = round(
				time_diff_in_seconds(row.completed_at, row.ordered_at) / 60, 1
			)
		else:
			row["tat_minutes"] = None

		if row.ordered_at and row.acknowledged_at:
			row["ack_tat_minutes"] = round(
				time_diff_in_seconds(row.acknowledged_at, row.ordered_at) / 60, 1
			)
		else:
			row["ack_tat_minutes"] = None

		target_key = (row.order_type or "", row.urgency or "")
		row["sla_target_minutes"] = sla_targets.get(target_key)

	return orders


def _get_sla_targets() -> dict[tuple[str, str], float]:
	"""Build a lookup of (order_type, urgency) -> target_minutes from
	IPD Order SLA Config."""
	configs = frappe.get_all(
		"IPD Order SLA Config",
		fields=["order_type", "urgency", "target_minutes"],
	)
	return {(c.order_type, c.urgency): c.target_minutes for c in configs}


def _get_report_summary(data: list[dict]) -> list[dict]:
	if not data:
		return []

	total = len(data)
	completed_tats = [r["tat_minutes"] for r in data if r.get("tat_minutes") is not None]
	ack_tats = [r["ack_tat_minutes"] for r in data if r.get("ack_tat_minutes") is not None]
	breached = sum(1 for r in data if r.get("is_sla_breached"))

	avg_tat = round(sum(completed_tats) / len(completed_tats), 1) if completed_tats else 0
	avg_ack = round(sum(ack_tats) / len(ack_tats), 1) if ack_tats else 0

	sorted_tats = sorted(completed_tats)
	median_tat = 0
	if sorted_tats:
		mid = len(sorted_tats) // 2
		median_tat = (
			sorted_tats[mid]
			if len(sorted_tats) % 2
			else round((sorted_tats[mid - 1] + sorted_tats[mid]) / 2, 1)
		)

	breach_pct = round((breached / total) * 100, 1) if total else 0

	return [
		{"value": total, "label": _("Total Orders"), "datatype": "Int"},
		{"value": avg_tat, "label": _("Avg TAT (min)"), "datatype": "Float"},
		{"value": median_tat, "label": _("Median TAT (min)"), "datatype": "Float"},
		{"value": avg_ack, "label": _("Avg Ack TAT (min)"), "datatype": "Float"},
		{
			"value": breach_pct,
			"label": _("% Breached"),
			"datatype": "Percent",
			"indicator": "red" if breach_pct > 10 else ("orange" if breach_pct > 5 else "green"),
		},
	]


def _get_chart(data: list[dict]) -> dict | None:
	if not data:
		return None

	type_tats: dict[str, list[float]] = {}
	for row in data:
		ot = row.get("order_type") or "Unknown"
		tat = row.get("tat_minutes")
		if tat is not None:
			type_tats.setdefault(ot, []).append(tat)

	if not type_tats:
		return None

	labels = sorted(type_tats.keys())
	avg_values = [
		round(sum(type_tats[ot]) / len(type_tats[ot]), 1) for ot in labels
	]

	sla_targets = _get_sla_targets()
	target_values = []
	for ot in labels:
		routine_target = sla_targets.get((ot, "Routine"))
		target_values.append(routine_target or 0)

	datasets = [
		{"name": _("Avg TAT (min)"), "values": avg_values},
	]
	if any(v > 0 for v in target_values):
		datasets.append({"name": _("SLA Target (Routine)"), "values": target_values})

	return {
		"data": {"labels": labels, "datasets": datasets},
		"type": "bar",
	}
