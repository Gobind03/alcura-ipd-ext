"""Protocol Compliance Report (US-L4).

Shows protocol adherence for ICU/CICU/MICU and other units with compliance
scoring, step-level detail, and summary metrics.
"""

from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import time_diff_in_seconds


def execute(filters=None):
	filters = filters or {}
	columns = get_columns()
	data = get_data(filters)
	report_summary = _get_report_summary(data)
	chart = _get_chart(data)
	return columns, data, None, chart, report_summary


def get_columns():
	return [
		{
			"fieldname": "active_bundle",
			"label": _("Active Bundle"),
			"fieldtype": "Link",
			"options": "Active Protocol Bundle",
			"width": 140,
		},
		{
			"fieldname": "protocol_bundle",
			"label": _("Protocol"),
			"fieldtype": "Link",
			"options": "Monitoring Protocol Bundle",
			"width": 200,
		},
		{
			"fieldname": "category",
			"label": _("Category"),
			"fieldtype": "Data",
			"width": 100,
		},
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
			"fieldname": "status",
			"label": _("Status"),
			"fieldtype": "Data",
			"width": 100,
		},
		{
			"fieldname": "compliance_score",
			"label": _("Compliance %"),
			"fieldtype": "Percent",
			"width": 110,
		},
		{
			"fieldname": "total_steps",
			"label": _("Total Steps"),
			"fieldtype": "Int",
			"width": 90,
		},
		{
			"fieldname": "completed_steps",
			"label": _("Completed"),
			"fieldtype": "Int",
			"width": 90,
		},
		{
			"fieldname": "missed_steps",
			"label": _("Missed"),
			"fieldtype": "Int",
			"width": 80,
		},
		{
			"fieldname": "delayed_steps",
			"label": _("Delayed"),
			"fieldtype": "Int",
			"width": 80,
		},
		{
			"fieldname": "activated_at",
			"label": _("Activated"),
			"fieldtype": "Datetime",
			"width": 160,
		},
	]


def get_data(filters):
	conditions = []
	values = {}

	if filters.get("protocol_bundle"):
		conditions.append("apb.protocol_bundle = %(protocol_bundle)s")
		values["protocol_bundle"] = filters["protocol_bundle"]

	if filters.get("status"):
		conditions.append("apb.status = %(status)s")
		values["status"] = filters["status"]

	if filters.get("from_date"):
		conditions.append("apb.activated_at >= %(from_date)s")
		values["from_date"] = filters["from_date"]

	if filters.get("to_date"):
		conditions.append("apb.activated_at <= %(to_date)s")
		values["to_date"] = filters["to_date"]

	if filters.get("category"):
		conditions.append("mpb.category = %(category)s")
		values["category"] = filters["category"]

	where = " AND ".join(conditions) if conditions else "1=1"

	bundles = frappe.db.sql(
		f"""
		SELECT
			apb.name AS active_bundle,
			apb.protocol_bundle,
			mpb.category,
			apb.patient,
			apb.inpatient_record,
			apb.status,
			apb.compliance_score,
			apb.activated_at
		FROM `tabActive Protocol Bundle` apb
		LEFT JOIN `tabMonitoring Protocol Bundle` mpb
			ON mpb.name = apb.protocol_bundle
		WHERE {where}
		ORDER BY apb.activated_at DESC
		""",
		values,
		as_dict=True,
	)

	if not bundles:
		return []

	ir_names = list({b["inpatient_record"] for b in bundles if b.get("inpatient_record")})
	ir_data = _batch_ir_data(ir_names)

	icu_ward_filter = filters.get("unit_type")
	icu_wards = set()
	if icu_ward_filter:
		icu_wards = _get_wards_by_unit_type(icu_ward_filter)

	bundle_names = [b["active_bundle"] for b in bundles]
	step_counts = _batch_step_counts(bundle_names)

	result = []
	for row in bundles:
		ir_info = ir_data.get(row.get("inpatient_record"), {})
		row["ward"] = ir_info.get("ward", "")
		row["patient_name"] = ir_info.get("patient_name", "")

		if filters.get("ward") and row["ward"] != filters["ward"]:
			continue

		if icu_ward_filter and row["ward"] not in icu_wards:
			continue

		counts = step_counts.get(row["active_bundle"], {})
		row["total_steps"] = counts.get("total", 0)
		row["completed_steps"] = counts.get("completed", 0)
		row["missed_steps"] = counts.get("missed", 0)
		row["delayed_steps"] = counts.get("delayed", 0)

		result.append(row)

	return result


