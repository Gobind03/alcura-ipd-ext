"""Doctor Census — Script Report (US-E5).

Shows all admitted patients for a practitioner with round-relevant
summary data: location, days admitted, active problems, last progress
note, last vitals, allergy alerts, and overdue charts.
"""

from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import date_diff, getdate


def execute(filters: dict | None = None) -> tuple[list[dict], list[dict]]:
	filters = filters or {}
	columns = _get_columns()
	data = _get_data(filters)
	return columns, data


def _get_columns() -> list[dict]:
	return [
		{
			"fieldname": "inpatient_record",
			"label": _("Inpatient Record"),
			"fieldtype": "Link",
			"options": "Inpatient Record",
			"width": 140,
		},
		{
			"fieldname": "patient",
			"label": _("Patient"),
			"fieldtype": "Link",
			"options": "Patient",
			"width": 120,
		},
		{
			"fieldname": "patient_name",
			"label": _("Patient Name"),
			"fieldtype": "Data",
			"width": 160,
		},
		{
			"fieldname": "ward",
			"label": _("Ward"),
			"fieldtype": "Data",
			"width": 100,
		},
		{
			"fieldname": "room",
			"label": _("Room"),
			"fieldtype": "Data",
			"width": 80,
		},
		{
			"fieldname": "bed",
			"label": _("Bed"),
			"fieldtype": "Data",
			"width": 80,
		},
		{
			"fieldname": "admission_date",
			"label": _("Admitted"),
			"fieldtype": "Date",
			"width": 100,
		},
		{
			"fieldname": "days_admitted",
			"label": _("Days"),
			"fieldtype": "Int",
			"width": 60,
		},
		{
			"fieldname": "active_problems",
			"label": _("Problems"),
			"fieldtype": "Int",
			"width": 80,
		},
		{
			"fieldname": "last_progress_note",
			"label": _("Last Note"),
			"fieldtype": "Date",
			"width": 100,
		},
		{
			"fieldname": "last_vitals_at",
			"label": _("Last Vitals"),
			"fieldtype": "Datetime",
			"width": 140,
		},
		{
			"fieldname": "allergy_alert",
			"label": _("Allergy"),
			"fieldtype": "Check",
			"width": 70,
		},
		{
			"fieldname": "overdue_charts",
			"label": _("Overdue"),
			"fieldtype": "Int",
			"width": 80,
		},
		{
			"fieldname": "department",
			"label": _("Department"),
			"fieldtype": "Data",
			"width": 120,
		},
	]


def _get_data(filters: dict) -> list[dict]:
	if not filters.get("practitioner"):
		frappe.msgprint(_("Please select a Practitioner."), alert=True)
		return []

	ir = frappe.qb.DocType("Inpatient Record")

	query = (
		frappe.qb.from_(ir)
		.select(
			ir.name.as_("inpatient_record"),
			ir.patient,
			ir.patient_name,
			ir.medical_department.as_("department"),
			ir.scheduled_date.as_("admission_date"),
			ir.custom_current_ward.as_("ward"),
			ir.custom_current_room.as_("room"),
			ir.custom_current_bed.as_("bed"),
			ir.custom_allergy_alert.as_("allergy_alert"),
			ir.custom_active_problems_count.as_("active_problems"),
			ir.custom_last_progress_note_date.as_("last_progress_note"),
			ir.custom_last_vitals_at.as_("last_vitals_at"),
			ir.custom_overdue_charts_count.as_("overdue_charts"),
		)
		.where(ir.primary_practitioner == filters["practitioner"])
		.where(ir.status == "Admitted")
		.orderby(ir.custom_current_ward)
		.orderby(ir.patient_name)
	)

	if filters.get("company"):
		query = query.where(ir.company == filters["company"])
	if filters.get("ward"):
		query = query.where(ir.custom_current_ward == filters["ward"])
	if filters.get("medical_department"):
		query = query.where(ir.medical_department == filters["medical_department"])

	rows = query.run(as_dict=True)

	today_date = getdate()
	for row in rows:
		admission = getdate(row.get("admission_date")) if row.get("admission_date") else today_date
		row["days_admitted"] = date_diff(today_date, admission) + 1

	return rows
