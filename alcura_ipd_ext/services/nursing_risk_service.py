"""Risk calculation and flag management for nursing admission assessments.

Interprets scored Patient Assessment totals using standard clinical cutoffs
and maintains risk indicator fields on the Inpatient Record.

Covers:
- Morse Fall Scale risk classification
- Braden Scale pressure injury risk classification
- MUST Nutritional Screening risk classification
- Allergy data extraction from IPD Intake Assessment responses
- Composite risk flag update on Inpatient Record
"""

from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import now_datetime


# ── Scale-to-Template name mapping ───────────────────────────────────

MORSE_TEMPLATE = "Morse Fall Scale"
BRADEN_TEMPLATE = "Braden Scale"
MUST_TEMPLATE = "MUST Nutritional Screening"

# Allergy field label used in intake templates
_ALLERGY_FIELD_LABEL = "Known Allergies"
_ALLERGY_DETAILS_LABEL = "Allergy Details"
_ALLERGY_NONE_VALUE = "None Known"


# ── Risk Classification Functions ────────────────────────────────────


def classify_fall_risk(total_score: int) -> str:
	"""Classify Morse Fall Scale total into a risk level.

	Standard clinical thresholds:
	  0–24  → Low
	  25–44 → Moderate
	  ≥ 45  → High
	"""
	if total_score >= 45:
		return "High"
	if total_score >= 25:
		return "Moderate"
	return "Low"


def classify_braden_risk(total_score: int) -> str:
	"""Classify Braden Scale total into a pressure injury risk level.

	Standard clinical thresholds (lower score = higher risk):
	  ≥ 19  → No Risk
	  15–18 → Low
	  13–14 → Moderate
	  10–12 → High
	  ≤ 9   → Very High
	"""
	if total_score >= 19:
		return "No Risk"
	if total_score >= 15:
		return "Low"
	if total_score >= 13:
		return "Moderate"
	if total_score >= 10:
		return "High"
	return "Very High"


def classify_nutrition_risk(total_score: int) -> str:
	"""Classify MUST Nutritional Screening total into a risk level.

	Standard clinical thresholds:
	  0 → Low
	  1 → Medium
	  ≥ 2 → High
	"""
	if total_score >= 2:
		return "High"
	if total_score == 1:
		return "Medium"
	return "Low"


# ── Risk Classification Lookup ───────────────────────────────────────

RISK_CLASSIFIERS = {
	MORSE_TEMPLATE: ("custom_fall_risk_level", classify_fall_risk),
	BRADEN_TEMPLATE: ("custom_pressure_risk_level", classify_braden_risk),
	MUST_TEMPLATE: ("custom_nutrition_risk_level", classify_nutrition_risk),
}


# ── Allergy Data Extraction ─────────────────────────────────────────


def extract_allergy_data(intake_assessment: str) -> tuple[bool, str]:
	"""Extract allergy alert status and summary from an intake assessment.

	Returns:
		Tuple of (has_allergy: bool, summary: str).
	"""
	responses = frappe.get_all(
		"IPD Intake Assessment Response",
		filters={"parent": intake_assessment},
		fields=["field_label", "text_value"],
	)

	allergy_type = ""
	allergy_details = ""

	for r in responses:
		if r.field_label == _ALLERGY_FIELD_LABEL:
			allergy_type = (r.text_value or "").strip()
		elif r.field_label == _ALLERGY_DETAILS_LABEL:
			allergy_details = (r.text_value or "").strip()

	if not allergy_type or allergy_type == _ALLERGY_NONE_VALUE:
		return False, ""

	summary = allergy_type
	if allergy_details:
		summary = f"{allergy_type}: {allergy_details}"

	return True, summary


# ── Scored Assessment Queries ────────────────────────────────────────


def _get_latest_score(inpatient_record: str, template_name: str) -> int | None:
	"""Return the total score from the most recently submitted Patient
	Assessment for a given template and Inpatient Record."""
	pa = frappe.get_all(
		"Patient Assessment",
		filters={
			"custom_inpatient_record": inpatient_record,
			"assessment_template": template_name,
			"docstatus": 1,
		},
		fields=["name", "total_score"],
		order_by="assessment_datetime desc",
		limit=1,
	)

	if not pa:
		return None

	return int(pa[0].total_score or 0)


