"""Bed availability service for the Live Bed Board and downstream consumers.

Computes real-time bed availability by joining Hospital Bed, Hospital Room,
and Hospital Ward, applying IPD Bed Policy exclusions, user-supplied filters,
and optional payer-eligibility enrichment via the tariff service.

All heavy lifting happens in SQL; payer eligibility is a lightweight
post-filter that groups by room type to avoid N+1 tariff lookups.
"""

from __future__ import annotations

import frappe
from frappe.utils import today

from alcura_ipd_ext.alcura_ipd_ext.doctype.ipd_bed_policy.ipd_bed_policy import (
	get_policy,
)

# ── public API ──────────────────────────────────────────────────────


def get_available_beds(filters: dict | None = None) -> list[dict]:
	"""Return beds matching the given filters, enriched with tariff info.

	Args:
		filters: dict with optional keys — ward, room_type, floor,
			critical_care_only, gender, isolation_only, show_unavailable,
			payer_type, payer, company.

	Returns:
		List of dicts, one per bed, sorted by ward → room → bed.
	"""
	filters = filters or {}
	policy = _get_effective_policy()

	sql, params = _build_bed_query(filters, policy)
	beds = frappe.db.sql(sql, params, as_dict=True)

	_compute_availability_label(beds)

	payer_type = filters.get("payer_type")
	payer = filters.get("payer")
	if payer_type:
		beds = _apply_payer_eligibility(beds, payer_type, payer, policy, filters)

	return beds


def get_bed_board_summary(filters: dict | None = None) -> dict:
	"""Return aggregate bed counts for the bed board header.

	Returns dict with keys: total, available, occupied, blocked.
	"""
	filters = filters or {}
	policy = _get_effective_policy()

	base_conditions, params = _base_conditions()
	_append_user_filters(base_conditions, params, filters, policy, include_availability=False)

	where = " AND ".join(base_conditions) if base_conditions else "1=1"

	sql = f"""
		SELECT
			COUNT(*) AS total,
			SUM(CASE WHEN bed.occupancy_status = 'Vacant'
				AND bed.housekeeping_status = 'Clean'
				AND bed.maintenance_hold = 0
				AND bed.infection_block = 0
			THEN 1 ELSE 0 END) AS available,
			SUM(CASE WHEN bed.occupancy_status = 'Occupied' THEN 1 ELSE 0 END) AS occupied,
			SUM(CASE WHEN bed.occupancy_status = 'Reserved' THEN 1 ELSE 0 END) AS reserved,
			SUM(CASE WHEN bed.maintenance_hold = 1
				OR bed.infection_block = 1
				OR (bed.occupancy_status = 'Vacant' AND bed.housekeeping_status != 'Clean')
			THEN 1 ELSE 0 END) AS blocked
		FROM `tabHospital Bed` bed
		INNER JOIN `tabHospital Room` room ON bed.hospital_room = room.name
		INNER JOIN `tabHospital Ward` ward ON bed.hospital_ward = ward.name
		WHERE {where}
	"""
	row = frappe.db.sql(sql, params, as_dict=True)
	if row:
		return {
			"total": int(row[0].total or 0),
			"available": int(row[0].available or 0),
			"occupied": int(row[0].occupied or 0),
			"reserved": int(row[0].reserved or 0),
			"blocked": int(row[0].blocked or 0),
		}
	return {"total": 0, "available": 0, "occupied": 0, "reserved": 0, "blocked": 0}


# ── internal helpers ────────────────────────────────────────────────


def _get_effective_policy() -> dict:
	return get_policy()


def _base_conditions() -> tuple[list[str], dict]:
	"""Return the always-on WHERE conditions and params dict."""
	conditions = [
		"bed.is_active = 1",
		"room.is_active = 1",
		"ward.is_active = 1",
	]
	return conditions, {}


def _build_bed_query(filters: dict, policy: dict) -> tuple[str, dict]:
	"""Construct the parameterized SQL for bed retrieval."""
	conditions, params = _base_conditions()

	_append_policy_exclusions(conditions, policy)
	_append_user_filters(conditions, params, filters, policy)

	where = " AND ".join(conditions)
	sql = f"""
		SELECT
			bed.name AS bed,
			bed.bed_number,
			bed.bed_label,
			bed.hospital_room AS room,
			bed.hospital_ward AS ward,
			bed.service_unit_type AS room_type,
			bed.occupancy_status,
			bed.housekeeping_status,
			bed.maintenance_hold,
			bed.infection_block,
			bed.gender_restriction,
			bed.equipment_notes,
			room.room_number,
			room.room_name,
			room.floor,
			room.wing,
			room.is_ac,
			ward.ward_name,
			ward.ward_code,
			ward.ward_classification,
			ward.medical_department,
			ward.gender_restriction AS ward_gender,
			ward.is_critical_care,
			ward.supports_isolation,
			ward.branch,
			ward.building,
			ward.floor AS ward_floor
		FROM `tabHospital Bed` bed
		INNER JOIN `tabHospital Room` room ON bed.hospital_room = room.name
		INNER JOIN `tabHospital Ward` ward ON bed.hospital_ward = ward.name
		WHERE {where}
		ORDER BY ward.ward_name, room.room_number, bed.bed_number
	"""
	return sql, params


