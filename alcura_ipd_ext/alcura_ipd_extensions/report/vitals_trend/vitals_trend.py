"""Vitals Trend Report — line chart of vital parameters over time."""

from __future__ import annotations

import frappe
from frappe import _


def execute(filters=None):
	filters = filters or {}
	columns = get_columns()
	data = get_data(filters)
	chart = get_chart(data, filters)
	return columns, data, None, chart


def get_columns():
	return [
		{"fieldname": "entry_datetime", "label": _("Date/Time"), "fieldtype": "Datetime", "width": 180},
		{"fieldname": "parameter_name", "label": _("Parameter"), "fieldtype": "Data", "width": 140},
		{"fieldname": "numeric_value", "label": _("Value"), "fieldtype": "Float", "width": 100},
		{"fieldname": "uom", "label": _("UOM"), "fieldtype": "Data", "width": 80},
		{"fieldname": "is_critical", "label": _("Critical"), "fieldtype": "Check", "width": 70},
		{"fieldname": "recorded_by_name", "label": _("Recorded By"), "fieldtype": "Data", "width": 150},
		{"fieldname": "patient_name", "label": _("Patient"), "fieldtype": "Data", "width": 150},
		{"fieldname": "entry_name", "label": _("Entry"), "fieldtype": "Link", "options": "IPD Chart Entry", "width": 120},
	]


def get_data(filters):
	conditions = ["ce.status = 'Active'", "ce.chart_type = 'Vitals'"]
	values = {}

	if filters.get("inpatient_record"):
		conditions.append("ce.inpatient_record = %(inpatient_record)s")
		values["inpatient_record"] = filters["inpatient_record"]

	if filters.get("patient"):
		conditions.append("ce.patient = %(patient)s")
		values["patient"] = filters["patient"]

	if filters.get("from_date"):
		conditions.append("ce.entry_datetime >= %(from_date)s")
		values["from_date"] = filters["from_date"]

	if filters.get("to_date"):
		conditions.append("ce.entry_datetime <= %(to_date)s")
		values["to_date"] = filters["to_date"]

	where = " AND ".join(conditions)

	return frappe.db.sql(
		f"""
		SELECT
			ce.entry_datetime,
			co.parameter_name,
			co.numeric_value,
			co.uom,
			co.is_critical,
			ce.recorded_by_name,
			p.patient_name,
			ce.name AS entry_name
		FROM `tabIPD Chart Observation` co
		JOIN `tabIPD Chart Entry` ce ON ce.name = co.parent
		JOIN `tabPatient` p ON p.name = ce.patient
		WHERE {where}
			AND co.numeric_value IS NOT NULL
			AND co.numeric_value != 0
		ORDER BY ce.entry_datetime ASC, co.idx ASC
		""",
		values,
		as_dict=True,
	)


def get_chart(data, filters):
	if not data:
		return None

	params: dict[str, list] = {}
	timestamps: list[str] = []
	ts_set: set[str] = set()

	for row in data:
		ts = str(row.entry_datetime)
		if ts not in ts_set:
			timestamps.append(ts)
			ts_set.add(ts)

		params.setdefault(row.parameter_name, {})
		params[row.parameter_name][ts] = row.numeric_value

	datasets = []
	for param_name, values in params.items():
		datasets.append({
			"name": param_name,
			"values": [values.get(ts, 0) for ts in timestamps],
		})

	return {
		"data": {
			"labels": timestamps,
			"datasets": datasets,
		},
		"type": "line",
		"lineOptions": {"regionFill": 0},
	}
