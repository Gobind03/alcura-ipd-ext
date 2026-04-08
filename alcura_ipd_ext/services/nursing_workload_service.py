"""Nursing workload by ward service (US-N1).

Aggregates patient census, acuity indicators, overdue charting,
medication administration load, and overdue protocol steps per ward
into a single summary suitable for staffing decisions.
"""

from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import now_datetime

from alcura_ipd_ext.services.charting_service import get_overdue_charts

# Workload score weights
_W_CENSUS = 1
_W_HIGH_ACUITY = 2
_W_OVERDUE_CHART = 3
_W_OVERDUE_MAR = 3
_W_OVERDUE_PROTOCOL = 2


def get_ward_workload(
	company: str | None = None,
	ward: str | None = None,
) -> list[dict]:
	"""Return per-ward nursing workload summary rows.

	Each row contains census, acuity, charting, MAR, and protocol
	metrics plus a composite workload score.
	"""
	wards = _get_active_wards(company=company, ward=ward)
	if not wards:
		return []

	ward_names = {w["name"]: w["ward_name"] for w in wards}
	ward_list = list(ward_names.keys())

	census_map = _count_census(ward_list)
	acuity_map = _count_high_acuity(ward_list)
	chart_stats = _count_chart_stats(ward_list)
	mar_stats = _count_mar_stats(ward_list)
	protocol_map = _count_overdue_protocol_steps(ward_list)

	rows = []
	for w in ward_list:
		census = census_map.get(w, 0)
		high_acuity = acuity_map.get(w, 0)
		active_charts = chart_stats.get(w, {}).get("active", 0)
		overdue_charts = chart_stats.get(w, {}).get("overdue", 0)
		pending_mar = mar_stats.get(w, {}).get("pending", 0)
		overdue_mar = mar_stats.get(w, {}).get("overdue", 0)
		overdue_protocol = protocol_map.get(w, 0)

		score = (
			census * _W_CENSUS
			+ high_acuity * _W_HIGH_ACUITY
			+ overdue_charts * _W_OVERDUE_CHART
			+ overdue_mar * _W_OVERDUE_MAR
			+ overdue_protocol * _W_OVERDUE_PROTOCOL
		)

		rows.append({
			"ward": w,
			"ward_name": ward_names.get(w, w),
			"patient_census": census,
			"high_acuity_count": high_acuity,
			"total_active_charts": active_charts,
			"overdue_charts": overdue_charts,
			"pending_mar_count": pending_mar,
			"overdue_mar_count": overdue_mar,
			"overdue_protocol_steps": overdue_protocol,
			"workload_score": score,
		})

	rows.sort(key=lambda r: r["workload_score"], reverse=True)
	return rows


def get_workload_totals(rows: list[dict]) -> dict:
	"""Aggregate totals across all ward rows."""
	totals: dict[str, int] = {
		"patient_census": 0,
		"high_acuity_count": 0,
		"overdue_charts": 0,
		"overdue_mar_count": 0,
		"overdue_protocol_steps": 0,
	}
	max_ward = ""
	max_score = -1

	for row in rows:
		for key in totals:
			totals[key] += row.get(key, 0)
		if row.get("workload_score", 0) > max_score:
			max_score = row["workload_score"]
			max_ward = row.get("ward_name") or row.get("ward", "")

	totals["highest_workload_ward"] = max_ward
	return totals


# ── internal helpers ────────────────────────────────────────────────


def _get_active_wards(
	company: str | None = None,
	ward: str | None = None,
) -> list[dict]:
	filters: dict = {"is_active": 1}
	if company:
		filters["company"] = company
	if ward:
		filters["name"] = ward

	return frappe.get_all(
		"Hospital Ward",
		filters=filters,
		fields=["name", "ward_name"],
		order_by="ward_name asc",
	)


def _count_census(ward_list: list[str]) -> dict[str, int]:
	"""Count admitted patients per ward."""
	rows = frappe.db.sql(
		"""
		SELECT custom_current_ward AS ward, COUNT(*) AS cnt
		FROM `tabInpatient Record`
		WHERE status = 'Admitted'
			AND custom_current_ward IN %(wards)s
		GROUP BY custom_current_ward
		""",
		{"wards": ward_list},
		as_dict=True,
	)
	return {r["ward"]: int(r["cnt"]) for r in rows}