@frappe.whitelist()
def get_step_detail(active_bundle: str) -> list[dict]:
	"""Return individual step tracker rows for drilldown display."""
	steps = frappe.get_all(
		"Protocol Step Tracker",
		filters={"parent": active_bundle},
		fields=[
			"step_name", "step_type", "sequence", "is_mandatory",
			"status", "due_at", "completed_at", "completed_by", "notes",
		],
		order_by="sequence asc",
	)

	for step in steps:
		if step.get("completed_at") and step.get("due_at"):
			delay_seconds = time_diff_in_seconds(step["completed_at"], step["due_at"])
			step["delay_minutes"] = round(delay_seconds / 60, 1) if delay_seconds > 0 else 0
		else:
			step["delay_minutes"] = None

	return steps


# ── Batch Helpers ────────────────────────────────────────────────────


def _batch_ir_data(ir_names: list[str]) -> dict[str, dict]:
	"""Fetch ward and patient_name for a batch of IRs."""
	if not ir_names:
		return {}

	rows = frappe.db.sql(
		"""
		SELECT name, custom_current_ward AS ward, patient_name
		FROM `tabInpatient Record`
		WHERE name IN %(names)s
		""",
		{"names": ir_names},
		as_dict=True,
	)
	return {r.name: {"ward": r.ward or "", "patient_name": r.patient_name or ""} for r in rows}


def _batch_step_counts(bundle_names: list[str]) -> dict[str, dict]:
	"""Fetch step counts (total, completed, missed, delayed) per bundle."""
	if not bundle_names:
		return {}

	rows = frappe.db.sql(
		"""
		SELECT
			parent,
			COUNT(*) AS total,
			SUM(CASE WHEN status = 'Completed' THEN 1 ELSE 0 END) AS completed,
			SUM(CASE WHEN status = 'Missed' THEN 1 ELSE 0 END) AS missed,
			SUM(
				CASE WHEN status = 'Completed' AND completed_at > due_at
				THEN 1 ELSE 0 END
			) AS delayed
		FROM `tabProtocol Step Tracker`
		WHERE parent IN %(names)s
		GROUP BY parent
		""",
		{"names": bundle_names},
		as_dict=True,
	)
	return {
		r.parent: {
			"total": r.total or 0,
			"completed": r.completed or 0,
			"missed": r.missed or 0,
			"delayed": r.delayed or 0,
		}
		for r in rows
	}


def _get_wards_by_unit_type(unit_type: str) -> set[str]:
	"""Return set of Hospital Ward names whose Healthcare Service Unit Type
	matches the given category (e.g. ICU, CICU, MICU)."""
	wards = frappe.db.sql(
		"""
		SELECT hw.name
		FROM `tabHospital Ward` hw
		INNER JOIN `tabHealthcare Service Unit Type` hsut
			ON hsut.name = hw.service_unit_type
		WHERE hsut.ipd_room_category = %(unit_type)s
		""",
		{"unit_type": unit_type},
		as_dict=True,
	)
	return {w.name for w in wards}


def _get_report_summary(data: list[dict]) -> list[dict]:
	if not data:
		return []

	total = len(data)
	scores = [r.get("compliance_score") or 0 for r in data]
	avg_score = round(sum(scores) / total, 1) if total else 0
	total_missed = sum(r.get("missed_steps") or 0 for r in data)
	total_delayed = sum(r.get("delayed_steps") or 0 for r in data)
	full_compliance = sum(1 for s in scores if s >= 100)

	return [
		{"value": total, "label": _("Total Bundles"), "datatype": "Int"},
		{
			"value": avg_score,
			"label": _("Avg Compliance"),
			"datatype": "Percent",
			"indicator": "red" if avg_score < 80 else ("orange" if avg_score < 95 else "green"),
		},
		{
			"value": full_compliance,
			"label": _("Full Compliance"),
			"datatype": "Int",
			"indicator": "green",
		},
		{
			"value": total_missed,
			"label": _("Total Missed Steps"),
			"datatype": "Int",
			"indicator": "red" if total_missed else "green",
		},
		{
			"value": total_delayed,
			"label": _("Delayed Steps"),
			"datatype": "Int",
			"indicator": "orange" if total_delayed else "green",
		},
	]


def _get_chart(data: list[dict]) -> dict | None:
	if not data:
		return None

	category_scores: dict[str, list[float]] = {}
	for row in data:
		cat = row.get("category") or "Uncategorised"
		score = row.get("compliance_score") or 0
		category_scores.setdefault(cat, []).append(score)

	if not category_scores:
		return None

	labels = sorted(category_scores.keys())
	avg_values = [
		round(sum(category_scores[c]) / len(category_scores[c]), 1)
		for c in labels
	]

	return {
		"data": {
			"labels": labels,
			"datasets": [{"name": _("Avg Compliance %"), "values": avg_values}],
		},
		"type": "bar",
		"colors": ["#36a2eb"],
	}
