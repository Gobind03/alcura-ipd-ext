"""Occupancy metrics service for bed occupancy dashboard and KPI consumers.

Provides aggregate occupancy statistics grouped by ward or room type,
average length of stay for admitted patients, and bed turnaround metrics
from housekeeping tasks.
"""

from __future__ import annotations

import frappe
from frappe.utils import getdate, today


def get_ward_occupancy_summary(filters: dict | None = None) -> list[dict]:
	"""Aggregate bed counts grouped by ward.

	Returns one row per active ward with total, occupied, vacant, reserved,
	blocked counts and occupancy percentage.
	"""
	filters = filters or {}
	conditions, params = _base_bed_conditions(filters)

	where = " AND ".join(conditions) if conditions else "1=1"

	rows = frappe.db.sql(
		f"""
		SELECT
			ward.name AS ward,
			ward.ward_name,
			ward.ward_classification,
			ward.is_critical_care,
			ward.branch,
			COUNT(*) AS total_beds,
			SUM(CASE WHEN bed.occupancy_status = 'Occupied' THEN 1 ELSE 0 END) AS occupied,
			SUM(CASE WHEN bed.occupancy_status = 'Vacant'
				AND bed.housekeeping_status = 'Clean'
				AND bed.maintenance_hold = 0
				AND bed.infection_block = 0
			THEN 1 ELSE 0 END) AS vacant,
			SUM(CASE WHEN bed.occupancy_status = 'Reserved' THEN 1 ELSE 0 END) AS reserved,
			SUM(CASE WHEN bed.maintenance_hold = 1
				OR bed.infection_block = 1
				OR (bed.occupancy_status = 'Vacant' AND bed.housekeeping_status != 'Clean')
			THEN 1 ELSE 0 END) AS blocked,
			SUM(CASE WHEN bed.occupancy_status = 'Vacant'
				AND bed.housekeeping_status = 'In Progress'
			THEN 1 ELSE 0 END) AS cleaning,
			SUM(CASE WHEN bed.maintenance_hold = 1 THEN 1 ELSE 0 END) AS maintenance
		FROM `tabHospital Bed` bed
		INNER JOIN `tabHospital Room` room ON bed.hospital_room = room.name
		INNER JOIN `tabHospital Ward` ward ON bed.hospital_ward = ward.name
		WHERE {where}
		GROUP BY ward.name
		ORDER BY ward.ward_name
		""",
		params,
		as_dict=True,
	)

	for row in rows:
		total = int(row.total_beds or 0)
		occupied = int(row.occupied or 0)
		row["occupancy_pct"] = round((occupied / total) * 100, 1) if total else 0.0

	return rows


def get_room_type_occupancy_summary(filters: dict | None = None) -> list[dict]:
	"""Aggregate bed counts grouped by room type (Healthcare Service Unit Type)."""
	filters = filters or {}
	conditions, params = _base_bed_conditions(filters)

	where = " AND ".join(conditions) if conditions else "1=1"

	rows = frappe.db.sql(
		f"""
		SELECT
			bed.service_unit_type AS room_type,
			COUNT(*) AS total_beds,
			SUM(CASE WHEN bed.occupancy_status = 'Occupied' THEN 1 ELSE 0 END) AS occupied,
			SUM(CASE WHEN bed.occupancy_status = 'Vacant'
				AND bed.housekeeping_status = 'Clean'
				AND bed.maintenance_hold = 0
				AND bed.infection_block = 0
			THEN 1 ELSE 0 END) AS vacant,
			SUM(CASE WHEN bed.occupancy_status = 'Reserved' THEN 1 ELSE 0 END) AS reserved,
			SUM(CASE WHEN bed.maintenance_hold = 1
				OR bed.infection_block = 1
				OR (bed.occupancy_status = 'Vacant' AND bed.housekeeping_status != 'Clean')
			THEN 1 ELSE 0 END) AS blocked,
			SUM(CASE WHEN bed.occupancy_status = 'Vacant'
				AND bed.housekeeping_status = 'In Progress'
			THEN 1 ELSE 0 END) AS cleaning,
			SUM(CASE WHEN bed.maintenance_hold = 1 THEN 1 ELSE 0 END) AS maintenance
		FROM `tabHospital Bed` bed
		INNER JOIN `tabHospital Room` room ON bed.hospital_room = room.name
		INNER JOIN `tabHospital Ward` ward ON bed.hospital_ward = ward.name
		WHERE {where}
		GROUP BY bed.service_unit_type
		ORDER BY bed.service_unit_type
		""",
		params,
		as_dict=True,
	)

	for row in rows:
		total = int(row.total_beds or 0)
		occupied = int(row.occupied or 0)
		row["occupancy_pct"] = round((occupied / total) * 100, 1) if total else 0.0

	return rows


def get_critical_care_summary(filters: dict | None = None) -> dict:
	"""Return aggregate occupancy for critical care wards only."""
	filters = filters or {}
	conditions, params = _base_bed_conditions(filters)
	conditions.append("ward.is_critical_care = 1")

	where = " AND ".join(conditions)

	row = frappe.db.sql(
		f"""
		SELECT
			COUNT(*) AS total_beds,
			SUM(CASE WHEN bed.occupancy_status = 'Occupied' THEN 1 ELSE 0 END) AS occupied
		FROM `tabHospital Bed` bed
		INNER JOIN `tabHospital Room` room ON bed.hospital_room = room.name
		INNER JOIN `tabHospital Ward` ward ON bed.hospital_ward = ward.name
		WHERE {where}
		""",
		params,
		as_dict=True,
	)

	if row:
		total = int(row[0].total_beds or 0)
		occupied = int(row[0].occupied or 0)
		return {
			"total": total,
			"occupied": occupied,
			"occupancy_pct": round((occupied / total) * 100, 1) if total else 0.0,
		}
	return {"total": 0, "occupied": 0, "occupancy_pct": 0.0}


