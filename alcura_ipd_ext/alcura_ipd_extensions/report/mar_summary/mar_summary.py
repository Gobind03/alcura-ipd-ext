"""MAR Summary Report — medication administration compliance tracking."""

from __future__ import annotations

import frappe
from frappe import _


def execute(filters=None):
	filters = filters or {}
	columns = get_columns()
	data = get_data(filters)
	chart = get_chart(data)
	return columns, data, None, chart


def get_columns():
	return [
		{"fieldname": "name", "label": _("Entry"), "fieldtype": "Link", "options": "IPD MAR Entry", "width": 120},
		{"fieldname": "patient_name", "label": _("Patient"), "fieldtype": "Data", "width": 150},
		{"fieldname": "medication_name", "label": _("Medication"), "fieldtype": "Data", "width": 180},
		{"fieldname": "dose", "label": _("Dose"), "fieldtype": "Data", "width": 100},
		{"fieldname": "route", "label": _("Route"), "fieldtype": "Data", "width": 80},
		{"fieldname": "scheduled_time", "label": _("Scheduled"), "fieldtype": "Datetime", "width": 170},
		{"fieldname": "administered_at", "label": _("Administered"), "fieldtype": "Datetime", "width": 170},
		{"fieldname": "administration_status", "label": _("Status"), "fieldtype": "Data", "width": 120},
		{"fieldname": "ward", "label": _("Ward"), "fieldtype": "Link", "options": "Hospital Ward", "width": 120},
	]


def get_data(filters):
	conditions = ["mar.status = 'Active'"]
	values = {}

	if filters.get("inpatient_record"):
		conditions.append("mar.inpatient_record = %(inpatient_record)s")
		values["inpatient_record"] = filters["inpatient_record"]

	if filters.get("patient"):
		conditions.append("mar.patient = %(patient)s")
		values["patient"] = filters["patient"]

	if filters.get("administration_status"):
		conditions.append("mar.administration_status = %(administration_status)s")
		values["administration_status"] = filters["administration_status"]

	if filters.get("from_date"):
		conditions.append("mar.scheduled_time >= %(from_date)s")
		values["from_date"] = filters["from_date"]

	if filters.get("to_date"):
		conditions.append("mar.scheduled_time <= %(to_date)s")
		values["to_date"] = filters["to_date"]

	if filters.get("ward"):
		conditions.append("mar.ward = %(ward)s")
		values["ward"] = filters["ward"]

	where = " AND ".join(conditions)

	return frappe.db.sql(
		f"""
		SELECT
			mar.name,
			p.patient_name,
			mar.medication_name,
			mar.dose,
			mar.route,
			mar.scheduled_time,
			mar.administered_at,
			mar.administration_status,
			mar.ward
		FROM `tabIPD MAR Entry` mar
		JOIN `tabPatient` p ON p.name = mar.patient
		WHERE {where}
		ORDER BY mar.scheduled_time ASC
		""",
		values,
		as_dict=True,
	)


def get_chart(data):
	if not data:
		return None

	status_counts: dict[str, int] = {}
	for row in data:
		st = row.administration_status
		status_counts[st] = status_counts.get(st, 0) + 1

	return {
		"data": {
			"labels": list(status_counts.keys()),
			"datasets": [{"values": list(status_counts.values())}],
		},
		"type": "pie",
	}
