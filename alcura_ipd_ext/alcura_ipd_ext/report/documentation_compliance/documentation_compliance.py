"""Documentation Compliance Report — Script Report (US-L2).

Shows which admitted patients are missing doctor notes, nursing charts,
intake assessments, or discharge summaries. Highlights overdue
documentation and provides a per-patient compliance score.
"""

from __future__ import annotations

import frappe
from frappe import _


def execute(filters: dict | None = None) -> tuple:
	filters = filters or {}
	columns = _get_columns()
	data = _get_data(filters)
	report_summary = _get_report_summary(data)
	chart = _get_chart(data)
	return columns, data, None, chart, report_summary


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
			"width": 150,
		},
		{
			"fieldname": "ward",
			"label": _("Ward"),
			"fieldtype": "Data",
			"width": 100,
		},
		{
			"fieldname": "bed",
			"label": _("Bed"),
			"fieldtype": "Data",
			"width": 80,
		},
		{
			"fieldname": "practitioner_name",
			"label": _("Doctor"),
			"fieldtype": "Data",
			"width": 140,
		},
		{
			"fieldname": "days_admitted",
			"label": _("Days"),
			"fieldtype": "Int",
			"width": 60,
		},
		{
			"fieldname": "has_admission_note",
			"label": _("Adm Note"),
			"fieldtype": "Check",
			"width": 80,
		},
		{
			"fieldname": "progress_note_gap",
			"label": _("Note Gap (d)"),
			"fieldtype": "Int",
			"width": 90,
		},
		{
			"fieldname": "intake_complete",
			"label": _("Intake"),
			"fieldtype": "Check",
			"width": 70,
		},
		{
			"fieldname": "nursing_charts_ok",
			"label": _("Charts OK"),
			"fieldtype": "Check",
			"width": 80,
		},
		{
			"fieldname": "overdue_charts",
			"label": _("Overdue"),
			"fieldtype": "Int",
			"width": 70,
		},
		{
			"fieldname": "has_discharge_summary",
			"label": _("Disch Summary"),
			"fieldtype": "Check",
			"width": 100,
		},
		{
			"fieldname": "compliance_score",
			"label": _("Score %"),
			"fieldtype": "Percent",
			"width": 90,
		},
	]


def _get_data(filters: dict) -> list[dict]:
	from alcura_ipd_ext.services.documentation_compliance_service import (
		get_documentation_compliance,
	)

	return get_documentation_compliance(
		company=filters.get("company"),
		ward=filters.get("ward"),
		practitioner=filters.get("practitioner"),
		medical_department=filters.get("medical_department"),
		status=filters.get("status") or "Admitted",
	)


def _get_report_summary(data: list[dict]) -> list[dict]:
	if not data:
		return []

	total = len(data)
	missing_adm = sum(1 for r in data if not r.get("has_admission_note"))
	overdue_notes = sum(1 for r in data if (r.get("progress_note_gap") or 0) > 1)
	missing_intake = sum(1 for r in data if not r.get("intake_complete"))
	charts_overdue = sum(1 for r in data if not r.get("nursing_charts_ok"))

	scores = [r.get("compliance_score", 0) for r in data]
	avg_score = round(sum(scores) / total, 1) if total else 0

	return [
		{"value": total, "label": _("Total Patients"), "datatype": "Int"},
		{
			"value": avg_score,
			"label": _("Avg Compliance"),
			"datatype": "Percent",
			"indicator": "red" if avg_score < 50 else ("orange" if avg_score < 75 else "green"),
		},
		{
			"value": missing_adm,
			"label": _("Missing Adm Note"),
			"datatype": "Int",
			"indicator": "red" if missing_adm else "green",
		},
		{
			"value": overdue_notes,
			"label": _("Overdue Progress Notes"),
			"datatype": "Int",
			"indicator": "orange" if overdue_notes else "green",
		},
		{
			"value": missing_intake,
			"label": _("Missing Intake"),
			"datatype": "Int",
			"indicator": "red" if missing_intake else "green",
		},
		{
			"value": charts_overdue,
			"label": _("Charts Overdue"),
			"datatype": "Int",
			"indicator": "orange" if charts_overdue else "green",
		},
	]


def _get_chart(data: list[dict]) -> dict | None:
	if not data:
		return None

	buckets = {"100%": 0, "75-99%": 0, "50-74%": 0, "<50%": 0}
	for row in data:
		score = row.get("compliance_score", 0)
		if score >= 100:
			buckets["100%"] += 1
		elif score >= 75:
			buckets["75-99%"] += 1
		elif score >= 50:
			buckets["50-74%"] += 1
		else:
			buckets["<50%"] += 1

	return {
		"data": {
			"labels": list(buckets.keys()),
			"datasets": [{"name": _("Patients"), "values": list(buckets.values())}],
		},
		"type": "bar",
		"colors": ["#36a2eb"],
	}
