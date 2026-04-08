"""Device connectivity and observation exception service (US-N3).

Provides three exception categories for ICU operations managers:

1. **Connectivity failures** — Device Observation Feed records with Error status
2. **Missing observations** — Expected observation slots on device-sourced
   charts with no corresponding entry
3. **Unacknowledged abnormals** — Critical device-generated observations
   not followed by a manual chart entry within a configurable window

Definitions
-----------
- **Connectivity failure**: ``Device Observation Feed.status = 'Error'``
- **Missing observation**: An expected observation slot (per chart frequency)
  with no actual entry, on charts sourced from device mappings
  (``source_profile`` is set).
- **Unacknowledged abnormal**: Critical device-generated observation not
  followed by a manual chart entry on the same chart within
  ``_ACK_WINDOW_MINUTES`` (default 30 min).
"""

from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import add_to_date, get_datetime, now_datetime

# Configurable acknowledgement window for critical device observations
_ACK_WINDOW_MINUTES = 30

# Exception type constants
CONNECTIVITY_FAILURE = "Connectivity Failure"
MISSING_OBSERVATION = "Missing Observation"
UNACKNOWLEDGED_ABNORMAL = "Unacknowledged Abnormal"


def get_exceptions(
	from_date: str,
	to_date: str,
	exception_type: str | None = None,
	ward: str | None = None,
	patient: str | None = None,
	device_type: str | None = None,
) -> list[dict]:
	"""Return all device/observation exceptions in the date range.

	Each row has: exception_type, datetime, patient, patient_name, ward,
	device_type, device_id, chart, parameter, description, source_name.
	"""
	to_date_end = f"{to_date} 23:59:59"

	rows: list[dict] = []

	if not exception_type or exception_type == CONNECTIVITY_FAILURE:
		rows.extend(_get_connectivity_failures(
			from_date, to_date_end, ward, patient, device_type,
		))

	if not exception_type or exception_type == MISSING_OBSERVATION:
		rows.extend(_get_missing_observations(
			from_date, to_date_end, ward, patient, device_type,
		))

	if not exception_type or exception_type == UNACKNOWLEDGED_ABNORMAL:
		rows.extend(_get_unacknowledged_abnormals(
			from_date, to_date_end, ward, patient, device_type,
		))

	rows.sort(key=lambda r: r.get("datetime") or "", reverse=True)
	return rows


def get_exception_summary(rows: list[dict]) -> dict[str, int]:
	"""Return count of exceptions grouped by type."""
	summary: dict[str, int] = {}
	for row in rows:
		et = row.get("exception_type", "Unknown")
		summary[et] = summary.get(et, 0) + 1
	return summary


# ── Connectivity Failures ────────────────────────────────────────────


def _get_connectivity_failures(
	from_date: str,
	to_date_end: str,
	ward: str | None,
	patient: str | None,
	device_type: str | None,
) -> list[dict]:
	"""Query Device Observation Feed records with Error status."""
	conditions = [
		"dof.status = 'Error'",
		"dof.received_at BETWEEN %(from_date)s AND %(to_date_end)s",
	]
	params: dict = {"from_date": from_date, "to_date_end": to_date_end}

	if patient:
		conditions.append("dof.patient = %(patient)s")
		params["patient"] = patient

	if device_type:
		conditions.append("dof.source_device_type = %(device_type)s")
		params["device_type"] = device_type

	ward_join = ""
	if ward:
		ward_join = "INNER JOIN `tabInpatient Record` ir ON ir.name = dof.inpatient_record"
		conditions.append("ir.custom_current_ward = %(ward)s")
		params["ward"] = ward

	where = " AND ".join(conditions)

	feeds = frappe.db.sql(
		f"""
		SELECT
			dof.name,
			dof.received_at AS dt,
			dof.patient,
			dof.inpatient_record,
			dof.source_device_type,
			dof.source_device_id,
			dof.error_message
		FROM `tabDevice Observation Feed` dof
		{ward_join}
		WHERE {where}
		ORDER BY dof.received_at DESC
		LIMIT 500
		""",
		params,
		as_dict=True,
	)

	rows = []
	for f in feeds:
		patient_name = ""
		ward_name = ""
		if f.patient:
			patient_name = frappe.db.get_value("Patient", f.patient, "patient_name") or ""
		if f.inpatient_record:
			ward_name = frappe.db.get_value(
				"Inpatient Record", f.inpatient_record, "custom_current_ward"
			) or ""

		rows.append({
			"exception_type": CONNECTIVITY_FAILURE,
			"datetime": f.dt,
			"patient": f.patient or "",
			"patient_name": patient_name,
			"ward": ward_name,
			"device_type": f.source_device_type or "",
			"device_id": f.source_device_id or "",
			"chart": "",
			"parameter": "",
			"description": f.error_message or "Device feed error",
			"source_name": f.name,
			"source_doctype": "Device Observation Feed",
		})

	return rows


