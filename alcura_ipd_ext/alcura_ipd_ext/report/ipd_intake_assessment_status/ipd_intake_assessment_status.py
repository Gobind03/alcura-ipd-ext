"""IPD Intake Assessment Status — Script Report.

Tracks pending vs completed intake assessments across wards, specialties,
and date ranges to help nursing and admin staff identify bottlenecks.
"""

from __future__ import annotations

import frappe
from frappe import _


def execute(filters=None):
	filters = filters or {}
	columns = _get_columns()
	data = _get_data(filters)
	return columns, data


def _get_columns():
	return [
		{
			"fieldname": "name",
			"label": _("Assessment"),
			"fieldtype": "Link",
			"options": "IPD Intake Assessment",
			"width": 180,
		},
		{
			"fieldname": "patient",
			"label": _("Patient"),
			"fieldtype": "Link",
			"options": "Patient",
			"width": 160,
		},
		{
			"fieldname": "patient_name",
			"label": _("Patient Name"),
			"fieldtype": "Data",
			"width": 160,
		},
		{
			"fieldname": "inpatient_record",
			"label": _("Inpatient Record"),
			"fieldtype": "Link",
			"options": "Inpatient Record",
			"width": 160,
		},
		{
			"fieldname": "template",
			"label": _("Template"),
			"fieldtype": "Link",
			"options": "IPD Intake Assessment Template",
			"width": 200,
		},
		{
			"fieldname": "specialty",
			"label": _("Specialty"),
			"fieldtype": "Link",
			"options": "Medical Department",
			"width": 140,
		},
		{
			"fieldname": "status",
			"label": _("Status"),
			"fieldtype": "Data",
			"width": 100,
		},
		{
			"fieldname": "assessed_by",
			"label": _("Assessed By"),
			"fieldtype": "Link",
			"options": "Healthcare Practitioner",
			"width": 140,
		},
		{
			"fieldname": "assessment_datetime",
			"label": _("Created On"),
			"fieldtype": "Datetime",
			"width": 160,
		},
		{
			"fieldname": "completed_on",
			"label": _("Completed On"),
			"fieldtype": "Datetime",
			"width": 160,
		},
		{
			"fieldname": "completed_by",
			"label": _("Completed By"),
			"fieldtype": "Link",
			"options": "User",
			"width": 140,
		},
	]


def _get_data(filters):
	conditions = []
	values = {}

	if filters.get("company"):
		conditions.append("ia.company = %(company)s")
		values["company"] = filters["company"]

	if filters.get("specialty"):
		conditions.append("ia.specialty = %(specialty)s")
		values["specialty"] = filters["specialty"]

	if filters.get("status"):
		conditions.append("ia.status = %(status)s")
		values["status"] = filters["status"]

	if filters.get("template"):
		conditions.append("ia.template = %(template)s")
		values["template"] = filters["template"]

	if filters.get("from_date"):
		conditions.append("ia.assessment_datetime >= %(from_date)s")
		values["from_date"] = filters["from_date"]

	if filters.get("to_date"):
		conditions.append("ia.assessment_datetime <= %(to_date)s")
		values["to_date"] = filters["to_date"]

	where_clause = " AND ".join(conditions) if conditions else "1=1"

	return frappe.db.sql(
		f"""
		SELECT
			ia.name,
			ia.patient,
			p.patient_name,
			ia.inpatient_record,
			ia.template,
			ia.specialty,
			ia.status,
			ia.assessed_by,
			ia.assessment_datetime,
			ia.completed_on,
			ia.completed_by
		FROM `tabIPD Intake Assessment` ia
		LEFT JOIN `tabPatient` p ON p.name = ia.patient
		WHERE {where_clause}
		ORDER BY ia.assessment_datetime DESC
		""",
		values=values,
		as_dict=True,
	)
