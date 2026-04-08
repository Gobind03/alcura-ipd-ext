"""Bed Transfer and Housekeeping Report — Script Report (US-K2).

Combined report showing:
1. Transfer log entries for the period
2. Currently blocked beds (maintenance / infection)
3. Housekeeping TAT aggregate summary

The main data table lists transfer movements. Blocked beds and
housekeeping TAT metrics are rendered in the report message HTML
and summary cards.
"""

from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import flt


def execute(filters: dict | None = None):
	filters = filters or {}
	columns = _get_columns()
	data = _get_transfer_data(filters)
	message = _build_message_html(filters)
	summary = _get_report_summary(filters)

	return columns, data, message, None, summary


# ── columns ─────────────────────────────────────────────────────────


def _get_columns() -> list[dict]:
	return [
		{"fieldname": "name", "label": _("Movement Log"), "fieldtype": "Link", "options": "Bed Movement Log", "width": 120},
		{"fieldname": "movement_type", "label": _("Type"), "fieldtype": "Data", "width": 80},
		{"fieldname": "patient", "label": _("Patient"), "fieldtype": "Link", "options": "Patient", "width": 100},
		{"fieldname": "patient_name", "label": _("Patient Name"), "fieldtype": "Data", "width": 150},
		{"fieldname": "from_ward", "label": _("From Ward"), "fieldtype": "Link", "options": "Hospital Ward", "width": 130},
		{"fieldname": "from_room", "label": _("From Room"), "fieldtype": "Link", "options": "Hospital Room", "width": 110},
		{"fieldname": "from_bed", "label": _("From Bed"), "fieldtype": "Link", "options": "Hospital Bed", "width": 110},
		{"fieldname": "to_ward", "label": _("To Ward"), "fieldtype": "Link", "options": "Hospital Ward", "width": 130},
		{"fieldname": "to_room", "label": _("To Room"), "fieldtype": "Link", "options": "Hospital Room", "width": 110},
		{"fieldname": "to_bed", "label": _("To Bed"), "fieldtype": "Link", "options": "Hospital Bed", "width": 110},
		{"fieldname": "reason", "label": _("Reason"), "fieldtype": "Data", "width": 150},
		{"fieldname": "practitioner_name", "label": _("Consultant"), "fieldtype": "Data", "width": 140},
		{"fieldname": "movement_datetime", "label": _("Date/Time"), "fieldtype": "Datetime", "width": 160},
	]


# ── transfer data ──────────────────────────────────────────────────


def _get_transfer_data(filters: dict) -> list[dict]:
	conditions = []
	params: dict = {}

	movement_type = filters.get("movement_type")
	if movement_type and movement_type != "All":
		conditions.append("bml.movement_type = %(movement_type)s")
		params["movement_type"] = movement_type
	else:
		conditions.append("bml.movement_type IN ('Transfer', 'Discharge')")

	if filters.get("from_date"):
		conditions.append("bml.movement_datetime >= %(from_date)s")
		params["from_date"] = filters["from_date"]

	if filters.get("to_date"):
		conditions.append("bml.movement_datetime <= CONCAT(%(to_date)s, ' 23:59:59')")
		params["to_date"] = filters["to_date"]

	if filters.get("ward"):
		conditions.append("(bml.from_ward = %(ward)s OR bml.to_ward = %(ward)s)")
		params["ward"] = filters["ward"]

	if filters.get("consultant"):
		conditions.append("bml.ordered_by_practitioner = %(consultant)s")
		params["consultant"] = filters["consultant"]

	if filters.get("company"):
		conditions.append("bml.company = %(company)s")
		params["company"] = filters["company"]

	if filters.get("branch"):
		conditions.append(
			"(EXISTS (SELECT 1 FROM `tabHospital Ward` w WHERE w.name = bml.from_ward AND w.branch = %(branch)s)"
			" OR EXISTS (SELECT 1 FROM `tabHospital Ward` w WHERE w.name = bml.to_ward AND w.branch = %(branch)s))"
		)
		params["branch"] = filters["branch"]

	where = " AND ".join(conditions) if conditions else "1=1"

	return frappe.db.sql(
		f"""
		SELECT
			bml.name,
			bml.movement_type,
			bml.patient,
			bml.patient_name,
			bml.from_ward,
			bml.from_room,
			bml.from_bed,
			bml.to_ward,
			bml.to_room,
			bml.to_bed,
			bml.reason,
			bml.practitioner_name,
			bml.movement_datetime
		FROM `tabBed Movement Log` bml
		WHERE {where}
		ORDER BY bml.movement_datetime DESC
		""",
		params,
		as_dict=True,
	)


# ── blocked beds ───────────────────────────────────────────────────