# ── Missing Observations ────────────────────────────────────────────


def _get_missing_observations(
	from_date: str,
	to_date_end: str,
	ward: str | None,
	patient: str | None,
	device_type: str | None,
) -> list[dict]:
	"""Detect expected-but-missing observation slots on device-sourced charts.

	Only considers charts with ``source_profile`` set (indicating device sourcing).
	"""
	filters: dict = {
		"status": "Active",
		"source_profile": ("is", "set"),
	}
	if ward:
		filters["ward"] = ward

	charts = frappe.get_all(
		"IPD Bedside Chart",
		filters=filters,
		fields=[
			"name", "patient", "patient_name", "inpatient_record",
			"chart_type", "chart_template", "frequency_minutes",
			"started_at", "last_entry_at", "ward", "bed",
			"source_profile",
		],
	)

	if patient:
		charts = [c for c in charts if c.patient == patient]

	if device_type:
		template_device_map = _get_template_device_types()
		charts = [
			c for c in charts
			if template_device_map.get(c.chart_template) == device_type
		]

	from_dt = get_datetime(from_date)
	to_dt = get_datetime(to_date_end)
	now = now_datetime()

	rows = []
	for chart in charts:
		missed_slots = _compute_missed_slots(chart, from_dt, to_dt, now)
		device_info = _get_device_info_for_chart(chart.chart_template)

		for slot in missed_slots:
			rows.append({
				"exception_type": MISSING_OBSERVATION,
				"datetime": slot,
				"patient": chart.patient or "",
				"patient_name": chart.patient_name or "",
				"ward": chart.ward or "",
				"device_type": device_info.get("device_type", ""),
				"device_id": "",
				"chart": chart.name,
				"parameter": "",
				"description": (
					f"Missing {chart.chart_type or ''} observation "
					f"(every {chart.frequency_minutes} min)"
				),
				"source_name": chart.name,
				"source_doctype": "IPD Bedside Chart",
			})

	return rows


def _compute_missed_slots(
	chart: dict,
	from_dt,
	to_dt,
	now,
) -> list[str]:
	"""Return list of expected-but-missed observation slot datetimes."""
	started = get_datetime(chart.started_at)
	freq = chart.frequency_minutes or 60

	actual_entries = frappe.db.sql(
		"""
		SELECT entry_datetime
		FROM `tabIPD Chart Entry`
		WHERE bedside_chart = %(chart)s AND status = 'Active'
			AND entry_datetime BETWEEN %(from)s AND %(to)s
		ORDER BY entry_datetime ASC
		""",
		{"chart": chart["name"], "from": str(from_dt), "to": str(to_dt)},
		as_dict=True,
	)
	actual_times = [get_datetime(e.entry_datetime) for e in actual_entries]

	grace_seconds = max(freq * 60 * 0.25, 300)

	slot = max(started, from_dt)
	missed = []

	while slot <= to_dt and slot < now:
		if not _has_nearby_entry(slot, actual_times, grace_seconds):
			missed.append(str(slot))
		slot = add_to_date(slot, minutes=freq)

	return missed


def _has_nearby_entry(expected, actual_times: list, grace_seconds: float) -> bool:
	for actual in actual_times:
		if abs((actual - expected).total_seconds()) <= grace_seconds:
			return True
	return False


