"""Nursing Workload by Ward — Script Report (US-N1).

Ward-wise workload summary covering patient census, acuity indicators,
overdue charting, medication load, and protocol compliance gaps.
Designed for nursing superintendents making staffing decisions.
"""

from __future__ import annotations

from frappe import _

from alcura_ipd_ext.services.nursing_workload_service import (
	get_ward_workload,
	get_workload_totals,
)


def execute(filters: dict | None = None) -> tuple:
	filters = filters or {}
	columns = _get_columns()
	data = get_ward_workload(
		company=filters.get("company"),
		ward=filters.get("ward"),
	)
	chart = _get_chart(data)
	summary = _get_report_summary(data)
	return columns, data, None, chart, summary


def _get_columns() -> list[dict]:
	return [
		{"fieldname": "ward", "label": _("Ward"), "fieldtype": "Link", "options": "Hospital Ward", "width": 140},
		{"fieldname": "ward_name", "label": _("Ward Name"), "fieldtype": "Data", "width": 140},
		{"fieldname": "patient_census", "label": _("Census"), "fieldtype": "Int", "width": 80},
		{"fieldname": "high_acuity_count", "label": _("High Acuity"), "fieldtype": "Int", "width": 100},
		{"fieldname": "total_active_charts", "label": _("Active Charts"), "fieldtype": "Int", "width": 110},
		{"fieldname": "overdue_charts", "label": _("Overdue Charts"), "fieldtype": "Int", "width": 120},
		{"fieldname": "pending_mar_count", "label": _("Pending Meds"), "fieldtype": "Int", "width": 110},
		{"fieldname": "overdue_mar_count", "label": _("Overdue Meds"), "fieldtype": "Int", "width": 110},
		{"fieldname": "overdue_protocol_steps", "label": _("Overdue Protocol"), "fieldtype": "Int", "width": 130},
		{"fieldname": "workload_score", "label": _("Workload Score"), "fieldtype": "Int", "width": 120},
	]


def _get_chart(data: list[dict]) -> dict | None:
	if not data:
		return None

	labels = [row.get("ward_name") or row.get("ward", "") for row in data]

	return {
		"data": {
			"labels": labels,
			"datasets": [
				{"name": _("Census"), "values": [r.get("patient_census", 0) for r in data]},
				{"name": _("Overdue Charts"), "values": [r.get("overdue_charts", 0) for r in data]},
				{"name": _("Overdue Meds"), "values": [r.get("overdue_mar_count", 0) for r in data]},
			],
		},
		"type": "bar",
		"barOptions": {"stacked": True},
	}


def _get_report_summary(data: list[dict]) -> list[dict]:
	if not data:
		return []

	totals = get_workload_totals(data)

	return [
		{
			"value": totals["patient_census"],
			"indicator": "Blue",
			"label": _("Total Patients"),
			"datatype": "Int",
		},
		{
			"value": totals["overdue_charts"],
			"indicator": "Orange" if totals["overdue_charts"] else "Green",
			"label": _("Overdue Charts"),
			"datatype": "Int",
		},
		{
			"value": totals["overdue_mar_count"],
			"indicator": "Red" if totals["overdue_mar_count"] else "Green",
			"label": _("Overdue Meds"),
			"datatype": "Int",
		},
		{
			"value": totals["high_acuity_count"],
			"indicator": "Red" if totals["high_acuity_count"] else "Blue",
			"label": _("High Acuity"),
			"datatype": "Int",
		},
		{
			"value": totals.get("highest_workload_ward", ""),
			"indicator": "Red",
			"label": _("Highest Workload"),
			"datatype": "Data",
		},
	]
