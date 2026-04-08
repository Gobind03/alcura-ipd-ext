"""Observation trend and schedule service (US-H2).

Provides high-performance queries for:
- Time-series parameter trends (for graph rendering)
- Expected vs actual observation schedule (missed observation detection)
- Dashboard summaries for ICU/ward views
"""

from __future__ import annotations

import frappe
from frappe.utils import add_to_date, get_datetime, now_datetime


def get_parameter_trend(
	bedside_chart: str,
	parameter_name: str,
	from_datetime: str | None = None,
	to_datetime: str | None = None,
	limit: int = 200,
) -> list[dict]:
	"""Return time-series data for a single parameter on a bedside chart.

	Optimised for graphing: returns only (datetime, value, is_critical, status).
	Uses raw SQL for performance on high-frequency charts.
	"""
	conditions = [
		"ce.bedside_chart = %(chart)s",
		"co.parameter_name = %(param)s",
		"ce.status = 'Active'",
		"co.numeric_value IS NOT NULL",
	]
	params = {
		"chart": bedside_chart,
		"param": parameter_name,
		"limit": limit,
	}

	if from_datetime:
		conditions.append("ce.entry_datetime >= %(from_dt)s")
		params["from_dt"] = from_datetime
	if to_datetime:
		conditions.append("ce.entry_datetime <= %(to_dt)s")
		params["to_dt"] = to_datetime

	where = " AND ".join(conditions)

	return frappe.db.sql(
		f"""
		SELECT
			ce.entry_datetime AS datetime,
			co.numeric_value AS value,
			co.is_critical,
			ce.is_correction,
			ce.is_device_generated
		FROM `tabIPD Chart Entry` ce
		INNER JOIN `tabIPD Chart Observation` co ON co.parent = ce.name
		WHERE {where}
		ORDER BY ce.entry_datetime ASC
		LIMIT %(limit)s
		""",
		params,
		as_dict=True,
	)


def get_multi_parameter_trend(
	bedside_chart: str,
	parameter_names: list[str],
	from_datetime: str | None = None,
	to_datetime: str | None = None,
	limit: int = 500,
) -> dict[str, list[dict]]:
	"""Return time-series data for multiple parameters, keyed by parameter name.

	More efficient than calling get_parameter_trend N times as it uses
	a single query.
	"""
	if not parameter_names:
		return {}

	conditions = [
		"ce.bedside_chart = %(chart)s",
		"ce.status = 'Active'",
		"co.numeric_value IS NOT NULL",
	]
	params: dict = {
		"chart": bedside_chart,
		"limit": limit,
	}

	placeholders = ", ".join(f"%({f'p{i}')s" for i in range(len(parameter_names)))
	for i, pn in enumerate(parameter_names):
		params[f"p{i}"] = pn
	conditions.append(f"co.parameter_name IN ({placeholders})")

	if from_datetime:
		conditions.append("ce.entry_datetime >= %(from_dt)s")
		params["from_dt"] = from_datetime
	if to_datetime:
		conditions.append("ce.entry_datetime <= %(to_dt)s")
		params["to_dt"] = to_datetime

	where = " AND ".join(conditions)

	rows = frappe.db.sql(
		f"""
		SELECT
			co.parameter_name,
			ce.entry_datetime AS datetime,
			co.numeric_value AS value,
			co.is_critical
		FROM `tabIPD Chart Entry` ce
		INNER JOIN `tabIPD Chart Observation` co ON co.parent = ce.name
		WHERE {where}
		ORDER BY ce.entry_datetime ASC
		LIMIT %(limit)s
		""",
		params,
		as_dict=True,
	)

	result: dict[str, list[dict]] = {pn: [] for pn in parameter_names}
	for row in rows:
		pn = row.pop("parameter_name")
		if pn in result:
			result[pn].append(row)

	return result


