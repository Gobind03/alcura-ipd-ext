"""Bed Occupancy Dashboard — Script Report (US-K1).

Aggregate occupancy statistics by ward or room type with KPI summary
cards, average LOS, bed turnaround, and a chart of occupancy % by ward.
"""

from __future__ import annotations

from alcura_ipd_ext.services.occupancy_metrics_service import (
	get_avg_los_by_ward,
	get_bed_turnaround_by_ward,
	get_critical_care_summary,
	get_overall_summary,
	get_room_type_occupancy_summary,
	get_ward_occupancy_summary,
)


def execute(filters: dict | None = None):
	filters = filters or {}
	group_by = filters.get("group_by", "Ward")

	if group_by == "Room Type":
		columns = _get_room_type_columns()
		data = _get_room_type_data(filters)
	else:
		columns = _get_ward_columns()
		data = _get_ward_data(filters)

	chart = _get_chart(data, group_by)
	summary = _get_report_summary(filters)

	return columns, data, None, chart, summary


# ── ward view ───────────────────────────────────────────────────────


def _get_ward_columns() -> list[dict]:
	return [
		{"fieldname": "ward", "label": "Ward", "fieldtype": "Link", "options": "Hospital Ward", "width": 160},
		{"fieldname": "ward_name", "label": "Ward Name", "fieldtype": "Data", "width": 140},
		{"fieldname": "ward_classification", "label": "Classification", "fieldtype": "Data", "width": 100},
		{"fieldname": "total_beds", "label": "Total", "fieldtype": "Int", "width": 70},
		{"fieldname": "occupied", "label": "Occupied", "fieldtype": "Int", "width": 80},
		{"fieldname": "vacant", "label": "Vacant", "fieldtype": "Int", "width": 70},
		{"fieldname": "reserved", "label": "Reserved", "fieldtype": "Int", "width": 80},
		{"fieldname": "blocked", "label": "Blocked", "fieldtype": "Int", "width": 70},
		{"fieldname": "cleaning", "label": "Cleaning", "fieldtype": "Int", "width": 80},
		{"fieldname": "maintenance", "label": "Maintenance", "fieldtype": "Int", "width": 90},
		{"fieldname": "occupancy_pct", "label": "Occupancy %", "fieldtype": "Percent", "width": 100},
		{"fieldname": "avg_los", "label": "Avg LOS (days)", "fieldtype": "Float", "precision": 1, "width": 110},
		{"fieldname": "avg_turnaround", "label": "Avg Turnaround (min)", "fieldtype": "Float", "precision": 1, "width": 140},
	]


def _get_ward_data(filters: dict) -> list[dict]:
	rows = get_ward_occupancy_summary(filters)
	los_map = get_avg_los_by_ward(filters)
	tat_map = get_bed_turnaround_by_ward(filters)

	for row in rows:
		ward = row["ward"]
		row["avg_los"] = los_map.get(ward, 0.0)
		row["avg_turnaround"] = tat_map.get(ward, 0.0)

	return rows


# ── room type view ──────────────────────────────────────────────────


def _get_room_type_columns() -> list[dict]:
	return [
		{"fieldname": "room_type", "label": "Room Type", "fieldtype": "Link", "options": "Healthcare Service Unit Type", "width": 180},
		{"fieldname": "total_beds", "label": "Total", "fieldtype": "Int", "width": 70},
		{"fieldname": "occupied", "label": "Occupied", "fieldtype": "Int", "width": 80},
		{"fieldname": "vacant", "label": "Vacant", "fieldtype": "Int", "width": 70},
		{"fieldname": "reserved", "label": "Reserved", "fieldtype": "Int", "width": 80},
		{"fieldname": "blocked", "label": "Blocked", "fieldtype": "Int", "width": 70},
		{"fieldname": "cleaning", "label": "Cleaning", "fieldtype": "Int", "width": 80},
		{"fieldname": "maintenance", "label": "Maintenance", "fieldtype": "Int", "width": 90},
		{"fieldname": "occupancy_pct", "label": "Occupancy %", "fieldtype": "Percent", "width": 100},
	]


def _get_room_type_data(filters: dict) -> list[dict]:
	return get_room_type_occupancy_summary(filters)


# ── chart ───────────────────────────────────────────────────────────


def _get_chart(data: list[dict], group_by: str) -> dict | None:
	if not data:
		return None

	label_key = "ward_name" if group_by == "Ward" else "room_type"
	labels = [row.get(label_key) or row.get("ward") or row.get("room_type") or "" for row in data]
	occupancy = [row.get("occupancy_pct", 0) for row in data]

	return {
		"data": {
			"labels": labels,
			"datasets": [
				{"name": "Occupancy %", "values": occupancy},
			],
		},
		"type": "bar",
		"colors": ["#7cd6fd"],
		"barOptions": {"stacked": False},
	}


# ── summary cards ───────────────────────────────────────────────────


def _get_report_summary(filters: dict) -> list[dict]:
	overall = get_overall_summary(filters)
	icu = get_critical_care_summary(filters)
	los_map = get_avg_los_by_ward(filters)
	tat_map = get_bed_turnaround_by_ward(filters)

	avg_los_all = round(
		sum(los_map.values()) / len(los_map), 1
	) if los_map else 0.0

	avg_tat_all = round(
		sum(tat_map.values()) / len(tat_map), 1
	) if tat_map else 0.0

	return [
		{
			"value": overall["total"],
			"indicator": "Blue",
			"label": "Total Beds",
			"datatype": "Int",
		},
		{
			"value": overall["occupancy_pct"],
			"indicator": "Red" if overall["occupancy_pct"] > 90 else (
				"Orange" if overall["occupancy_pct"] > 70 else "Green"
			),
			"label": "Overall Occupancy %",
			"datatype": "Percent",
		},
		{
			"value": icu["occupancy_pct"],
			"indicator": "Red" if icu["occupancy_pct"] > 90 else (
				"Orange" if icu["occupancy_pct"] > 70 else "Green"
			),
			"label": "ICU Occupancy %",
			"datatype": "Percent",
		},
		{
			"value": avg_los_all,
			"indicator": "Blue",
			"label": "Avg LOS (days)",
			"datatype": "Float",
		},
		{
			"value": avg_tat_all,
			"indicator": "Blue",
			"label": "Avg Turnaround (min)",
			"datatype": "Float",
		},
	]
