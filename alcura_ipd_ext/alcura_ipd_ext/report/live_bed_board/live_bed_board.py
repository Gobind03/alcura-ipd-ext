"""Server-side entry point for the Live Bed Board Script Report."""

from __future__ import annotations

from alcura_ipd_ext.services.bed_availability_service import (
	get_available_beds,
	get_bed_board_summary,
)


def execute(filters: dict | None = None):
	filters = filters or {}
	columns = _get_columns(filters)
	data = get_available_beds(filters)
	summary = _get_report_summary(filters)

	return columns, data, None, None, summary


def _get_columns(filters: dict) -> list[dict]:
	"""Build column definitions. Payer columns appear only when a payer filter is active."""
	columns = [
		{
			"fieldname": "bed",
			"label": "Bed",
			"fieldtype": "Link",
			"options": "Hospital Bed",
			"width": 140,
		},
		{
			"fieldname": "bed_label",
			"label": "Label",
			"fieldtype": "Data",
			"width": 90,
		},
		{
			"fieldname": "room",
			"label": "Room",
			"fieldtype": "Link",
			"options": "Hospital Room",
			"width": 130,
		},
		{
			"fieldname": "ward",
			"label": "Ward",
			"fieldtype": "Link",
			"options": "Hospital Ward",
			"width": 140,
		},
		{
			"fieldname": "room_type",
			"label": "Room Type",
			"fieldtype": "Link",
			"options": "Healthcare Service Unit Type",
			"width": 140,
		},
		{
			"fieldname": "floor",
			"label": "Floor",
			"fieldtype": "Data",
			"width": 60,
		},
		{
			"fieldname": "availability",
			"label": "Availability",
			"fieldtype": "Data",
			"width": 110,
		},
		{
			"fieldname": "housekeeping_status",
			"label": "Housekeeping",
			"fieldtype": "Data",
			"width": 100,
		},
		{
			"fieldname": "gender_restriction",
			"label": "Gender",
			"fieldtype": "Data",
			"width": 90,
		},
		{
			"fieldname": "maintenance_hold",
			"label": "Maintenance",
			"fieldtype": "Check",
			"width": 50,
		},
		{
			"fieldname": "infection_block",
			"label": "Infection",
			"fieldtype": "Check",
			"width": 50,
		},
		{
			"fieldname": "equipment_notes",
			"label": "Equipment",
			"fieldtype": "Data",
			"width": 120,
		},
	]

	if filters.get("payer_type"):
		columns.extend([
			{
				"fieldname": "daily_rate",
				"label": "Daily Rate",
				"fieldtype": "Currency",
				"width": 100,
			},
			{
				"fieldname": "payer_eligible",
				"label": "Payer Eligible",
				"fieldtype": "Data",
				"width": 80,
			},
		])

	columns.extend([
		{
			"fieldname": "ward_classification",
			"label": "Ward Class",
			"fieldtype": "Data",
			"width": 100,
		},
		{
			"fieldname": "medical_department",
			"label": "Specialty",
			"fieldtype": "Link",
			"options": "Medical Department",
			"width": 120,
		},
	])

	return columns


def _get_report_summary(filters: dict) -> list[dict]:
	"""Build the report summary cards shown above the data table."""
	summary = get_bed_board_summary(filters)
	return [
		{
			"value": summary["total"],
			"indicator": "Blue",
			"label": "Total Beds",
			"datatype": "Int",
		},
		{
			"value": summary["available"],
			"indicator": "Green",
			"label": "Available",
			"datatype": "Int",
		},
		{
			"value": summary["occupied"],
			"indicator": "Red",
			"label": "Occupied",
			"datatype": "Int",
		},
		{
			"value": summary["blocked"],
			"indicator": "Orange",
			"label": "Blocked",
			"datatype": "Int",
		},
	]
