"""Service for doctor round sheets and progress note workflows (US-E5).

Aggregates clinical context from multiple subsystems (vitals, labs, meds,
problems, alerts) to support efficient daily round documentation.

Responsibilities:
- Doctor census: list admitted patients for a practitioner
- Patient round summary: rich per-patient clinical snapshot
- Problem list CRUD
- Progress note encounter creation with pre-populated context
"""

from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import (
	add_days,
	date_diff,
	getdate,
	now_datetime,
	today,
)


# ── Doctor Census ────────────────────────────────────────────────────


def get_doctor_census(
	practitioner: str,
	company: str | None = None,
	ward: str | None = None,
) -> list[dict]:
	"""Return all admitted patients for a practitioner with summary data.

	Uses a single query with sub-queries for counts to stay efficient.

	Args:
		practitioner: Healthcare Practitioner name.
		company: Optional company filter.
		ward: Optional ward filter.

	Returns:
		List of dicts with patient info, location, and summary metrics.
	"""
	ir = frappe.qb.DocType("Inpatient Record")

	query = (
		frappe.qb.from_(ir)
		.select(
			ir.name.as_("inpatient_record"),
			ir.patient,
			ir.patient_name,
			ir.status,
			ir.company,
			ir.medical_department,
			ir.scheduled_date.as_("admission_date"),
			ir.custom_current_ward.as_("ward"),
			ir.custom_current_room.as_("room"),
			ir.custom_current_bed.as_("bed"),
			ir.custom_allergy_alert.as_("allergy_alert"),
			ir.custom_allergy_summary.as_("allergy_summary"),
			ir.custom_fall_risk_level.as_("fall_risk"),
			ir.custom_active_problems_count.as_("active_problems"),
			ir.custom_last_progress_note_date.as_("last_progress_note"),
			ir.custom_last_vitals_at.as_("last_vitals_at"),
			ir.custom_overdue_charts_count.as_("overdue_charts"),
			ir.custom_active_lab_orders.as_("pending_tests"),
			ir.custom_due_meds_count.as_("due_meds"),
			ir.custom_critical_alerts_count.as_("critical_alerts"),
		)
		.where(ir.primary_practitioner == practitioner)
		.where(ir.status == "Admitted")
		.orderby(ir.custom_current_ward)
		.orderby(ir.patient_name)
	)

	if company:
		query = query.where(ir.company == company)
	if ward:
		query = query.where(ir.custom_current_ward == ward)

	rows = query.run(as_dict=True)

	today_date = getdate()
	for row in rows:
		admission = getdate(row.get("admission_date")) if row.get("admission_date") else today_date
		row["days_admitted"] = date_diff(today_date, admission) + 1

	return rows


# ── Patient Round Summary ────────────────────────────────────────────


def get_patient_round_summary(inpatient_record: str) -> dict:
	"""Return comprehensive clinical summary for round note preparation.

	Aggregates data from multiple subsystems into a single response
	optimised for the progress note entry form.
	"""
	ir = frappe.db.get_value(
		"Inpatient Record",
		inpatient_record,
		[
			"name", "patient", "patient_name", "status", "company",
			"medical_department", "primary_practitioner", "scheduled_date",
			"custom_current_ward", "custom_current_room", "custom_current_bed",
			"custom_allergy_alert", "custom_allergy_summary",
			"custom_fall_risk_level", "custom_pressure_risk_level",
			"custom_nutrition_risk_level",
			"custom_last_vitals_at", "custom_active_problems_count",
			"custom_last_progress_note_date",
		],
		as_dict=True,
	)
	if not ir:
		frappe.throw(
			_("Inpatient Record {0} not found.").format(frappe.bold(inpatient_record)),
			exc=frappe.DoesNotExistError,
		)

	return {
		"patient": {
			"name": ir.patient,
			"patient_name": ir.patient_name,
			"admission_date": str(ir.scheduled_date) if ir.scheduled_date else "",
			"days_admitted": _days_admitted(ir.scheduled_date),
			"department": ir.medical_department or "",
		},
		"location": {
			"ward": ir.custom_current_ward or "",
			"room": ir.custom_current_room or "",
			"bed": ir.custom_current_bed or "",
		},
		"alerts": _build_alerts(ir),
		"active_problems": get_active_problems(inpatient_record),
		"recent_vitals": _get_recent_vitals(inpatient_record),
		"pending_lab_tests": get_pending_lab_tests(inpatient_record),
		"due_medications": _get_due_medications(inpatient_record),
		"fluid_balance": _get_fluid_balance(inpatient_record),
		"recent_notes": _get_recent_notes(inpatient_record),
	}


# ── Problem List ─────────────────────────────────────────────────────


def get_active_problems(inpatient_record: str) -> list[dict]:
	"""Return active/monitoring problems for an admission."""
	return frappe.get_all(
		"IPD Problem List Item",
		filters={
			"inpatient_record": inpatient_record,
			"status": ("in", ("Active", "Monitoring")),
		},
		fields=[
			"name", "problem_description", "onset_date", "icd_code",
			"status", "severity", "sequence_number", "added_by", "added_on",
		],
		order_by="sequence_number asc, added_on asc",
	)


