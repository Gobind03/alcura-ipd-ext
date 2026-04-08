"""Incident and critical alert report service (US-N2).

Consolidates safety/quality incidents from multiple source records
into a unified row format for quality managers:

- Fall-risk / Nursing risk alerts (from ToDo)
- Missed medications (from IPD MAR Entry)
- Critical observations (from IPD Chart Entry + Observation)
- SLA breaches (from IPD Clinical Order)
"""

from __future__ import annotations

import frappe
from frappe import _


# Incident type constants
FALL_RISK = "Fall Risk"
PRESSURE_RISK = "Pressure Risk"
NUTRITION_RISK = "Nutrition Risk"
MISSED_MEDICATION = "Missed Medication"
CRITICAL_OBSERVATION = "Critical Observation"
SLA_BREACH = "SLA Breach"

_RISK_TAG_MAP = {
	"fall-risk": FALL_RISK,
	"pressure-risk": PRESSURE_RISK,
	"nutrition-risk": NUTRITION_RISK,
}


def get_incidents(
	from_date: str,
	to_date: str,
	incident_type: str | None = None,
	ward: str | None = None,
	patient: str | None = None,
	severity: str | None = None,
) -> list[dict]:
	"""Return consolidated incident rows from all sources.

	Each row has: incident_datetime, incident_type, severity, patient,
	patient_name, ward, description, source_doctype, source_name, status.
	"""
	to_date_end = f"{to_date} 23:59:59"

	collectors = [
		(_collect_risk_alerts, FALL_RISK),
		(_collect_risk_alerts, PRESSURE_RISK),
		(_collect_risk_alerts, NUTRITION_RISK),
		(_collect_missed_medications, MISSED_MEDICATION),
		(_collect_critical_observations, CRITICAL_OBSERVATION),
		(_collect_sla_breaches, SLA_BREACH),
	]

	rows: list[dict] = []
	for collector, itype in collectors:
		if incident_type and incident_type != itype:
			continue
		rows.extend(
			collector(
				from_date=from_date,
				to_date_end=to_date_end,
				ward=ward,
				patient=patient,
				incident_type_filter=itype,
			)
		)

	if severity:
		rows = [r for r in rows if r.get("severity") == severity]

	rows.sort(key=lambda r: r.get("incident_datetime") or "", reverse=True)
	return rows


def get_incident_summary(rows: list[dict]) -> dict[str, int]:
	"""Return count of incidents grouped by type."""
	summary: dict[str, int] = {}
	for row in rows:
		it = row.get("incident_type", "Unknown")
		summary[it] = summary.get(it, 0) + 1
	return summary


# ── Collectors ───────────────────────────────────────────────────────


def _collect_risk_alerts(
	from_date: str,
	to_date_end: str,
	ward: str | None,
	patient: str | None,
	incident_type_filter: str,
) -> list[dict]:
	"""Collect nursing risk alert ToDos created by nursing_alert_service."""
	tag = None
	for key, val in _RISK_TAG_MAP.items():
		if val == incident_type_filter:
			tag = key
			break

	if not tag:
		return []

	ref_pattern = f"%NursingRisk:{tag}%"

	conditions = [
		"td.reference_type = 'Inpatient Record'",
		"td.description LIKE %(ref_pattern)s",
		"td.creation BETWEEN %(from_date)s AND %(to_date_end)s",
	]
	params: dict = {
		"ref_pattern": ref_pattern,
		"from_date": from_date,
		"to_date_end": to_date_end,
	}

	if patient:
		conditions.append("ir.patient = %(patient)s")
		params["patient"] = patient

	if ward:
		conditions.append("ir.custom_current_ward = %(ward)s")
		params["ward"] = ward

	where = " AND ".join(conditions)

	todos = frappe.db.sql(
		f"""
		SELECT
			td.name,
			td.creation AS incident_datetime,
			td.description,
			td.priority,
			td.status,
			td.reference_name AS inpatient_record,
			ir.patient,
			ir.patient_name,
			ir.custom_current_ward AS ward
		FROM `tabToDo` td
		LEFT JOIN `tabInpatient Record` ir ON ir.name = td.reference_name
		WHERE {where}
		ORDER BY td.creation DESC
		LIMIT 500
		""",
		params,
		as_dict=True,
	)

	rows = []
	for td in todos:
		rows.append({
			"incident_datetime": td.incident_datetime,
			"incident_type": incident_type_filter,
			"severity": _map_priority_to_severity(td.priority),
			"patient": td.patient or "",
			"patient_name": td.patient_name or "",
			"ward": td.ward or "",
			"description": _clean_todo_description(td.description or ""),
			"source_doctype": "ToDo",
			"source_name": td.name,
			"status": td.status or "Open",
		})

	return rows