def _append_policy_exclusions(conditions: list[str], policy: dict) -> None:
	"""Add WHERE clauses based on IPD Bed Policy exclusion settings."""
	if policy.get("exclude_dirty_beds"):
		conditions.append(
			"NOT (bed.occupancy_status = 'Vacant' AND bed.housekeeping_status = 'Dirty')"
		)
	if policy.get("exclude_cleaning_beds"):
		conditions.append(
			"NOT (bed.occupancy_status = 'Vacant' AND bed.housekeeping_status = 'In Progress')"
		)
	if policy.get("exclude_maintenance_beds"):
		conditions.append("bed.maintenance_hold = 0")
	if policy.get("exclude_infection_blocked"):
		conditions.append("bed.infection_block = 0")


def _append_user_filters(
	conditions: list[str],
	params: dict,
	filters: dict,
	policy: dict,
	include_availability: bool = True,
) -> None:
	"""Add WHERE clauses from user-supplied report filters."""
	if filters.get("ward"):
		conditions.append("bed.hospital_ward = %(ward)s")
		params["ward"] = filters["ward"]

	if filters.get("room_type"):
		conditions.append("bed.service_unit_type = %(room_type)s")
		params["room_type"] = filters["room_type"]

	if filters.get("floor"):
		conditions.append("room.floor = %(floor)s")
		params["floor"] = filters["floor"]

	if filters.get("critical_care_only"):
		conditions.append("ward.is_critical_care = 1")

	if filters.get("isolation_only"):
		conditions.append("ward.supports_isolation = 1")

	if filters.get("company"):
		conditions.append("bed.company = %(company)s")
		params["company"] = filters["company"]

	# Gender filter: respect policy enforcement level
	gender = filters.get("gender")
	if gender and gender != "All":
		enforcement = policy.get("gender_enforcement", "Strict")
		if enforcement == "Strict":
			conditions.append(
				"bed.gender_restriction IN ('No Restriction', %(gender)s)"
			)
			params["gender"] = gender

	# Availability: default is to show only vacant beds
	if include_availability and not filters.get("show_unavailable"):
		conditions.append("bed.occupancy_status = 'Vacant'")


def _compute_availability_label(beds: list[dict]) -> None:
	"""Annotate each bed row with a human-readable availability label."""
	for bed in beds:
		if bed.get("occupancy_status") == "Occupied":
			bed["availability"] = "Occupied"
		elif bed.get("occupancy_status") == "Reserved":
			bed["availability"] = "Reserved"
		elif bed.get("maintenance_hold"):
			bed["availability"] = "Maintenance"
		elif bed.get("infection_block"):
			bed["availability"] = "Infection Block"
		elif bed.get("housekeeping_status") == "Dirty":
			bed["availability"] = "Dirty"
		elif bed.get("housekeeping_status") == "In Progress":
			bed["availability"] = "Cleaning"
		else:
			bed["availability"] = "Available"


def _apply_payer_eligibility(
	beds: list[dict],
	payer_type: str,
	payer: str | None,
	policy: dict,
	filters: dict,
) -> list[dict]:
	"""Enrich beds with tariff info and optionally filter by payer eligibility.

	Groups beds by room type to call resolve_tariff once per type (not per bed).
	"""
	from alcura_ipd_ext.services.tariff_service import resolve_tariff

	enforcement = policy.get("enforce_payer_eligibility", "Ignore")
	if enforcement == "Ignore":
		for bed in beds:
			bed["daily_rate"] = None
			bed["payer_eligible"] = ""
		return beds

	room_types = {bed["room_type"] for bed in beds if bed.get("room_type")}
	tariff_cache: dict[str, dict | None] = {}

	for rt in room_types:
		tariff_cache[rt] = resolve_tariff(
			room_type=rt,
			payer_type=payer_type,
			payer=payer,
			effective_date=today(),
			company=filters.get("company"),
			charge_type="Room Rent",
		)

	result = []
	for bed in beds:
		tariff = tariff_cache.get(bed.get("room_type"))
		if tariff and tariff.get("tariff_items"):
			bed["daily_rate"] = float(tariff["tariff_items"][0].get("rate", 0))
			bed["payer_eligible"] = "Yes"
		else:
			bed["daily_rate"] = 0.0
			bed["payer_eligible"] = "No"

		if enforcement == "Strict" and bed["payer_eligible"] == "No":
			continue
		result.append(bed)

	return result