def _get_blocked_beds(filters: dict) -> list[dict]:
	conditions = [
		"bed.is_active = 1",
		"(bed.maintenance_hold = 1 OR bed.infection_block = 1)",
	]
	params: dict = {}

	if filters.get("ward"):
		conditions.append("bed.hospital_ward = %(ward)s")
		params["ward"] = filters["ward"]

	if filters.get("company"):
		conditions.append("bed.company = %(company)s")
		params["company"] = filters["company"]

	if filters.get("branch"):
		conditions.append(
			"EXISTS (SELECT 1 FROM `tabHospital Ward` w WHERE w.name = bed.hospital_ward AND w.branch = %(branch)s)"
		)
		params["branch"] = filters["branch"]

	where = " AND ".join(conditions)

	return frappe.db.sql(
		f"""
		SELECT
			bed.name AS bed,
			bed.hospital_ward AS ward,
			bed.hospital_room AS room,
			CASE
				WHEN bed.maintenance_hold = 1 AND bed.infection_block = 1
					THEN 'Maintenance + Infection Block'
				WHEN bed.maintenance_hold = 1 THEN 'Maintenance Hold'
				ELSE 'Infection Block'
			END AS block_reason,
			bed.modified AS blocked_since
		FROM `tabHospital Bed` bed
		WHERE {where}
		ORDER BY bed.hospital_ward, bed.name
		""",
		params,
		as_dict=True,
	)


# ── housekeeping TAT summary ──────────────────────────────────────


def _get_housekeeping_summary(filters: dict) -> dict:
	conditions = []
	params: dict = {}

	if filters.get("from_date"):
		conditions.append("task.created_on >= %(from_date)s")
		params["from_date"] = filters["from_date"]

	if filters.get("to_date"):
		conditions.append("task.created_on <= CONCAT(%(to_date)s, ' 23:59:59')")
		params["to_date"] = filters["to_date"]

	if filters.get("ward"):
		conditions.append("task.hospital_ward = %(ward)s")
		params["ward"] = filters["ward"]

	if filters.get("company"):
		conditions.append("task.company = %(company)s")
		params["company"] = filters["company"]

	where = " AND ".join(conditions) if conditions else "1=1"

	row = frappe.db.sql(
		f"""
		SELECT
			COUNT(*) AS total_tasks,
			SUM(CASE WHEN task.status = 'Completed' THEN 1 ELSE 0 END) AS completed,
			SUM(CASE WHEN task.status IN ('Pending', 'In Progress') THEN 1 ELSE 0 END) AS pending,
			SUM(CASE WHEN task.sla_breached = 1 THEN 1 ELSE 0 END) AS sla_breached,
			AVG(CASE WHEN task.status = 'Completed' THEN task.turnaround_minutes END) AS avg_tat
		FROM `tabBed Housekeeping Task` task
		WHERE {where}
		""",
		params,
		as_dict=True,
	)

	if row:
		r = row[0]
		total = int(r.total_tasks or 0)
		breached = int(r.sla_breached or 0)
		return {
			"total_tasks": total,
			"completed": int(r.completed or 0),
			"pending": int(r.pending or 0),
			"sla_breached": breached,
			"sla_breach_pct": round((breached / total) * 100, 1) if total else 0.0,
			"avg_tat": round(flt(r.avg_tat), 1),
		}
	return {
		"total_tasks": 0, "completed": 0, "pending": 0,
		"sla_breached": 0, "sla_breach_pct": 0.0, "avg_tat": 0.0,
	}


def _get_housekeeping_by_ward(filters: dict) -> list[dict]:
	conditions = ["task.status = 'Completed'", "task.turnaround_minutes IS NOT NULL"]
	params: dict = {}

	if filters.get("from_date"):
		conditions.append("task.created_on >= %(from_date)s")
		params["from_date"] = filters["from_date"]

	if filters.get("to_date"):
		conditions.append("task.created_on <= CONCAT(%(to_date)s, ' 23:59:59')")
		params["to_date"] = filters["to_date"]

	if filters.get("ward"):
		conditions.append("task.hospital_ward = %(ward)s")
		params["ward"] = filters["ward"]

	if filters.get("company"):
		conditions.append("task.company = %(company)s")
		params["company"] = filters["company"]

	where = " AND ".join(conditions)

	return frappe.db.sql(
		f"""
		SELECT
			task.hospital_ward AS ward,
			task.cleaning_type,
			COUNT(*) AS task_count,
			ROUND(AVG(task.turnaround_minutes), 1) AS avg_tat
		FROM `tabBed Housekeeping Task` task
		WHERE {where}
		GROUP BY task.hospital_ward, task.cleaning_type
		ORDER BY task.hospital_ward, task.cleaning_type
		""",
		params,
		as_dict=True,
	)


