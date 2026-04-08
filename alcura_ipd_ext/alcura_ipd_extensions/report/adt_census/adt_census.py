"""ADT Census — Script Report (US-K3).

Daily admission-discharge-transfer census showing opening count,
admissions, transfers in/out, discharges, deaths, and closing count
per ward. Supports consultant breakdown and stacked bar chart.
"""

from __future__ import annotations

from frappe import _

from alcura_ipd_ext.services.adt_census_service import get_adt_census, get_adt_totals


def execute(filters: dict | None = None):
	filters = filters or {}
	columns = _get_columns(filters)
	data = get_adt_census(filters)
	chart = _get_chart(data)
	summary = _get_report_summary(data)

	return columns, data, None, chart, summary


def _get_columns(filters: dict) -> list[dict]:
	cols = [
		{"fieldname": "ward", "label": _("Ward"), "fieldtype": "Link", "options": "Hospital Ward", "width": 160},
		{"fieldname": "ward_name", "label": _("Ward Name"), "fieldtype": "Data", "width": 140},
		{"fieldname": "opening_census", "label": _("Opening"), "fieldtype": "Int", "width": 80},
		{"fieldname": "admissions", "label": _("Admissions"), "fieldtype": "Int", "width": 90},
		{"fieldname": "transfers_in", "label": _("Transfers In"), "fieldtype": "Int", "width": 90},
		{"fieldname": "transfers_out", "label": _("Transfers Out"), "fieldtype": "Int", "width": 100},
		{"fieldname": "discharges", "label": _("Discharges"), "fieldtype": "Int", "width": 90},
		{"fieldname": "deaths", "label": _("Deaths"), "fieldtype": "Int", "width": 70},
		{"fieldname": "closing_census", "label": _("Closing"), "fieldtype": "Int", "width": 80},
	]
	return cols


def _get_chart(data: list[dict]) -> dict | None:
	if not data:
		return None

	labels = [row.get("ward_name") or row.get("ward") or "" for row in data]
	admissions = [row.get("admissions", 0) for row in data]
	discharges = [row.get("discharges", 0) for row in data]

	return {
		"data": {
			"labels": labels,
			"datasets": [
				{"name": _("Admissions"), "values": admissions},
				{"name": _("Discharges"), "values": discharges},
			],
		},
		"type": "bar",
		"colors": ["#28a745", "#dc3545"],
		"barOptions": {"stacked": True},
	}


def _get_report_summary(data: list[dict]) -> list[dict]:
	totals = get_adt_totals(data)

	return [
		{
			"value": totals["opening_census"],
			"indicator": "Blue",
			"label": _("Opening Census"),
			"datatype": "Int",
		},
		{
			"value": totals["admissions"],
			"indicator": "Green",
			"label": _("Total Admissions"),
			"datatype": "Int",
		},
		{
			"value": totals["discharges"],
			"indicator": "Orange",
			"label": _("Total Discharges"),
			"datatype": "Int",
		},
		{
			"value": totals["deaths"],
			"indicator": "Red",
			"label": _("Deaths"),
			"datatype": "Int",
		},
		{
			"value": totals["closing_census"],
			"indicator": "Blue",
			"label": _("Closing Census"),
			"datatype": "Int",
		},
		{
			"value": totals["net_movement"],
			"indicator": "Green" if totals["net_movement"] >= 0 else "Red",
			"label": _("Net Movement"),
			"datatype": "Int",
		},
	]
