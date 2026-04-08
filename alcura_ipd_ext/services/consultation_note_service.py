"""Service for IPD consultant clinical documentation via Patient Encounter.

US-E3: Handles creation and lifecycle of consultant admission/progress notes
by extending standard Patient Encounter with IPD clinical context.

Responsibilities:
- Create pre-populated Patient Encounters linked to an Inpatient Record
- Extract and present clinical context (allergies, risks, history)
- Validate IPD-specific encounter constraints
- Post timeline comments on IR when notes are submitted
"""

from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import now_datetime


# ── Encounter Creation ───────────────────────────────────────────────


def create_consultation_encounter(
	inpatient_record: str,
	note_type: str = "Admission Note",
	practitioner: str | None = None,
) -> dict:
	"""Create a draft Patient Encounter pre-linked to the Inpatient Record.

	The encounter is pre-populated with allergy data from the IR and
	past history from the most recent intake assessment.

	Args:
		inpatient_record: Name of the Inpatient Record (must be Admitted
			or Admission Scheduled).
		note_type: One of Admission Note, Progress Note, Procedure Note,
			Consultation Note, Discharge Summary.
		practitioner: Healthcare Practitioner name. Falls back to the IR's
			primary practitioner if not provided.

	Returns:
		Dict with ``encounter``, ``patient``, and ``note_type`` keys.

	Raises:
		frappe.ValidationError: If the IR is not in a valid status or
			required fields are missing.
	"""
	ir_doc = frappe.get_doc("Inpatient Record", inpatient_record)
	_validate_ir_for_encounter(ir_doc)

	resolved_practitioner = practitioner or ir_doc.primary_practitioner
	if not resolved_practitioner:
		frappe.throw(
			_("A Healthcare Practitioner must be specified."),
			exc=frappe.ValidationError,
		)

	context = _extract_prepopulation_data(ir_doc)

	enc_doc = frappe.get_doc({
		"doctype": "Patient Encounter",
		"patient": ir_doc.patient,
		"practitioner": resolved_practitioner,
		"medical_department": ir_doc.medical_department,
		"company": ir_doc.company,
		"encounter_date": frappe.utils.today(),
		"custom_linked_inpatient_record": ir_doc.name,
		"custom_ipd_note_type": note_type,
		"custom_allergies_text": context.get("allergy_summary") or "",
		"custom_past_history_summary": context.get("past_history") or "",
	})

	enc_doc.insert()

	ir_doc.add_comment(
		"Info",
		_("{0} started by {1}.").format(
			frappe.bold(note_type),
			frappe.bold(
				frappe.db.get_value(
					"Healthcare Practitioner",
					resolved_practitioner,
					"practitioner_name",
				)
				or resolved_practitioner
			),
		),
	)

	return {
		"encounter": enc_doc.name,
		"patient": enc_doc.patient,
		"note_type": note_type,
	}


# ── Clinical Context ─────────────────────────────────────────────────


def get_ipd_clinical_context(inpatient_record: str) -> dict:
	"""Return clinical context data for display on IPD encounter forms.

	Fetches allergy flags, nursing risk indicators, current bed location,
	and recent encounter summaries from the Inpatient Record.
	"""
	ir_fields = [
		"name", "patient", "patient_name", "status",
		"custom_current_bed", "custom_current_room", "custom_current_ward",
		"custom_allergy_alert", "custom_allergy_summary",
		"custom_fall_risk_level", "custom_pressure_risk_level",
		"custom_nutrition_risk_level",
		"primary_practitioner",
	]
	ir = frappe.db.get_value("Inpatient Record", inpatient_record, ir_fields, as_dict=True)
	if not ir:
		frappe.throw(
			_("Inpatient Record {0} not found.").format(frappe.bold(inpatient_record)),
			exc=frappe.DoesNotExistError,
		)

	recent_encounters = frappe.get_all(
		"Patient Encounter",
		filters={
			"custom_linked_inpatient_record": inpatient_record,
			"docstatus": ("!=", 2),
		},
		fields=[
			"name", "encounter_date", "practitioner", "practitioner_name",
			"custom_ipd_note_type", "custom_ipd_note_summary",
			"custom_chief_complaint_text", "docstatus",
		],
		order_by="encounter_date desc, creation desc",
		limit_page_length=5,
	)

	intake_history = _extract_intake_history(inpatient_record)

	return {
		"allergy_alert": ir.get("custom_allergy_alert") or 0,
		"allergy_summary": ir.get("custom_allergy_summary") or "",
		"risk_flags": {
			"fall": ir.get("custom_fall_risk_level") or "",
			"pressure": ir.get("custom_pressure_risk_level") or "",
			"nutrition": ir.get("custom_nutrition_risk_level") or "",
		},
		"bed": ir.get("custom_current_bed") or "",
		"room": ir.get("custom_current_room") or "",
		"ward": ir.get("custom_current_ward") or "",
		"status": ir.get("status") or "",
		"recent_encounters": recent_encounters,
		"intake_history": intake_history,
	}


