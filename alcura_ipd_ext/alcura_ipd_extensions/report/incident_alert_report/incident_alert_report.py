"""Incident and Critical Alert Report — Script Report (US-N2).

Consolidated view of safety and quality incidents across fall-risk
events, missed medications, critical observations, and SLA breaches.
"""

from __future__ import annotations

from frappe import _

from alcura_ipd_ext.services.incident_report_service import (
	get_incident_summary,
	get_incidents,
)


def execute(filters: dict | None = None) -> tuple:
	filters = filters or {}
	columns = _get_columns()
	data = get_incidents(
		from_date=filters.get("from_date", ""),
		to_date=filters.get("to_date", ""),
		incident_type=filters.get("incident_type"),
		ward=filters.get("ward"),
		patient=filters.get("patient"),
		severity=filters.get("severity"),
	)
	chart = _get_chart(data)
	summary = _get_report_summary(data)
	return columns, data, None, chart, summary


def _get_columns() -> list[dict]:
	return [
		{"fieldname": "incident_datetime", "label": _("Date/Time"), "fieldtype": "Datetime", "width": 170},
		{"fieldname": "incident_type", "label": _("Incident Type"), "fieldtype": "Data", "width": 150},
		{"fieldname": "severity", "label": _("Severity"), "fieldtype": "Data", "width": 90},
		{"fieldname": "patient", "label": _("Patient"), "fieldtype": "Link", "options": "Patient", "width": 120},
		{"fieldname": "patient_name", "label": _("Patient Name"), "fieldtype": "Data", "width": 150},
		{"fieldname": "ward", "label": _("Ward"), "fieldtype": "Link", "options": "Hospital Ward", "width": 120},
		{"fieldname": "description", "label": _("Description"), "fieldtype": "Data", "width": 250},
		{"fieldname": "source_doctype", "label": _("Source Type"), "fieldtype": "Data", "width": 130},
		{"fieldname": "source_name", "label": _("Source"), "fieldtype": "Dynamic Link", "options": "source_doctype", "width": 140},
		{"fieldname": "status", "label": _("Status"), "fieldtype": "Data", "width": 100},
	]


def _get_chart(data: list[dict]) -> dict | None:
	if not data:
		return None

	type_counts = get_incident_summary(data)
	labels = sorted(type_counts.keys())
	values = [type_counts[k] for k in labels]

	return {
		"data": {
			"labels": labels,
			"datasets": [{"name": _("Incidents"), "values": values}],
		},
		"type": "pie",
	}


def _get_report_summary(data: list[dict]) -> list[dict]:
	if not data:
		return []

	type_counts = get_incident_summary(data)
	total = len(data)

	items = [
		{
			"value": total,
			"indicator": "Red" if total else "Green",
			"label": _("Total Incidents"),
			"datatype": "Int",
		},
	]

	indicator_map = {
		"Fall Risk": "Red",
		"Pressure Risk": "Red",
		"Nutrition Risk": "Orange",
		"Missed Medication": "Orange",
		"Critical Observation": "Red",
		"SLA Breach": "Orange",
	}

	for itype in sorted(type_counts.keys()):
		items.append({
			"value": type_counts[itype],
			"indicator": indicator_map.get(itype, "Blue"),
			"label": _(itype),
			"datatype": "Int",
		})

	return items