def _collect_missed_medications(
	from_date: str,
	to_date_end: str,
	ward: str | None,
	patient: str | None,
	incident_type_filter: str,
) -> list[dict]:
	"""Collect MAR entries with administration_status = Missed."""
	conditions = [
		"mar.status = 'Active'",
		"mar.administration_status = 'Missed'",
		"mar.scheduled_time BETWEEN %(from_date)s AND %(to_date_end)s",
	]
	params: dict = {"from_date": from_date, "to_date_end": to_date_end}

	if patient:
		conditions.append("mar.patient = %(patient)s")
		params["patient"] = patient

	if ward:
		conditions.append("mar.ward = %(ward)s")
		params["ward"] = ward

	where = " AND ".join(conditions)

	entries = frappe.db.sql(
		f"""
		SELECT
			mar.name,
			mar.scheduled_time AS incident_datetime,
			mar.patient,
			p.patient_name,
			mar.ward,
			mar.medication_name,
			mar.dose,
			mar.route
		FROM `tabIPD MAR Entry` mar
		LEFT JOIN `tabPatient` p ON p.name = mar.patient
		WHERE {where}
		ORDER BY mar.scheduled_time DESC
		LIMIT 500
		""",
		params,
		as_dict=True,
	)

	rows = []
	for e in entries:
		desc = f"Missed: {e.medication_name or ''} {e.dose or ''} ({e.route or ''})"
		rows.append({
			"incident_datetime": e.incident_datetime,
			"incident_type": MISSED_MEDICATION,
			"severity": "Medium",
			"patient": e.patient or "",
			"patient_name": e.patient_name or "",
			"ward": e.ward or "",
			"description": desc.strip(),
			"source_doctype": "IPD MAR Entry",
			"source_name": e.name,
			"status": "Open",
		})

	return rows


def _collect_critical_observations(
	from_date: str,
	to_date_end: str,
	ward: str | None,
	patient: str | None,
	incident_type_filter: str,
) -> list[dict]:
	"""Collect chart entries with critical observations."""
	conditions = [
		"ce.status = 'Active'",
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
			ce.entry_datetime AS incident_datetime,
			ce.patient,
			p.patient_name,
			bc.ward,
			co.parameter_name,
			co.numeric_value,
			co.uom,
			ce.chart_type
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

	rows = []
	for e in entries:
		value_str = ""
		if e.numeric_value is not None:
			value_str = f"{e.numeric_value}"
			if e.uom:
				value_str += f" {e.uom}"

		desc = f"Critical {e.chart_type or ''}: {e.parameter_name or ''} = {value_str}"
		rows.append({
			"incident_datetime": e.incident_datetime,
			"incident_type": CRITICAL_OBSERVATION,
			"severity": "High",
			"patient": e.patient or "",
			"patient_name": e.patient_name or "",
			"ward": e.ward or "",
			"description": desc.strip(),
			"source_doctype": "IPD Chart Entry",
			"source_name": e.name,
			"status": "Open",
		})

	return rows


def _collect_sla_breaches(
	from_date: str,
	to_date_end: str,
	ward: str | None,
	patient: str | None,
	incident_type_filter: str,
) -> list[dict]:
	"""Collect clinical orders that have breached SLA."""
	conditions = [
		"co.is_sla_breached = 1",
		"co.ordered_at BETWEEN %(from_date)s AND %(to_date_end)s",
	]
	params: dict = {"from_date": from_date, "to_date_end": to_date_end}

	if patient:
		conditions.append("co.patient = %(patient)s")
		params["patient"] = patient

	if ward:
		conditions.append("co.ward = %(ward)s")
		params["ward"] = ward

	where = " AND ".join(conditions)

	orders = frappe.db.sql(
		f"""
		SELECT
			co.name,
			co.ordered_at AS incident_datetime,
			co.patient,
			co.patient_name,
			co.ward,
			co.order_type,
			co.urgency,
			co.status,
			co.sla_breach_count
		FROM `tabIPD Clinical Order` co
		WHERE {where}
		ORDER BY co.ordered_at DESC
		LIMIT 500
		""",
		params,
		as_dict=True,
	)

	rows = []
	for o in orders:
		severity = "High" if o.urgency in ("STAT", "Emergency") else "Medium"
		desc = (
			f"SLA Breach: {o.order_type or ''} ({o.urgency or ''}) "
			f"— {o.sla_breach_count or 0} milestone(s) breached"
		)
		rows.append({
			"incident_datetime": o.incident_datetime,
			"incident_type": SLA_BREACH,
			"severity": severity,
			"patient": o.patient or "",
			"patient_name": o.patient_name or "",
			"ward": o.ward or "",
			"description": desc.strip(),
			"source_doctype": "IPD Clinical Order",
			"source_name": o.name,
			"status": o.status or "Open",
		})

	return rows


# ── Helpers ──────────────────────────────────────────────────────────


def _map_priority_to_severity(priority: str | None) -> str:
	if priority == "High":
		return "High"
	if priority == "Medium":
		return "Medium"
	return "Low"


def _clean_todo_description(description: str) -> str:
	"""Remove HTML comment refs embedded by nursing_alert_service."""
	import re
	return re.sub(r"\s*<!--.*?-->", "", description).strip()