def add_problem(
	inpatient_record: str,
	problem_description: str,
	onset_date: str | None = None,
	severity: str | None = None,
	icd_code: str | None = None,
	practitioner: str | None = None,
) -> dict:
	"""Create a new problem list item for an admission.

	Returns:
		Dict with ``name`` and ``problem_description``.
	"""
	ir = frappe.db.get_value(
		"Inpatient Record", inpatient_record,
		["patient", "company"],
		as_dict=True,
	)
	if not ir:
		frappe.throw(
			_("Inpatient Record {0} not found.").format(frappe.bold(inpatient_record)),
			exc=frappe.DoesNotExistError,
		)

	max_seq = frappe.db.get_value(
		"IPD Problem List Item",
		{"inpatient_record": inpatient_record},
		"max(sequence_number)",
	) or 0

	doc = frappe.get_doc({
		"doctype": "IPD Problem List Item",
		"patient": ir.patient,
		"inpatient_record": inpatient_record,
		"company": ir.company,
		"problem_description": problem_description,
		"onset_date": onset_date or today(),
		"severity": severity or "",
		"icd_code": icd_code or "",
		"added_by": practitioner or "",
		"sequence_number": max_seq + 1,
	})
	doc.insert(ignore_permissions=True)

	return {"name": doc.name, "problem_description": doc.problem_description}


def resolve_problem(
	problem_name: str,
	resolution_notes: str = "",
	practitioner: str | None = None,
) -> dict:
	"""Mark a problem as resolved.

	Returns:
		Dict with ``name`` and ``status``.
	"""
	doc = frappe.get_doc("IPD Problem List Item", problem_name)

	if doc.status == "Resolved":
		frappe.throw(_("Problem {0} is already resolved.").format(frappe.bold(problem_name)))

	doc.status = "Resolved"
	doc.resolution_notes = resolution_notes
	if practitioner:
		doc.resolved_by = practitioner
	doc.save(ignore_permissions=True)

	return {"name": doc.name, "status": doc.status}


def update_ir_problem_count(inpatient_record: str) -> int:
	"""Recount active problems and update the IR field. Returns new count."""
	count = frappe.db.count(
		"IPD Problem List Item",
		{"inpatient_record": inpatient_record, "status": ("in", ("Active", "Monitoring"))},
	)
	frappe.db.set_value(
		"Inpatient Record",
		inpatient_record,
		"custom_active_problems_count",
		count,
		update_modified=False,
	)
	return count


# ── Progress Note Encounter ─────────────────────────────────────────


def create_progress_note_encounter(
	inpatient_record: str,
	practitioner: str | None = None,
) -> dict:
	"""Create a Progress Note encounter pre-populated with round context.

	Extends the standard consultation encounter creation with:
	- Active problems snapshot
	- Last progress note date update on IR

	Returns:
		Dict with ``encounter``, ``patient``, ``note_type``.
	"""
	from alcura_ipd_ext.services.consultation_note_service import (
		create_consultation_encounter,
	)

	result = create_consultation_encounter(
		inpatient_record=inpatient_record,
		note_type="Progress Note",
		practitioner=practitioner,
	)

	problems = get_active_problems(inpatient_record)
	if problems:
		problems_text = "\n".join(
			f"{i+1}. {p['problem_description']}"
			+ (f" [{p['severity']}]" if p.get("severity") else "")
			for i, p in enumerate(problems)
		)
		frappe.db.set_value(
			"Patient Encounter",
			result["encounter"],
			"custom_active_problems_text",
			problems_text,
			update_modified=False,
		)

	frappe.db.set_value(
		"Inpatient Record",
		inpatient_record,
		"custom_last_progress_note_date",
		today(),
		update_modified=False,
	)

	return result


# ── Pending Lab Tests ────────────────────────────────────────────────


def get_pending_lab_tests(inpatient_record: str) -> list[dict]:
	"""Return lab tests ordered but not yet completed for this admission.

	Looks at lab_test_prescription child rows from submitted encounters
	linked to this IR, then checks whether a corresponding Lab Test
	document exists with a non-completed status.
	"""
	prescriptions = frappe.get_all(
		"Lab Prescription",
		filters={
			"parent": ("in",
				frappe.get_all(
					"Patient Encounter",
					filters={
						"custom_linked_inpatient_record": inpatient_record,
						"docstatus": 1,
					},
					pluck="name",
				) or ["__never_match__"]
			),
		},
		fields=["lab_test_code", "lab_test_name", "parent as encounter"],
	)

	if not prescriptions:
		return []

	pending = []
	for rx in prescriptions:
		completed = frappe.db.exists(
			"Lab Test",
			{
				"template": rx.lab_test_code,
				"custom_linked_inpatient_record": inpatient_record,
				"docstatus": 1,
			},
		)
		if not completed:
			status = "Pending"
			existing = frappe.db.get_value(
				"Lab Test",
				{
					"template": rx.lab_test_code,
					"custom_linked_inpatient_record": inpatient_record,
					"docstatus": 0,
				},
				["name", "status"],
				as_dict=True,
			)
			if existing:
				status = existing.get("status") or "In Progress"

			pending.append({
				"lab_test_code": rx.lab_test_code,
				"lab_test_name": rx.lab_test_name,
				"encounter": rx.encounter,
				"status": status,
			})

	return pending


