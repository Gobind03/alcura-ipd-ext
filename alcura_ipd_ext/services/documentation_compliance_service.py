"""Documentation Compliance Service (US-L2).

Checks completeness of clinical documentation for admitted patients:
- Admission Note presence
- Daily progress note recency
- Intake assessment completion
- Nursing chart currency (overdue charts)
- Discharge summary presence (when applicable)

Produces per-patient compliance scores for operational review.
"""

from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import date_diff, getdate


def get_documentation_compliance(
	company: str | None = None,
	ward: str | None = None,
	practitioner: str | None = None,
	medical_department: str | None = None,
	status: str = "Admitted",
) -> list[dict]:
	"""Return documentation compliance data for admitted patients.

	Each row contains compliance flags and a computed score. All data
	is fetched in batch queries to avoid N+1 patterns.
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
			ir.medical_department.as_("department"),
			ir.primary_practitioner,
			ir.scheduled_date.as_("admission_date"),
			ir.custom_current_ward.as_("ward"),
			ir.custom_current_room.as_("room"),
			ir.custom_current_bed.as_("bed"),
			ir.custom_last_progress_note_date.as_("last_progress_note"),
			ir.custom_overdue_charts_count.as_("overdue_charts"),
			ir.custom_intake_status.as_("intake_status"),
		)
		.where(ir.status == status)
		.orderby(ir.custom_current_ward)
		.orderby(ir.patient_name)
	)

	if company:
		query = query.where(ir.company == company)
	if ward:
		query = query.where(ir.custom_current_ward == ward)
	if practitioner:
		query = query.where(ir.primary_practitioner == practitioner)
	if medical_department:
		query = query.where(ir.medical_department == medical_department)

	rows = query.run(as_dict=True)
	if not rows:
		return []

	ir_names = [r["inpatient_record"] for r in rows]

	admission_notes = _batch_check_note_type(ir_names, "Admission Note")
	progress_notes = _batch_latest_note_dates(ir_names, "Progress Note")
	discharge_summaries = _batch_check_note_type(ir_names, "Discharge Summary")
	practitioner_names = _batch_practitioner_names(
		list({r["primary_practitioner"] for r in rows if r.get("primary_practitioner")})
	)

	today_date = getdate()

	for row in rows:
		ir_name = row["inpatient_record"]
		admission_date = getdate(row["admission_date"]) if row.get("admission_date") else today_date
		row["days_admitted"] = date_diff(today_date, admission_date) + 1

		row["practitioner_name"] = practitioner_names.get(
			row.get("primary_practitioner"), ""
		)

		row["has_admission_note"] = 1 if ir_name in admission_notes else 0

		last_note_date = progress_notes.get(ir_name)
		if last_note_date:
			row["progress_note_gap"] = date_diff(today_date, getdate(last_note_date))
		else:
			row["progress_note_gap"] = row["days_admitted"]

		intake = row.get("intake_status") or ""
		row["intake_complete"] = 1 if intake == "Completed" else 0

		row["nursing_charts_ok"] = 1 if not row.get("overdue_charts") else 0

		needs_discharge = row.get("status") in (
			"Discharge Initiated", "Discharge in Progress",
		)
		if needs_discharge:
			row["has_discharge_summary"] = 1 if ir_name in discharge_summaries else 0
		else:
			row["has_discharge_summary"] = None

		row["compliance_score"] = _compute_compliance_score(row)

	return rows


def _compute_compliance_score(row: dict) -> float:
	"""Calculate percentage of applicable documentation checks that pass."""
	checks = [
		row.get("has_admission_note", 0),
		1 if row.get("progress_note_gap", 99) <= 1 else 0,
		row.get("intake_complete", 0),
		row.get("nursing_charts_ok", 0),
	]

	if row.get("has_discharge_summary") is not None:
		checks.append(row["has_discharge_summary"])

	total = len(checks)
	passed = sum(checks)
	return round((passed / total) * 100, 1) if total else 0.0


def _batch_check_note_type(ir_names: list[str], note_type: str) -> set[str]:
	"""Return set of IR names that have at least one submitted encounter
	of the given note type."""
	if not ir_names:
		return set()

	results = frappe.get_all(
		"Patient Encounter",
		filters={
			"custom_linked_inpatient_record": ("in", ir_names),
			"custom_ipd_note_type": note_type,
			"docstatus": 1,
		},
		fields=["custom_linked_inpatient_record"],
		group_by="custom_linked_inpatient_record",
	)
	return {r.custom_linked_inpatient_record for r in results}


def _batch_latest_note_dates(ir_names: list[str], note_type: str) -> dict[str, str]:
	"""Return dict of IR name -> latest encounter_date for the given note type."""
	if not ir_names:
		return {}

	results = frappe.db.sql(
		"""
		SELECT
			custom_linked_inpatient_record AS ir_name,
			MAX(encounter_date) AS latest_date
		FROM `tabPatient Encounter`
		WHERE custom_linked_inpatient_record IN %(ir_names)s
			AND custom_ipd_note_type = %(note_type)s
			AND docstatus = 1
		GROUP BY custom_linked_inpatient_record
		""",
		{"ir_names": ir_names, "note_type": note_type},
		as_dict=True,
	)
	return {r.ir_name: str(r.latest_date) for r in results if r.latest_date}


def _batch_practitioner_names(practitioner_ids: list[str]) -> dict[str, str]:
	"""Return dict of practitioner_id -> practitioner_name."""
	if not practitioner_ids:
		return {}

	results = frappe.get_all(
		"Healthcare Practitioner",
		filters={"name": ("in", practitioner_ids)},
		fields=["name", "practitioner_name"],
	)
	return {r.name: r.practitioner_name for r in results}
