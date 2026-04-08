"""IPD Consultation Notes — Script Report.

Lists all Patient Encounters linked to Inpatient Records via
``custom_linked_inpatient_record``, with bed/ward context from the IR.
Supports filtering by company, patient, practitioner, department, note
type, ward, and date range.
"""

from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import getdate


def execute(filters: dict | None = None) -> tuple[list[dict], list[dict]]:
	filters = filters or {}
	columns = _get_columns()
	data = _get_data(filters)
	return columns, data


def _get_columns() -> list[dict]:
	return [
		{
			"fieldname": "encounter",
			"label": _("Encounter"),
			"fieldtype": "Link",
			"options": "Patient Encounter",
			"width": 140,
		},
		{
			"fieldname": "encounter_date",
			"label": _("Date"),
			"fieldtype": "Date",
			"width": 100,
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
			"fieldname": "practitioner_name",
			"label": _("Practitioner"),
			"fieldtype": "Data",
			"width": 150,
		},
		{
			"fieldname": "note_type",
			"label": _("Note Type"),
			"fieldtype": "Data",
			"width": 130,
		},
		{
			"fieldname": "chief_complaint",
			"label": _("Chief Complaint"),
			"fieldtype": "Data",
			"width": 200,
		},
		{
			"fieldname": "provisional_diagnosis",
			"label": _("Provisional Diagnosis"),
			"fieldtype": "Data",
			"width": 200,
		},
		{
			"fieldname": "inpatient_record",
			"label": _("Inpatient Record"),
			"fieldtype": "Link",
			"options": "Inpatient Record",
			"width": 140,
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
			"width": 100,
		},
		{
			"fieldname": "bed",
			"label": _("Bed"),
			"fieldtype": "Data",
			"width": 100,
		},
		{
			"fieldname": "docstatus",
			"label": _("Status"),
			"fieldtype": "Data",
			"width": 80,
		},
	]


def _get_data(filters: dict) -> list[dict]:
	pe = frappe.qb.DocType("Patient Encounter")
	ir = frappe.qb.DocType("Inpatient Record")

	query = (
		frappe.qb.from_(pe)
		.left_join(ir)
		.on(pe.custom_linked_inpatient_record == ir.name)
		.select(
			pe.name.as_("encounter"),
			pe.encounter_date,
			pe.patient,
			pe.patient_name,
			pe.practitioner,
			pe.practitioner_name,
			pe.custom_ipd_note_type.as_("note_type"),
			pe.custom_chief_complaint_text.as_("chief_complaint"),
			pe.custom_provisional_diagnosis_text.as_("provisional_diagnosis"),
			pe.custom_linked_inpatient_record.as_("inpatient_record"),
			ir.custom_current_ward.as_("ward"),
			ir.custom_current_room.as_("room"),
			ir.custom_current_bed.as_("bed"),
			pe.docstatus,
		)
		.where(pe.custom_ipd_note_type.isnotnull())
		.where(pe.custom_ipd_note_type != "")
		.where(pe.docstatus != 2)
		.orderby(pe.encounter_date, order=frappe.qb.desc)
		.orderby(pe.creation, order=frappe.qb.desc)
	)

	if filters.get("company"):
		query = query.where(pe.company == filters["company"])
	if filters.get("patient"):
		query = query.where(pe.patient == filters["patient"])
	if filters.get("practitioner"):
		query = query.where(pe.practitioner == filters["practitioner"])
	if filters.get("medical_department"):
		query = query.where(pe.medical_department == filters["medical_department"])
	if filters.get("note_type"):
		query = query.where(pe.custom_ipd_note_type == filters["note_type"])
	if filters.get("ward"):
		query = query.where(ir.custom_current_ward == filters["ward"])
	if filters.get("from_date"):
		query = query.where(pe.encounter_date >= getdate(filters["from_date"]))
	if filters.get("to_date"):
		query = query.where(pe.encounter_date <= getdate(filters["to_date"]))

	rows = query.run(as_dict=True)

	status_map = {0: "Draft", 1: "Submitted"}
	for row in rows:
		row["docstatus"] = status_map.get(row.get("docstatus"), "")

	return rows
