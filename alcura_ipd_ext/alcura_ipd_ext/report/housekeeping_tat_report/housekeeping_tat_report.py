"""Housekeeping TAT Report.

Shows housekeeping task turnaround times with ward/cleaning-type breakdowns,
SLA breach counts, and pending task listings.
"""

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
			"label": _("Task"),
			"fieldtype": "Link",
			"options": "Bed Housekeeping Task",
			"width": 120,
		},
		{
			"fieldname": "hospital_bed",
			"label": _("Bed"),
			"fieldtype": "Link",
			"options": "Hospital Bed",
			"width": 140,
		},
		{
			"fieldname": "hospital_ward",
			"label": _("Ward"),
			"fieldtype": "Link",
			"options": "Hospital Ward",
			"width": 140,
		},
		{
			"fieldname": "cleaning_type",
			"label": _("Cleaning Type"),
			"fieldtype": "Data",
			"width": 120,
		},
		{
			"fieldname": "status",
			"label": _("Status"),
			"fieldtype": "Data",
			"width": 100,
		},
		{
			"fieldname": "trigger_event",
			"label": _("Trigger"),
			"fieldtype": "Data",
			"width": 90,
		},
		{
			"fieldname": "created_on",
			"label": _("Created"),
			"fieldtype": "Datetime",
			"width": 160,
		},
		{
			"fieldname": "started_on",
			"label": _("Started"),
			"fieldtype": "Datetime",
			"width": 160,
		},
		{
			"fieldname": "completed_on",
			"label": _("Completed"),
			"fieldtype": "Datetime",
			"width": 160,
		},
		{
			"fieldname": "turnaround_minutes",
			"label": _("TAT (min)"),
			"fieldtype": "Int",
			"width": 90,
		},
		{
			"fieldname": "sla_target_minutes",
			"label": _("SLA Target (min)"),
			"fieldtype": "Int",
			"width": 110,
		},
		{
			"fieldname": "sla_breached",
			"label": _("SLA Breached"),
			"fieldtype": "Check",
			"width": 100,
		},
	]


def _get_data(filters):
	conditions = []
	params = {}

	if filters.get("ward"):
		conditions.append("task.hospital_ward = %(ward)s")
		params["ward"] = filters["ward"]

	if filters.get("cleaning_type"):
		conditions.append("task.cleaning_type = %(cleaning_type)s")
		params["cleaning_type"] = filters["cleaning_type"]

	if filters.get("status"):
		conditions.append("task.status = %(status)s")
		params["status"] = filters["status"]

	if filters.get("from_date"):
		conditions.append("task.created_on >= %(from_date)s")
		params["from_date"] = filters["from_date"]

	if filters.get("to_date"):
		conditions.append("task.created_on <= %(to_date)s")
		params["to_date"] = filters["to_date"]

	if filters.get("company"):
		conditions.append("task.company = %(company)s")
		params["company"] = filters["company"]

	where = " AND ".join(conditions) if conditions else "1=1"

	return frappe.db.sql(
		f"""
		SELECT
			task.name,
			task.hospital_bed,
			task.hospital_ward,
			task.cleaning_type,
			task.status,
			task.trigger_event,
			task.created_on,
			task.started_on,
			task.completed_on,
			task.turnaround_minutes,
			task.sla_target_minutes,
			task.sla_breached
		FROM `tabBed Housekeeping Task` task
		WHERE {where}
		ORDER BY task.created_on DESC
		""",
		params,
		as_dict=True,
	)
