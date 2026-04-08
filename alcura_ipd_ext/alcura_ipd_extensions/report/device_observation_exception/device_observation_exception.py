"""Device Observation Exception — Script Report (US-N3).

Shows device feed failures, missing observation intervals, and
unacknowledged abnormal readings for ICU operations managers.
"""

from __future__ import annotations

from frappe import _

from alcura_ipd_ext.services.device_exception_service import (
	get_exception_summary,
	get_exceptions,
)


def execute(filters: dict | None = None) -> tuple:
	filters = filters or {}
	columns = _get_columns()
	data = get_exceptions(
		from_date=filters.get("from_date", ""),
		to_date=filters.get("to_date", ""),
		exception_type=filters.get("exception_type"),
		ward=filters.get("ward"),
		patient=filters.get("patient"),
		device_type=filters.get("device_type"),
	)
	chart = _get_chart(data)
	summary = _get_report_summary(data)
	return columns, data, None, chart, summary


def _get_columns() -> list[dict]:
	return [
		{"fieldname": "exception_type", "label": _("Exception Type"), "fieldtype": "Data", "width": 180},
		{"fieldname": "datetime", "label": _("Date/Time"), "fieldtype": "Datetime", "width": 170},
		{"fieldname": "patient", "label": _("Patient"), "fieldtype": "Link", "options": "Patient", "width": 120},
		{"fieldname": "patient_name", "label": _("Patient Name"), "fieldtype": "Data", "width": 150},
		{"fieldname": "ward", "label": _("Ward"), "fieldtype": "Link", "options": "Hospital Ward", "width": 120},
		{"fieldname": "device_type", "label": _("Device Type"), "fieldtype": "Data", "width": 130},
		{"fieldname": "device_id", "label": _("Device ID"), "fieldtype": "Data", "width": 120},
		{"fieldname": "chart", "label": _("Chart"), "fieldtype": "Link", "options": "IPD Bedside Chart", "width": 130},
		{"fieldname": "parameter", "label": _("Parameter"), "fieldtype": "Data", "width": 120},
		{"fieldname": "description", "label": _("Description"), "fieldtype": "Data", "width": 250},
		{"fieldname": "source_doctype", "label": _("Source Type"), "fieldtype": "Data", "width": 140},
		{"fieldname": "source_name", "label": _("Source"), "fieldtype": "Dynamic Link", "options": "source_doctype", "width": 140},
	]


def _get_chart(data: list[dict]) -> dict | None:
	if not data:
		return None

	type_counts = get_exception_summary(data)
	labels = sorted(type_counts.keys())
	values = [type_counts[k] for k in labels]

	return {
		"data": {
			"labels": labels,
			"datasets": [{"name": _("Exceptions"), "values": values}],
		},
		"type": "bar",
		"colors": ["#ff5858"],
	}


def _get_report_summary(data: list[dict]) -> list[dict]:
	if not data:
		return []

	type_counts = get_exception_summary(data)

	from alcura_ipd_ext.services.device_exception_service import (
		CONNECTIVITY_FAILURE,
		MISSING_OBSERVATION,
		UNACKNOWLEDGED_ABNORMAL,
	)

	return [
		{
			"value": len(data),
			"indicator": "Red" if data else "Green",
			"label": _("Total Exceptions"),
			"datatype": "Int",
		},
		{
			"value": type_counts.get(CONNECTIVITY_FAILURE, 0),
			"indicator": "Red",
			"label": _("Connectivity Failures"),
			"datatype": "Int",
		},
		{
			"value": type_counts.get(MISSING_OBSERVATION, 0),
			"indicator": "Orange",
			"label": _("Missing Observations"),
			"datatype": "Int",
		},
		{
			"value": type_counts.get(UNACKNOWLEDGED_ABNORMAL, 0),
			"indicator": "Red",
			"label": _("Unacknowledged Abnormals"),
			"datatype": "Int",
		},
	]