def get_avg_los_by_ward(filters: dict | None = None) -> dict[str, float]:
	"""Average length of stay (days) for currently admitted patients, keyed by ward.

	LOS = today - scheduled_date + 1 for each admitted IR.
	"""
	filters = filters or {}
	conditions = ["ir.status = 'Admitted'"]
	params: dict = {}

	ref_date = getdate(filters.get("date") or today())
	params["ref_date"] = str(ref_date)

	if filters.get("company"):
		conditions.append("ir.company = %(company)s")
		params["company"] = filters["company"]

	if filters.get("ward"):
		conditions.append("ir.custom_current_ward = %(ward)s")
		params["ward"] = filters["ward"]

	where = " AND ".join(conditions)

	rows = frappe.db.sql(
		f"""
		SELECT
			ir.custom_current_ward AS ward,
			AVG(DATEDIFF(%(ref_date)s, ir.scheduled_date) + 1) AS avg_los
		FROM `tabInpatient Record` ir
		WHERE {where}
			AND ir.custom_current_ward IS NOT NULL
			AND ir.custom_current_ward != ''
			AND ir.scheduled_date IS NOT NULL
		GROUP BY ir.custom_current_ward
		""",
		params,
		as_dict=True,
	)

	return {r["ward"]: round(float(r["avg_los"] or 0), 1) for r in rows}


def get_bed_turnaround_by_ward(filters: dict | None = None) -> dict[str, float]:
	"""Average housekeeping turnaround (minutes) for completed tasks, keyed by ward."""
	filters = filters or {}
	conditions = [
		"task.status = 'Completed'",
		"task.turnaround_minutes IS NOT NULL",
	]
	params: dict = {}

	if filters.get("from_date"):
		conditions.append("task.completed_on >= %(from_date)s")
		params["from_date"] = filters["from_date"]

	if filters.get("to_date"):
		conditions.append("task.completed_on <= %(to_date)s")
		params["to_date"] = filters["to_date"]

	if filters.get("ward"):
		conditions.append("task.hospital_ward = %(ward)s")
		params["ward"] = filters["ward"]

	if filters.get("company"):
		conditions.append("task.company = %(company)s")
		params["company"] = filters["company"]

	where = " AND ".join(conditions)

	rows = frappe.db.sql(
		f"""
		SELECT
			task.hospital_ward AS ward,
			AVG(task.turnaround_minutes) AS avg_tat
		FROM `tabBed Housekeeping Task` task
		WHERE {where}
		GROUP BY task.hospital_ward
		""",
		params,
		as_dict=True,
	)

	return {r["ward"]: round(float(r["avg_tat"] or 0), 1) for r in rows}


def get_overall_summary(filters: dict | None = None) -> dict:
	"""Return hospital-wide aggregate occupancy for summary cards."""
	filters = filters or {}
	conditions, params = _base_bed_conditions(filters)

	where = " AND ".join(conditions) if conditions else "1=1"

	row = frappe.db.sql(
		f"""
		SELECT
			COUNT(*) AS total,
			SUM(CASE WHEN bed.occupancy_status = 'Occupied' THEN 1 ELSE 0 END) AS occupied,
			SUM(CASE WHEN bed.occupancy_status = 'Vacant'
				AND bed.housekeeping_status = 'Clean'
				AND bed.maintenance_hold = 0
				AND bed.infection_block = 0
			THEN 1 ELSE 0 END) AS available,
			SUM(CASE WHEN bed.occupancy_status = 'Reserved' THEN 1 ELSE 0 END) AS reserved,
			SUM(CASE WHEN bed.maintenance_hold = 1
				OR bed.infection_block = 1
				OR (bed.occupancy_status = 'Vacant' AND bed.housekeeping_status != 'Clean')
			THEN 1 ELSE 0 END) AS blocked
		FROM `tabHospital Bed` bed
		INNER JOIN `tabHospital Room` room ON bed.hospital_room = room.name
		INNER JOIN `tabHospital Ward` ward ON bed.hospital_ward = ward.name
		WHERE {where}
		""",
		params,
		as_dict=True,
	)

	if row:
		total = int(row[0].total or 0)
		occupied = int(row[0].occupied or 0)
		return {
			"total": total,
			"occupied": occupied,
			"available": int(row[0].available or 0),
			"reserved": int(row[0].reserved or 0),
			"blocked": int(row[0].blocked or 0),
			"occupancy_pct": round((occupied / total) * 100, 1) if total else 0.0,
		}
	return {
		"total": 0, "occupied": 0, "available": 0,
		"reserved": 0, "blocked": 0, "occupancy_pct": 0.0,
	}


# ── internal helpers ────────────────────────────────────────────────


def _base_bed_conditions(filters: dict) -> tuple[list[str], dict]:
	"""Common WHERE clauses for bed queries."""
	conditions = [
		"bed.is_active = 1",
		"room.is_active = 1",
		"ward.is_active = 1",
	]
	params: dict = {}

	if filters.get("company"):
		conditions.append("bed.company = %(company)s")
		params["company"] = filters["company"]

	if filters.get("branch"):
		conditions.append("ward.branch = %(branch)s")
		params["branch"] = filters["branch"]

	if filters.get("ward"):
		conditions.append("bed.hospital_ward = %(ward)s")
		params["ward"] = filters["ward"]

	if filters.get("room_type"):
		conditions.append("bed.service_unit_type = %(room_type)s")
		params["room_type"] = filters["room_type"]

	if filters.get("critical_care_only"):
		conditions.append("ward.is_critical_care = 1")

	return conditions, params
