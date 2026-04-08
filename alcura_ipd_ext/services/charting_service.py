"""Service for bedside charting operations.

Handles:
- Bedside chart creation from template
- Chart entry recording with parameter population
- Correction entry creation
- Overdue chart detection
- Chart summary queries
"""

from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import add_to_date, get_datetime, now_datetime


# ── Bedside Chart Creation ───────────────────────────────────────────


def start_bedside_chart(
	inpatient_record: str,
	chart_template: str,
	frequency_minutes: int | None = None,
) -> dict:
	"""Create an IPD Bedside Chart for an admission.

	Returns:
		Dict with ``chart`` (name), ``chart_type``, ``status``.
	"""
	ir = frappe.db.get_value(
		"Inpatient Record",
		inpatient_record,
		["patient", "status", "custom_current_ward", "custom_current_bed"],
		as_dict=True,
	)
	if not ir:
		frappe.throw(_("Inpatient Record {0} not found.").format(inpatient_record))

	if ir.status not in ("Admitted", "Admission Scheduled"):
		frappe.throw(_("Cannot start a chart for a patient with status '{0}'.").format(ir.status))

	template = frappe.get_doc("IPD Chart Template", chart_template)
	if not template.is_active:
		frappe.throw(_("Chart template '{0}' is not active.").format(chart_template))

	_check_duplicate_chart(inpatient_record, chart_template)

	freq = frequency_minutes or template.default_frequency_minutes

	doc = frappe.get_doc({
		"doctype": "IPD Bedside Chart",
		"patient": ir.patient,
		"inpatient_record": inpatient_record,
		"chart_template": chart_template,
		"frequency_minutes": freq,
		"status": "Active",
		"started_at": now_datetime(),
	})
	doc.insert(ignore_permissions=True)

	frappe.get_doc("Inpatient Record", inpatient_record).add_comment(
		"Info",
		_("{0} chart started (every {1} min).").format(
			template.chart_type, freq
		),
	)

	return {
		"chart": doc.name,
		"chart_type": doc.chart_type,
		"status": doc.status,
	}


def _check_duplicate_chart(inpatient_record: str, chart_template: str):
	existing = frappe.db.exists(
		"IPD Bedside Chart",
		{
			"inpatient_record": inpatient_record,
			"chart_template": chart_template,
			"status": ("in", ("Active", "Paused")),
		},
	)
	if existing:
		frappe.throw(
			_("An active chart already exists for this template: {0}").format(existing)
		)


# ── Chart Entry Recording ───────────────────────────────────────────


def record_chart_entry(
	bedside_chart: str,
	observations: list[dict],
	entry_datetime: str | None = None,
	notes: str = "",
) -> dict:
	"""Record a chart entry with observations.

	Args:
		bedside_chart: Name of the IPD Bedside Chart.
		observations: List of dicts with ``parameter_name`` and value fields.
		entry_datetime: Optional override (defaults to now).
		notes: Optional entry notes.

	Returns:
		Dict with ``entry`` (name), ``chart_type``, ``has_critical``.
	"""
	doc = frappe.get_doc({
		"doctype": "IPD Chart Entry",
		"bedside_chart": bedside_chart,
		"entry_datetime": entry_datetime or now_datetime(),
		"notes": notes,
		"observations": [
			{
				"parameter_name": obs.get("parameter_name"),
				"numeric_value": obs.get("numeric_value"),
				"text_value": obs.get("text_value"),
				"select_value": obs.get("select_value"),
				"uom": obs.get("uom", ""),
			}
			for obs in observations
		],
	})
	doc.insert(ignore_permissions=True)

	has_critical = any(o.is_critical for o in doc.observations)

	if doc.chart_type == "Vitals":
		frappe.db.set_value(
			"Inpatient Record",
			doc.inpatient_record,
			"custom_last_vitals_at",
			doc.entry_datetime,
			update_modified=False,
		)

	return {
		"entry": doc.name,
		"chart_type": doc.chart_type,
		"has_critical": has_critical,
	}


# ── Correction Entry ────────────────────────────────────────────────