def _count_high_acuity(ward_list: list[str]) -> dict[str, int]:
	"""Count patients with high-acuity risk flags per ward.

	High acuity: fall_risk = High OR pressure_risk in (High, Very High).
	"""
	rows = frappe.db.sql(
		"""
		SELECT custom_current_ward AS ward, COUNT(*) AS cnt
		FROM `tabInpatient Record`
		WHERE status = 'Admitted'
			AND custom_current_ward IN %(wards)s
			AND (
				custom_fall_risk_level = 'High'
				OR custom_pressure_risk_level IN ('High', 'Very High')
			)
		GROUP BY custom_current_ward
		""",
		{"wards": ward_list},
		as_dict=True,
	)
	return {r["ward"]: int(r["cnt"]) for r in rows}


def _count_chart_stats(ward_list: list[str]) -> dict[str, dict[str, int]]:
	"""Count active and overdue charts per ward.

	Active count via SQL; overdue reuses charting_service logic.
	"""
	active_rows = frappe.db.sql(
		"""
		SELECT ward, COUNT(*) AS cnt
		FROM `tabIPD Bedside Chart`
		WHERE status = 'Active' AND ward IN %(wards)s
		GROUP BY ward
		""",
		{"wards": ward_list},
		as_dict=True,
	)
	result: dict[str, dict[str, int]] = {}
	for r in active_rows:
		result[r["ward"]] = {"active": int(r["cnt"]), "overdue": 0}

	overdue_list = get_overdue_charts(grace_minutes=0)
	for chart in overdue_list:
		w = chart.get("ward")
		if w and w in ward_list:
			result.setdefault(w, {"active": 0, "overdue": 0})
			result[w]["overdue"] += 1

	return result


def _count_mar_stats(ward_list: list[str]) -> dict[str, dict[str, int]]:
	"""Count pending (Scheduled, not yet due) and overdue (Missed) MAR entries per ward."""
	now = now_datetime()

	pending_rows = frappe.db.sql(
		"""
		SELECT ward, COUNT(*) AS cnt
		FROM `tabIPD MAR Entry`
		WHERE status = 'Active'
			AND administration_status = 'Scheduled'
			AND scheduled_time > %(now)s
			AND ward IN %(wards)s
		GROUP BY ward
		""",
		{"now": now, "wards": ward_list},
		as_dict=True,
	)

	overdue_rows = frappe.db.sql(
		"""
		SELECT ward, COUNT(*) AS cnt
		FROM `tabIPD MAR Entry`
		WHERE status = 'Active'
			AND administration_status = 'Missed'
			AND ward IN %(wards)s
		GROUP BY ward
		""",
		{"wards": ward_list},
		as_dict=True,
	)

	result: dict[str, dict[str, int]] = {}
	for r in pending_rows:
		result.setdefault(r["ward"], {"pending": 0, "overdue": 0})
		result[r["ward"]]["pending"] = int(r["cnt"])

	for r in overdue_rows:
		result.setdefault(r["ward"], {"pending": 0, "overdue": 0})
		result[r["ward"]]["overdue"] = int(r["cnt"])

	return result


def _count_overdue_protocol_steps(ward_list: list[str]) -> dict[str, int]:
	"""Count overdue (Missed) protocol step trackers per ward.

	Joins Active Protocol Bundle -> Inpatient Record for ward.
	"""
	rows = frappe.db.sql(
		"""
		SELECT ir.custom_current_ward AS ward, COUNT(*) AS cnt
		FROM `tabProtocol Step Tracker` pst
		INNER JOIN `tabActive Protocol Bundle` apb ON apb.name = pst.parent
		INNER JOIN `tabInpatient Record` ir ON ir.name = apb.inpatient_record
		WHERE apb.status = 'Active'
			AND pst.status = 'Missed'
			AND ir.custom_current_ward IN %(wards)s
		GROUP BY ir.custom_current_ward
		""",
		{"wards": ward_list},
		as_dict=True,
	)
	return {r["ward"]: int(r["cnt"]) for r in rows}