# ── Unacknowledged Abnormals ─────────────────────────────────────────


def _get_unacknowledged_abnormals(
	from_date: str,
	to_date_end: str,
	ward: str | None,
	patient: str | None,
	device_type: str | None,
) -> list[dict]:
	"""Find critical device-generated observations without a follow-up
	manual entry within the acknowledgement window."""
	conditions = [
		"ce.status = 'Active'",
		"ce.is_device_generated = 1",
		"co.is_critical = 1",
		"ce.entry_datetime BETWEEN %(from_date)s AND %(to_date_end)s",
	]
	params: dict = {"from_date": from_date, "to_date_end": to_date_end}

	if patient:
		conditions.append("ce.patient = %(patient)s")
		params["patient"] = patient

	if ward:
		conditions.append("bc.ward = %(ward)s")
		params["ward"] = ward

	where = " AND ".join(conditions)

	entries = frappe.db.sql(
		f"""
		SELECT
			ce.name,
			ce.entry_datetime,
			ce.patient,
			p.patient_name,
			ce.bedside_chart,
			bc.ward,
			bc.chart_type,
			bc.chart_template,
			co.parameter_name,
			co.numeric_value,
			co.uom,
			ce.device_feed
		FROM `tabIPD Chart Entry` ce
		INNER JOIN `tabIPD Chart Observation` co ON co.parent = ce.name
		LEFT JOIN `tabIPD Bedside Chart` bc ON bc.name = ce.bedside_chart
		LEFT JOIN `tabPatient` p ON p.name = ce.patient
		WHERE {where}
		ORDER BY ce.entry_datetime DESC
		LIMIT 500
		""",
		params,
		as_dict=True,
	)

	if device_type:
		template_device_map = _get_template_device_types()
		entries = [
			e for e in entries
			if template_device_map.get(e.chart_template) == device_type
		]

	rows = []
	for e in entries:
		if _has_follow_up_entry(e.bedside_chart, e.entry_datetime):
			continue

		value_str = ""
		if e.numeric_value is not None:
			value_str = f"{e.numeric_value}"
			if e.uom:
				value_str += f" {e.uom}"

		device_info = _get_device_info_for_chart(e.chart_template)

		rows.append({
			"exception_type": UNACKNOWLEDGED_ABNORMAL,
			"datetime": e.entry_datetime,
			"patient": e.patient or "",
			"patient_name": e.patient_name or "",
			"ward": e.ward or "",
			"device_type": device_info.get("device_type", ""),
			"device_id": "",
			"chart": e.bedside_chart or "",
			"parameter": e.parameter_name or "",
			"description": (
				f"Unacknowledged critical: {e.parameter_name or ''} = {value_str} "
				f"({e.chart_type or ''})"
			),
			"source_name": e.name,
			"source_doctype": "IPD Chart Entry",
		})

	return rows


def _has_follow_up_entry(bedside_chart: str, critical_datetime) -> bool:
	"""Check if a manual chart entry was recorded within the ack window
	after the critical device entry."""
	window_end = add_to_date(
		get_datetime(critical_datetime), minutes=_ACK_WINDOW_MINUTES
	)

	return bool(frappe.db.exists(
		"IPD Chart Entry",
		{
			"bedside_chart": bedside_chart,
			"status": "Active",
			"is_device_generated": 0,
			"entry_datetime": ("between", [str(critical_datetime), str(window_end)]),
		},
	))


# ── Shared helpers ───────────────────────────────────────────────────


def _get_template_device_types() -> dict[str, str]:
	"""Return mapping of chart_template -> source_device_type from active mappings."""
	mappings = frappe.get_all(
		"Device Observation Mapping",
		filters={"is_active": 1},
		fields=["chart_template", "source_device_type"],
	)
	return {m.chart_template: m.source_device_type for m in mappings}


def _get_device_info_for_chart(chart_template: str | None) -> dict:
	"""Return device type info for a chart template."""
	if not chart_template:
		return {}
	device_type = frappe.db.get_value(
		"Device Observation Mapping",
		{"chart_template": chart_template, "is_active": 1},
		"source_device_type",
	)
	return {"device_type": device_type or ""}
