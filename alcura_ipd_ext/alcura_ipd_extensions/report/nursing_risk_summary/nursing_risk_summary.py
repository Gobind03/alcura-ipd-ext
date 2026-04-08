"""Nursing Risk Summary — Script Report.

Shows all admitted patients with their nursing risk indicators (fall risk,
pressure injury risk, nutrition risk, allergy alert). Filters by company,
ward, risk type, minimum risk level, and consultant.
"""

from __future__ import annotations

import frappe
from frappe import _


# Risk level ordering (higher index = higher severity)
_FALL_ORDER = {"Low": 1, "Moderate": 2, "High": 3}
_PRESSURE_ORDER = {"No Risk": 0, "Low": 1, "Moderate": 2, "High": 3, "Very High": 4}
_NUTRITION_ORDER = {"Low": 1, "Medium": 2, "High": 3}

# Minimum level filter mapping
_MIN_LEVEL_THRESHOLD = {
	"High": 3,
	"Moderate": 2,
	"Low": 1,
}


def execute(filters: dict | None = None) -> tuple[list[dict], list[dict]]:
	filters = filters or {}
	columns = _get_columns()
	data = _get_data(filters)
	return columns, data


def _get_columns() -> list[dict]:
	return [
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
			"fieldname": "inpatient_record",
			"label": _("Inpatient Record"),
			"fieldtype": "Link",
			"options": "Inpatient Record",
			"width": 140,
		},
		{
			"fieldname": "ward",
			"label": _("Ward"),
			"fieldtype": "Link",
			"options": "Hospital Ward",
			"width": 120,
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
			"fieldname": "consultant",
			"label": _("Consultant"),
			"fieldtype": "Link",
			"options": "Healthcare Practitioner",
			"width": 140,
		},
		{
			"fieldname": "fall_risk_level",
			"label": _("Fall Risk"),
			"fieldtype": "Data",
			"width": 100,
		},
		{
			"fieldname": "pressure_risk_level",
			"label": _("Pressure Risk"),
			"fieldtype": "Data",
			"width": 110,
		},
		{
			"fieldname": "nutrition_risk_level",
			"label": _("Nutrition Risk"),
			"fieldtype": "Data",
			"width": 110,
		},
		{
			"fieldname": "allergy_alert",
			"label": _("Allergy"),
			"fieldtype": "Check",
			"width": 80,
		},
		{
			"fieldname": "allergy_summary",
			"label": _("Allergy Details"),
			"fieldtype": "Data",
			"width": 160,
		},
		{
			"fieldname": "updated_on",
			"label": _("Last Updated"),
			"fieldtype": "Datetime",
			"width": 140,
		},
	]


def _get_data(filters: dict) -> list[dict]:
	conditions = {"status": "Admitted"}

	if filters.get("company"):
		conditions["company"] = filters["company"]
	if filters.get("ward"):
		conditions["custom_current_ward"] = filters["ward"]
	if filters.get("consultant"):
		conditions["primary_practitioner"] = filters["consultant"]

	records = frappe.get_all(
		"Inpatient Record",
		filters=conditions,
		fields=[
			"name",
			"patient",
			"patient_name",
			"primary_practitioner",
			"custom_current_ward",
			"custom_current_room",
			"custom_current_bed",
			"custom_fall_risk_level",
			"custom_pressure_risk_level",
			"custom_nutrition_risk_level",
			"custom_allergy_alert",
			"custom_allergy_summary",
			"custom_risk_flags_updated_on",
		],
		order_by="custom_current_ward asc, custom_current_bed asc",
	)

	data = []
	for r in records:
		row = {
			"patient": r.patient,
			"patient_name": r.patient_name,
			"inpatient_record": r.name,
			"ward": r.custom_current_ward or "",
			"room": r.custom_current_room or "",
			"bed": r.custom_current_bed or "",
			"consultant": r.primary_practitioner or "",
			"fall_risk_level": r.custom_fall_risk_level or "",
			"pressure_risk_level": r.custom_pressure_risk_level or "",
			"nutrition_risk_level": r.custom_nutrition_risk_level or "",
			"allergy_alert": r.custom_allergy_alert or 0,
			"allergy_summary": r.custom_allergy_summary or "",
			"updated_on": r.custom_risk_flags_updated_on,
		}

		if not _passes_risk_filter(row, filters):
			continue

		data.append(row)

	return data


def _passes_risk_filter(row: dict, filters: dict) -> bool:
	"""Apply risk-type and minimum-level filters."""
	risk_type = filters.get("risk_type")
	min_level = filters.get("risk_level")

	if not risk_type and not min_level:
		return True

	if risk_type == "Allergy":
		return bool(row.get("allergy_alert"))

	threshold = _MIN_LEVEL_THRESHOLD.get(min_level, 0)

	if risk_type == "Fall Risk":
		return _FALL_ORDER.get(row.get("fall_risk_level", ""), 0) >= threshold
	if risk_type == "Pressure Injury":
		return _PRESSURE_ORDER.get(row.get("pressure_risk_level", ""), 0) >= threshold
	if risk_type == "Nutrition":
		return _NUTRITION_ORDER.get(row.get("nutrition_risk_level", ""), 0) >= threshold

	# No specific risk type but min_level specified — match any risk at threshold
	if min_level and not risk_type:
		return (
			_FALL_ORDER.get(row.get("fall_risk_level", ""), 0) >= threshold
			or _PRESSURE_ORDER.get(row.get("pressure_risk_level", ""), 0) >= threshold
			or _NUTRITION_ORDER.get(row.get("nutrition_risk_level", ""), 0) >= threshold
			or bool(row.get("allergy_alert"))
		)

	return True