def create_correction_entry(original_entry: str, correction_reason: str) -> dict:
	"""Create a correction for an existing chart entry.

	The original entry is marked as Corrected, and a new entry is created
	pre-populated with the original observations for editing.

	Returns:
		Dict with ``name`` of the new correction entry.
	"""
	original = frappe.get_doc("IPD Chart Entry", original_entry)

	if original.status == "Corrected":
		frappe.throw(_("This entry has already been corrected."))

	new_doc = frappe.get_doc({
		"doctype": "IPD Chart Entry",
		"bedside_chart": original.bedside_chart,
		"entry_datetime": original.entry_datetime,
		"is_correction": 1,
		"corrects_entry": original.name,
		"correction_reason": correction_reason,
		"notes": original.notes,
		"observations": [
			{
				"parameter_name": obs.parameter_name,
				"numeric_value": obs.numeric_value,
				"text_value": obs.text_value,
				"select_value": obs.select_value,
				"uom": obs.uom,
			}
			for obs in original.observations
		],
	})
	new_doc.insert(ignore_permissions=True)

	return {"name": new_doc.name}


# ── Parameter Retrieval ─────────────────────────────────────────────


def get_chart_parameters(bedside_chart: str) -> list[dict]:
	"""Return template parameters for a bedside chart."""
	template_name = frappe.db.get_value(
		"IPD Bedside Chart", bedside_chart, "chart_template"
	)
	if not template_name:
		return []

	return frappe.get_all(
		"IPD Chart Template Parameter",
		filters={"parent": template_name},
		fields=[
			"parameter_name", "parameter_type", "uom", "options",
			"min_value", "max_value", "critical_low", "critical_high",
			"is_mandatory", "display_order",
		],
		order_by="display_order asc",
	)


# ── Overdue Detection ───────────────────────────────────────────────


def get_overdue_charts(
	ward: str | None = None,
	company: str | None = None,
	grace_minutes: int = 0,
) -> list[dict]:
	"""Return active bedside charts that are overdue.

	An chart is overdue when ``now > last_entry_at + frequency_minutes + grace``.
	If ``last_entry_at`` is null, ``started_at`` is used.
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
		],
	)

	now = now_datetime()
	overdue = []

	for chart in charts:
		base_time = get_datetime(chart.last_entry_at or chart.started_at)
		due_at = add_to_date(base_time, minutes=chart.frequency_minutes + grace_minutes)

		if now > due_at:
			diff = now - due_at
			chart["overdue_minutes"] = int(diff.total_seconds() / 60)
			chart["next_due_at"] = str(due_at)
			overdue.append(chart)

	overdue.sort(key=lambda c: c["overdue_minutes"], reverse=True)
	return overdue


# ── Chart Summary ────────────────────────────────────────────────────


def get_charts_for_ir(inpatient_record: str) -> list[dict]:
	"""Return all bedside charts for an Inpatient Record."""
	charts = frappe.get_all(
		"IPD Bedside Chart",
		filters={"inpatient_record": inpatient_record},
		fields=[
			"name", "chart_template", "chart_type", "status",
			"frequency_minutes", "started_at", "last_entry_at",
			"total_entries", "ward", "bed",
		],
		order_by="status asc, chart_type asc",
	)

	now = now_datetime()
	for chart in charts:
		if chart.status == "Active":
			base_time = get_datetime(chart.last_entry_at or chart.started_at)
			due_at = add_to_date(base_time, minutes=chart.frequency_minutes)
			chart["is_overdue"] = now > due_at
			chart["overdue_minutes"] = max(0, int((now - due_at).total_seconds() / 60)) if now > due_at else 0
		else:
			chart["is_overdue"] = False
			chart["overdue_minutes"] = 0

	return charts


def update_ir_chart_counts(inpatient_record: str):
	"""Update the charting summary fields on Inpatient Record."""
	active_count = frappe.db.count(
		"IPD Bedside Chart",
		{"inpatient_record": inpatient_record, "status": "Active"},
	)

	overdue_charts = get_overdue_charts()
	overdue_count = sum(
		1 for c in overdue_charts if c["inpatient_record"] == inpatient_record
	)

	frappe.db.set_value(
		"Inpatient Record",
		inpatient_record,
		{
			"custom_active_charts_count": active_count,
			"custom_overdue_charts_count": overdue_count,
		},
		update_modified=False,
	)