# ── Private Helpers ──────────────────────────────────────────────────


def _days_admitted(scheduled_date) -> int:
	if not scheduled_date:
		return 0
	return date_diff(getdate(), getdate(scheduled_date)) + 1


def _build_alerts(ir: dict) -> list[dict]:
	"""Build a list of alert items from IR risk/allergy flags."""
	alerts = []

	if ir.get("custom_allergy_alert"):
		alerts.append({
			"type": "allergy",
			"level": "red",
			"message": ir.get("custom_allergy_summary") or "Allergy present",
		})

	risk_map = {
		"custom_fall_risk_level": ("Fall Risk", {"High": "red", "Moderate": "orange", "Low": "green"}),
		"custom_pressure_risk_level": ("Pressure Risk", {"Very High": "red", "High": "red", "Moderate": "orange", "Low": "blue", "No Risk": "green"}),
		"custom_nutrition_risk_level": ("Nutrition Risk", {"High": "red", "Medium": "orange", "Low": "green"}),
	}

	for field, (label, color_map) in risk_map.items():
		value = ir.get(field)
		if value:
			alerts.append({
				"type": field.replace("custom_", "").replace("_level", ""),
				"level": color_map.get(value, "grey"),
				"message": f"{label}: {value}",
			})

	return alerts


def _get_recent_vitals(inpatient_record: str) -> list[dict]:
	"""Return latest vital signs from the most recent chart entry."""
	from alcura_ipd_ext.services.charting_service import get_charts_for_ir

	charts = get_charts_for_ir(inpatient_record)
	vitals_charts = [c for c in charts if c.get("chart_type") == "Vitals" and c.get("status") == "Active"]
	if not vitals_charts:
		return []

	chart_name = vitals_charts[0]["name"]
	latest_entry = frappe.get_all(
		"IPD Chart Entry",
		filters={"bedside_chart": chart_name, "status": "Active"},
		fields=["name", "entry_datetime"],
		order_by="entry_datetime desc",
		limit_page_length=1,
	)
	if not latest_entry:
		return []

	observations = frappe.get_all(
		"IPD Chart Observation",
		filters={"parent": latest_entry[0]["name"]},
		fields=["parameter_name", "numeric_value", "text_value", "select_value", "uom", "is_critical"],
		order_by="idx asc",
	)

	return [
		{
			"parameter": obs.parameter_name,
			"value": obs.numeric_value if obs.numeric_value is not None else (obs.text_value or obs.select_value or ""),
			"uom": obs.uom or "",
			"is_critical": obs.is_critical,
			"recorded_at": str(latest_entry[0]["entry_datetime"]),
		}
		for obs in observations
	]


def _get_due_medications(inpatient_record: str) -> dict:
	"""Return today's due medication summary from the MAR service."""
	from alcura_ipd_ext.services.mar_service import get_mar_summary

	summary = get_mar_summary(inpatient_record, today())
	due_entries = [
		e for e in summary.get("entries", [])
		if e.get("administration_status") in ("Scheduled", "Due", "")
	]

	return {
		"total_today": summary.get("total", 0),
		"due_count": len(due_entries),
		"status_counts": summary.get("status_counts", {}),
		"due_entries": [
			{
				"medication": e.get("medication_name", ""),
				"dose": e.get("dose", ""),
				"route": e.get("route", ""),
				"scheduled_time": str(e.get("scheduled_time", "")),
			}
			for e in due_entries[:10]
		],
	}


def _get_fluid_balance(inpatient_record: str) -> dict:
	"""Return today's fluid balance summary."""
	from alcura_ipd_ext.services.io_service import get_fluid_balance

	return get_fluid_balance(inpatient_record, today())


def _get_recent_notes(inpatient_record: str) -> list[dict]:
	"""Return recent progress notes for this admission."""
	return frappe.get_all(
		"Patient Encounter",
		filters={
			"custom_linked_inpatient_record": inpatient_record,
			"custom_ipd_note_type": ("in", ("Progress Note", "Admission Note", "Consultation Note")),
			"docstatus": ("!=", 2),
		},
		fields=[
			"name", "encounter_date", "practitioner_name",
			"custom_ipd_note_type as note_type",
			"custom_ipd_note_summary as summary",
			"custom_chief_complaint_text as chief_complaint",
			"docstatus",
		],
		order_by="encounter_date desc, creation desc",
		limit_page_length=5,
	)