def get_observation_schedule(
	bedside_chart: str,
	from_datetime: str | None = None,
	to_datetime: str | None = None,
) -> list[dict]:
	"""Return expected vs actual observation slots for a bedside chart.

	Generates expected slots from started_at + frequency_minutes, then
	matches against actual entries to identify gaps (missed observations).
	"""
	chart = frappe.db.get_value(
		"IPD Bedside Chart",
		bedside_chart,
		["started_at", "frequency_minutes", "status", "discontinued_at"],
		as_dict=True,
	)
	if not chart or not chart.started_at:
		return []

	start = get_datetime(from_datetime or chart.started_at)
	end_bound = get_datetime(to_datetime) if to_datetime else now_datetime()
	if chart.status == "Discontinued" and chart.discontinued_at:
		disc = get_datetime(chart.discontinued_at)
		if disc < end_bound:
			end_bound = disc

	freq = chart.frequency_minutes or 60

	actual_entries = frappe.db.sql(
		"""
		SELECT entry_datetime
		FROM `tabIPD Chart Entry`
		WHERE bedside_chart = %(chart)s AND status = 'Active'
		ORDER BY entry_datetime ASC
		""",
		{"chart": bedside_chart},
		as_dict=True,
	)
	actual_times = [get_datetime(e.entry_datetime) for e in actual_entries]

	slots = []
	current_slot = start
	grace_seconds = max(freq * 60 * 0.25, 300)  # 25% of interval or 5 min minimum

	while current_slot <= end_bound:
		matched_entry = _find_closest_entry(current_slot, actual_times, grace_seconds)
		slots.append({
			"expected_at": str(current_slot),
			"actual_at": str(matched_entry) if matched_entry else None,
			"is_missed": matched_entry is None and current_slot < now_datetime(),
			"is_future": current_slot > now_datetime(),
		})
		current_slot = add_to_date(current_slot, minutes=freq)

	return slots


def compute_missed_observations(
	bedside_chart: str,
	from_datetime: str | None = None,
	to_datetime: str | None = None,
) -> dict:
	"""Return missed observation count and time slots for a bedside chart."""
	schedule = get_observation_schedule(bedside_chart, from_datetime, to_datetime)
	missed = [s for s in schedule if s["is_missed"]]
	return {
		"total_expected": len([s for s in schedule if not s["is_future"]]),
		"total_recorded": len([s for s in schedule if s["actual_at"]]),
		"missed_count": len(missed),
		"missed_slots": missed,
	}


def get_dashboard_summary(
	ward: str | None = None,
	shift_start: str | None = None,
	shift_end: str | None = None,
) -> list[dict]:
	"""Aggregated observation summary per active bedside chart for dashboard view.

	Returns one row per chart with entry counts, last entry time, and overdue status.
	"""
	filters = {"status": "Active"}
	if ward:
		filters["ward"] = ward

	charts = frappe.get_all(
		"IPD Bedside Chart",
		filters=filters,
		fields=[
			"name", "patient", "patient_name", "inpatient_record",
			"chart_type", "chart_template", "frequency_minutes",
			"started_at", "last_entry_at", "ward", "bed",
			"missed_count", "source_profile",
		],
	)

	now = now_datetime()
	shift_s = get_datetime(shift_start) if shift_start else None
	shift_e = get_datetime(shift_end) if shift_end else None

	for chart in charts:
		base_time = get_datetime(chart.last_entry_at or chart.started_at)
		due_at = add_to_date(base_time, minutes=chart.frequency_minutes)
		chart["next_due_at"] = str(due_at)
		chart["is_overdue"] = now > due_at
		chart["overdue_minutes"] = max(0, int((now - due_at).total_seconds() / 60)) if now > due_at else 0

		if chart["is_overdue"]:
			overdue_ratio = chart["overdue_minutes"] / max(chart.frequency_minutes, 1)
			if overdue_ratio >= 3:
				chart["severity"] = "Critical"
			elif overdue_ratio >= 2:
				chart["severity"] = "Escalation"
			else:
				chart["severity"] = "Warning"
		else:
			chart["severity"] = None

		if shift_s and shift_e:
			chart["shift_entries"] = frappe.db.count(
				"IPD Chart Entry",
				{
					"bedside_chart": chart.name,
					"status": "Active",
					"entry_datetime": ("between", [str(shift_s), str(shift_e)]),
				},
			)
		else:
			chart["shift_entries"] = None

	charts.sort(key=lambda c: (c.get("severity") or "Z", -(c.get("overdue_minutes") or 0)))
	return charts


def classify_overdue_severity(
	overdue_minutes: int,
	frequency_minutes: int,
) -> str | None:
	"""Classify overdue severity based on how many intervals have been missed."""
	if overdue_minutes <= 0:
		return None
	ratio = overdue_minutes / max(frequency_minutes, 1)
	if ratio >= 3:
		return "Critical"
	if ratio >= 2:
		return "Escalation"
	return "Warning"


def _find_closest_entry(
	expected: "datetime",
	actual_times: list,
	grace_seconds: float,
) -> "datetime | None":
	"""Find the actual entry closest to an expected slot within grace period."""
	for actual in actual_times:
		diff = abs((actual - expected).total_seconds())
		if diff <= grace_seconds:
			return actual
	return None