# ── message HTML ───────────────────────────────────────────────────


def _build_message_html(filters: dict) -> str:
	blocked = _get_blocked_beds(filters)
	hk_summary = _get_housekeeping_summary(filters)
	hk_by_ward = _get_housekeeping_by_ward(filters)

	parts = []

	# Blocked beds table
	parts.append("<h5>{}</h5>".format(_("Currently Blocked Beds")))
	if blocked:
		parts.append('<table class="table table-bordered table-sm">')
		parts.append("<thead><tr><th>{}</th><th>{}</th><th>{}</th><th>{}</th><th>{}</th></tr></thead>".format(
			_("Bed"), _("Ward"), _("Room"), _("Reason"), _("Since"),
		))
		parts.append("<tbody>")
		for row in blocked:
			parts.append(
				"<tr><td>{}</td><td>{}</td><td>{}</td><td>{}</td><td>{}</td></tr>".format(
					row["bed"], row["ward"], row["room"],
					row["block_reason"],
					frappe.format(row["blocked_since"], {"fieldtype": "Datetime"}),
				)
			)
		parts.append("</tbody></table>")
	else:
		parts.append("<p>{}</p>".format(_("No blocked beds.")))

	# Housekeeping TAT summary
	parts.append("<h5>{}</h5>".format(_("Housekeeping Summary")))
	parts.append(
		"<p>{total_tasks} {total_label} &bull; {completed} {completed_label} "
		"&bull; {pending} {pending_label} &bull; {sla_breached} {sla_label} "
		"({sla_breach_pct}%) &bull; {avg_label}: {avg_tat} min</p>".format(
			total_label=_("Total"),
			completed_label=_("Completed"),
			pending_label=_("Pending"),
			sla_label=_("SLA Breached"),
			avg_label=_("Avg TAT"),
			**hk_summary,
		)
	)

	# TAT by ward and cleaning type
	if hk_by_ward:
		parts.append('<table class="table table-bordered table-sm">')
		parts.append("<thead><tr><th>{}</th><th>{}</th><th>{}</th><th>{}</th></tr></thead>".format(
			_("Ward"), _("Cleaning Type"), _("Tasks"), _("Avg TAT (min)"),
		))
		parts.append("<tbody>")
		for row in hk_by_ward:
			parts.append(
				"<tr><td>{}</td><td>{}</td><td>{}</td><td>{}</td></tr>".format(
					row["ward"], row["cleaning_type"], row["task_count"], row["avg_tat"],
				)
			)
		parts.append("</tbody></table>")

	return "\n".join(parts)


# ── summary cards ──────────────────────────────────────────────────


def _get_report_summary(filters: dict) -> list[dict]:
	transfer_count = _count_transfers(filters)
	blocked_count = len(_get_blocked_beds(filters))
	hk = _get_housekeeping_summary(filters)

	return [
		{
			"value": transfer_count,
			"indicator": "Blue",
			"label": _("Total Transfers"),
			"datatype": "Int",
		},
		{
			"value": blocked_count,
			"indicator": "Red" if blocked_count > 0 else "Green",
			"label": _("Blocked Beds"),
			"datatype": "Int",
		},
		{
			"value": hk["avg_tat"],
			"indicator": "Blue",
			"label": _("Avg Housekeeping TAT (min)"),
			"datatype": "Float",
		},
		{
			"value": hk["sla_breach_pct"],
			"indicator": "Red" if hk["sla_breach_pct"] > 20 else (
				"Orange" if hk["sla_breach_pct"] > 10 else "Green"
			),
			"label": _("SLA Breach %"),
			"datatype": "Percent",
		},
	]


def _count_transfers(filters: dict) -> int:
	conditions = ["bml.movement_type = 'Transfer'"]
	params: dict = {}

	if filters.get("from_date"):
		conditions.append("bml.movement_datetime >= %(from_date)s")
		params["from_date"] = filters["from_date"]

	if filters.get("to_date"):
		conditions.append("bml.movement_datetime <= CONCAT(%(to_date)s, ' 23:59:59')")
		params["to_date"] = filters["to_date"]

	if filters.get("ward"):
		conditions.append("(bml.from_ward = %(ward)s OR bml.to_ward = %(ward)s)")
		params["ward"] = filters["ward"]

	if filters.get("company"):
		conditions.append("bml.company = %(company)s")
		params["company"] = filters["company"]

	where = " AND ".join(conditions)

	result = frappe.db.sql(
		f"SELECT COUNT(*) AS cnt FROM `tabBed Movement Log` bml WHERE {where}",
		params,
		as_dict=True,
	)
	return int(result[0].cnt) if result else 0