def _extract_intake_history(inpatient_record: str) -> dict:
	"""Extract clinical history fields from the latest completed intake
	assessment responses for the given IR."""
	intake_name = frappe.db.get_value(
		"IPD Intake Assessment",
		{"inpatient_record": inpatient_record, "status": "Completed"},
		"name",
		order_by="creation desc",
	)
	if not intake_name:
		return {}

	history_labels = {
		"Chief Complaint",
		"History of Present Illness",
		"Past Medical History",
		"Past Surgical History",
		"Drug History",
		"Family History",
		"Social History",
		"Provisional Diagnosis",
		"Plan of Care",
	}

	responses = frappe.get_all(
		"IPD Intake Assessment Response",
		filters={"parent": intake_name, "field_label": ("in", list(history_labels))},
		fields=["field_label", "text_value"],
	)

	return {r.field_label: r.text_value for r in responses if r.text_value}


# ── Validation ───────────────────────────────────────────────────────


def validate_consultation_encounter(doc: "frappe.Document") -> None:
	"""Server-side validation for Patient Encounters linked to an IR.

	Called from the doc_events validate hook when
	``custom_linked_inpatient_record`` is set.
	"""
	ir_name = doc.get("custom_linked_inpatient_record")
	if not ir_name:
		return

	if not doc.get("custom_ipd_note_type"):
		frappe.throw(
			_("Note Type is required when the encounter is linked to an Inpatient Record."),
			exc=frappe.ValidationError,
		)

	ir_status = frappe.db.get_value("Inpatient Record", ir_name, "status")
	if not ir_status:
		frappe.throw(
			_("Inpatient Record {0} not found.").format(frappe.bold(ir_name)),
			exc=frappe.DoesNotExistError,
		)

	valid_statuses = ("Admission Scheduled", "Admitted")
	if ir_status not in valid_statuses:
		frappe.throw(
			_("Cannot create consultation note: Inpatient Record {0} is in "
			  "'{1}' status. Expected one of: {2}.").format(
				frappe.bold(ir_name),
				ir_status,
				", ".join(valid_statuses),
			),
			exc=frappe.ValidationError,
		)

	if not doc.get("practitioner"):
		frappe.throw(
			_("A Healthcare Practitioner must be set for IPD consultation notes."),
			exc=frappe.ValidationError,
		)

	note_type = doc.get("custom_ipd_note_type")
	if note_type == "Admission Note" and not doc.get("custom_chief_complaint_text"):
		frappe.throw(
			_("Chief Complaint is required for Admission Notes."),
			exc=frappe.ValidationError,
		)


# ── On Submit ────────────────────────────────────────────────────────


def on_submit_consultation_encounter(doc: "frappe.Document") -> None:
	"""Post-submit actions for IPD consultation encounters.

	- Adds a timeline comment to the Inpatient Record
	- Publishes a realtime event for nurse station awareness
	"""
	ir_name = doc.get("custom_linked_inpatient_record")
	if not ir_name:
		return

	note_type = doc.get("custom_ipd_note_type") or "Note"
	summary = doc.get("custom_ipd_note_summary") or doc.get("custom_chief_complaint_text") or ""
	practitioner_name = doc.get("practitioner_name") or doc.get("practitioner") or ""

	summary_text = f" — {summary}" if summary else ""

	try:
		ir_doc = frappe.get_doc("Inpatient Record", ir_name)
		ir_doc.add_comment(
			"Info",
			_("{note_type} submitted by {practitioner}{summary}").format(
				note_type=frappe.bold(note_type),
				practitioner=frappe.bold(practitioner_name),
				summary=summary_text,
			),
		)
	except Exception:
		frappe.log_error(
			title=f"US-E3: Failed to add IR timeline comment for {doc.name}",
		)

	frappe.publish_realtime(
		"ipd_note_submitted",
		{
			"encounter": doc.name,
			"inpatient_record": ir_name,
			"note_type": note_type,
			"patient": doc.patient,
			"practitioner": practitioner_name,
		},
		after_commit=True,
	)


# ── Helpers ──────────────────────────────────────────────────────────


def _validate_ir_for_encounter(ir_doc: "frappe.Document") -> None:
	"""Validate that the Inpatient Record is in a state that allows
	new consultation encounters."""
	valid_statuses = ("Admission Scheduled", "Admitted")
	if ir_doc.status not in valid_statuses:
		frappe.throw(
			_("Cannot create consultation note: Inpatient Record {0} is in "
			  "'{1}' status. Expected one of: {2}.").format(
				frappe.bold(ir_doc.name),
				ir_doc.status,
				", ".join(valid_statuses),
			),
			exc=frappe.ValidationError,
		)


def _extract_prepopulation_data(ir_doc: "frappe.Document") -> dict:
	"""Gather allergy and history data from the IR and its intake
	assessments for pre-populating new encounters."""
	data: dict = {
		"allergy_summary": ir_doc.get("custom_allergy_summary") or "",
	}

	intake_history = _extract_intake_history(ir_doc.name)
	history_parts = []
	for label in (
		"Past Medical History",
		"Past Surgical History",
		"Drug History",
		"Family History",
		"Social History",
	):
		value = intake_history.get(label)
		if value:
			history_parts.append(f"{label}: {value}")

	data["past_history"] = "\n".join(history_parts) if history_parts else ""

	return data