# ── Composite Risk Flag Update ───────────────────────────────────────


def update_risk_flags(inpatient_record: str) -> dict:
	"""Recompute all nursing risk flags for an Inpatient Record and persist
	the results as custom fields.

	Returns:
		Dict with the computed risk values.
	"""
	flags: dict[str, str | int] = {}

	for template_name, (fieldname, classifier) in RISK_CLASSIFIERS.items():
		score = _get_latest_score(inpatient_record, template_name)
		if score is not None:
			flags[fieldname] = classifier(score)

	# Allergy data from the first linked intake assessment
	intake_name = frappe.db.get_value(
		"Inpatient Record", inpatient_record, "custom_intake_assessment"
	)
	if intake_name:
		has_allergy, summary = extract_allergy_data(intake_name)
		flags["custom_allergy_alert"] = 1 if has_allergy else 0
		flags["custom_allergy_summary"] = summary

	if not flags:
		return {}

	flags["custom_risk_flags_updated_on"] = now_datetime()
	flags["custom_risk_flags_updated_by"] = frappe.session.user

	frappe.db.set_value("Inpatient Record", inpatient_record, flags, update_modified=False)

	from alcura_ipd_ext.services.nursing_alert_service import raise_risk_alerts

	raise_risk_alerts(inpatient_record, flags)

	return flags


def get_risk_summary(inpatient_record: str) -> dict:
	"""Return the current risk flag values for an Inpatient Record."""
	fields = [
		"custom_fall_risk_level",
		"custom_pressure_risk_level",
		"custom_nutrition_risk_level",
		"custom_allergy_alert",
		"custom_allergy_summary",
		"custom_risk_flags_updated_on",
		"custom_risk_flags_updated_by",
		"patient",
		"patient_name",
		"custom_current_ward",
		"custom_current_bed",
	]

	values = frappe.db.get_value("Inpatient Record", inpatient_record, fields, as_dict=True)
	if not values:
		return {}

	return {
		"inpatient_record": inpatient_record,
		"fall_risk_level": values.get("custom_fall_risk_level") or "",
		"pressure_risk_level": values.get("custom_pressure_risk_level") or "",
		"nutrition_risk_level": values.get("custom_nutrition_risk_level") or "",
		"allergy_alert": values.get("custom_allergy_alert") or 0,
		"allergy_summary": values.get("custom_allergy_summary") or "",
		"updated_on": str(values.get("custom_risk_flags_updated_on") or ""),
		"updated_by": values.get("custom_risk_flags_updated_by") or "",
		"patient": values.get("patient") or "",
		"patient_name": values.get("patient_name") or "",
		"ward": values.get("custom_current_ward") or "",
		"bed": values.get("custom_current_bed") or "",
	}


def get_ward_risk_overview(ward: str | None = None, company: str | None = None) -> list[dict]:
	"""Return risk summaries for all admitted patients, optionally filtered by ward."""
	filters = {"status": "Admitted"}
	if ward:
		filters["custom_current_ward"] = ward
	if company:
		filters["company"] = company

	records = frappe.get_all(
		"Inpatient Record",
		filters=filters,
		fields=[
			"name",
			"patient",
			"patient_name",
			"custom_current_ward",
			"custom_current_room",
			"custom_current_bed",
			"primary_practitioner",
			"custom_fall_risk_level",
			"custom_pressure_risk_level",
			"custom_nutrition_risk_level",
			"custom_allergy_alert",
			"custom_allergy_summary",
			"custom_risk_flags_updated_on",
		],
		order_by="custom_current_ward asc, custom_current_bed asc",
	)

	return [
		{
			"inpatient_record": r.name,
			"patient": r.patient,
			"patient_name": r.patient_name,
			"ward": r.custom_current_ward or "",
			"room": r.custom_current_room or "",
			"bed": r.custom_current_bed or "",
			"consultant": r.primary_practitioner or "",
			"fall_risk_level": r.custom_fall_risk_level or "",
			"pressure_risk_level": r.custom_pressure_risk_level or "",
			"nutrition_risk_level": r.custom_nutrition_risk_level or "",
			"allergy_alert": r.custom_allergy_alert or 0,
			"allergy_summary": r.custom_allergy_summary or "",
			"updated_on": str(r.custom_risk_flags_updated_on or ""),
		}
		for r in records
	]
