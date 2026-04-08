"""Fixture data for IPD Intake Assessments.

Creates:
- Patient Assessment Parameters for standard clinical scales
- Patient Assessment Templates for GCS, Pain NRS, Morse Fall, Braden
- IPD Intake Assessment Templates for 6 hospital specialties

Safe to call repeatedly — uses insert(ignore_if_duplicate=True) or
existence checks before creation.
"""

from __future__ import annotations

import frappe
from frappe import _


MODULE = "Alcura IPD Extensions"


# ── Patient Assessment Parameters ────────────────────────────────────

PARAMETERS = [
	# GCS
	"Eye Opening",
	"Verbal Response",
	"Motor Response",
	# Pain NRS
	"Pain Intensity",
	# Morse Fall Risk Scale
	"History of Falling",
	"Secondary Diagnosis",
	"Ambulatory Aid",
	"IV / Heparin Lock",
	"Gait",
	"Mental Status",
	# Braden Scale
	"Sensory Perception",
	"Moisture",
	"Activity",
	"Mobility",
	"Nutrition",
	"Friction and Shear",
	# MUST Nutritional Screening
	"BMI Score",
	"Weight Loss Score",
	"Acute Disease Effect Score",
]


# ── Scored Assessment Templates ──────────────────────────────────────

SCORED_TEMPLATES = [
	{
		"assessment_name": "Glasgow Coma Scale (GCS)",
		"assessment_description": "Standardised 3–15 point neurological scale for level of consciousness.",
		"scale_min": 1,
		"scale_max": 6,
		"parameters": ["Eye Opening", "Verbal Response", "Motor Response"],
		"custom_assessment_context": "Intake",
		"custom_ipd_sort_order": 10,
		"custom_is_ipd_active": 1,
	},
	{
		"assessment_name": "Numeric Pain Rating Scale (NRS)",
		"assessment_description": "0–10 self-reported pain intensity scale.",
		"scale_min": 0,
		"scale_max": 10,
		"parameters": ["Pain Intensity"],
		"custom_assessment_context": "Intake",
		"custom_ipd_sort_order": 20,
		"custom_is_ipd_active": 1,
	},
	{
		"assessment_name": "Morse Fall Scale",
		"assessment_description": "Nurse-administered fall risk assessment; total ≥45 = high risk.",
		"scale_min": 0,
		"scale_max": 4,
		"parameters": [
			"History of Falling",
			"Secondary Diagnosis",
			"Ambulatory Aid",
			"IV / Heparin Lock",
			"Gait",
			"Mental Status",
		],
		"custom_assessment_context": "Intake",
		"custom_ipd_sort_order": 30,
		"custom_is_ipd_active": 1,
	},
	{
		"assessment_name": "Braden Scale",
		"assessment_description": "Pressure ulcer risk assessment; total ≤18 indicates risk.",
		"scale_min": 1,
		"scale_max": 4,
		"parameters": [
			"Sensory Perception",
			"Moisture",
			"Activity",
			"Mobility",
			"Nutrition",
			"Friction and Shear",
		],
		"custom_assessment_context": "Intake",
		"custom_ipd_sort_order": 40,
		"custom_is_ipd_active": 1,
	},
	{
		"assessment_name": "MUST Nutritional Screening",
		"assessment_description": "Malnutrition Universal Screening Tool; score ≥2 = high risk.",
		"scale_min": 0,
		"scale_max": 2,
		"parameters": [
			"BMI Score",
			"Weight Loss Score",
			"Acute Disease Effect Score",
		],
		"custom_assessment_context": "Intake",
		"custom_ipd_sort_order": 50,
		"custom_is_ipd_active": 1,
	},
]


# ── IPD Intake Assessment Templates ─────────────────────────────────

# Field type abbreviations for readability
_T = "Text"
_LT = "Long Text"
_ST = "Small Text"
_S = "Select"
_C = "Check"
_I = "Int"
_F = "Float"

# Common nursing intake fields reused across specialties
_COMMON_NURSING_FIELDS = [
	# ── Vitals on Admission ──
	("Vitals on Admission", "Blood Pressure (mmHg)", _T, "", 0, 10),
	("Vitals on Admission", "Pulse Rate (bpm)", _I, "", 0, 20),
	("Vitals on Admission", "Temperature (°F)", _F, "", 0, 30),
	("Vitals on Admission", "SpO2 (%)", _I, "", 0, 40),
	("Vitals on Admission", "Respiratory Rate", _I, "", 0, 50),
	("Vitals on Admission", "Weight (kg)", _F, "", 0, 60),
	("Vitals on Admission", "Height (cm)", _F, "", 0, 70),
	# ── Chief Complaint ──
	("Chief Complaint", "Chief Complaint", _ST, "", 1, 80),
	("Chief Complaint", "Duration of Symptoms", _T, "", 0, 90),
	# ── Allergy Status ──
	("Allergy Status", "Known Allergies", _S, "None Known\nDrug Allergy\nFood Allergy\nEnvironmental\nMultiple", 1, 100),
	("Allergy Status", "Allergy Details", _ST, "", 0, 110),
	# ── General Status ──
	("General Status", "Consciousness Level", _S, "Alert\nVerbal\nPain\nUnresponsive", 1, 120),
	("General Status", "Orientation", _S, "Oriented\nConfused\nDisoriented", 0, 130),
	("General Status", "Mobility Status", _S, "Ambulatory\nWith Assistance\nWheelchair\nBed-bound", 1, 140),
	("General Status", "Fall Risk Identified", _C, "", 0, 150),
	# ── Skin Assessment ──
	("Skin Assessment", "Skin Integrity", _S, "Intact\nWound Present\nPressure Injury\nSurgical Site\nOther", 0, 160),
	("Skin Assessment", "Skin Notes", _ST, "", 0, 170),
	# ── Diet & Nutrition ──
	("Diet & Nutrition", "Current Diet", _S, "Regular\nSoft\nLiquid\nNPO\nDiabetic\nRenal\nOther", 0, 180),
	("Diet & Nutrition", "Dietary Restrictions", _ST, "", 0, 190),
	("Diet & Nutrition", "Swallowing Difficulty", _C, "", 0, 200),
	("Diet & Nutrition", "Feeding Assistance Required", _S, "Independent\nPartial\nFull", 0, 210),
	# ── Elimination ──
	("Elimination", "Bowel Pattern", _S, "Normal\nConstipation\nDiarrhea\nIncontinence\nOstomy", 0, 220),
	("Elimination", "Last Bowel Movement", _T, "", 0, 230),
	("Elimination", "Bladder Function", _S, "Normal\nIncontinence\nRetention\nCatheterized", 0, 240),
	("Elimination", "Urinary Catheter Present", _C, "", 0, 250),
	("Elimination", "Catheter Details", _T, "", 0, 260),
	# ── Device Lines & Access ──
	("Device Lines & Access", "IV Access Present", _C, "", 0, 270),
	("Device Lines & Access", "IV Access Site/Type", _T, "", 0, 280),
	("Device Lines & Access", "Central Line Present", _C, "", 0, 290),
	("Device Lines & Access", "Central Line Details", _T, "", 0, 300),
	("Device Lines & Access", "Arterial Line Present", _C, "", 0, 310),
	("Device Lines & Access", "Nasogastric/Feeding Tube", _C, "", 0, 320),
	("Device Lines & Access", "Drain/Tube Present", _C, "", 0, 330),
	("Device Lines & Access", "Drain Details", _T, "", 0, 340),
	("Device Lines & Access", "Other Devices", _ST, "", 0, 350),
	# ── Patient Belongings ──
	("Patient Belongings", "Valuables Secured", _C, "", 0, 360),
	("Patient Belongings", "Belongings Notes", _T, "", 0, 370),
]

# Common doctor intake fields
_COMMON_DOCTOR_FIELDS = [
	("History of Present Illness", "Chief Complaint", _ST, "", 1, 10),
	("History of Present Illness", "History of Present Illness", _LT, "", 1, 20),
	("History of Present Illness", "Duration", _T, "", 0, 30),
	("Past History", "Past Medical History", _LT, "", 0, 40),
	("Past History", "Past Surgical History", _ST, "", 0, 50),
	("Past History", "Drug History", _ST, "", 0, 60),
	("Past History", "Family History", _ST, "", 0, 70),
	("Past History", "Social History", _ST, "", 0, 80),
	("Review of Systems", "Cardiovascular", _T, "", 0, 90),
	("Review of Systems", "Respiratory", _T, "", 0, 100),
	("Review of Systems", "Gastrointestinal", _T, "", 0, 110),
	("Review of Systems", "Genitourinary", _T, "", 0, 120),
	("Review of Systems", "Neurological", _T, "", 0, 130),
	("Review of Systems", "Musculoskeletal", _T, "", 0, 140),
	("Physical Examination", "General Examination", _LT, "", 1, 150),
	("Physical Examination", "Systemic Examination", _LT, "", 0, 160),
	("Assessment & Plan", "Provisional Diagnosis", _ST, "", 1, 170),
	("Assessment & Plan", "Plan of Care", _LT, "", 1, 180),
]


def _field_row(section, label, ftype, options, mandatory, order, role="All"):
	return {
		"section_label": section,
		"field_label": label,
		"field_type": ftype,
		"options": options,
		"is_mandatory": mandatory,
		"display_order": order,
		"role_visibility": role,
	}


INTAKE_TEMPLATES = [
	{
		"template_name": "General Medicine — Nursing Intake",
		"target_role": "Nursing User",
		"description": "Standard nursing intake assessment for general medicine admissions.",
		"fields": [_field_row(*f) for f in _COMMON_NURSING_FIELDS],
		"scored": [
			"Numeric Pain Rating Scale (NRS)",
			"Morse Fall Scale",
			"Braden Scale",
			"MUST Nutritional Screening",
		],
	},
	{
		"template_name": "General Medicine — Doctor Intake",
		"target_role": "Physician",
		"description": "Initial medical assessment for general medicine admissions.",
		"fields": [_field_row(*f) for f in _COMMON_DOCTOR_FIELDS],
		"scored": ["Glasgow Coma Scale (GCS)"],
	},
	{
		"template_name": "Surgery — Nursing Intake",
		"target_role": "Nursing User",
		"description": "Pre-surgical nursing intake assessment.",
		"fields": [_field_row(*f) for f in _COMMON_NURSING_FIELDS] + [
			_field_row("Surgical Prep", "NPO Status", _S, "NPO\nNot NPO", 1, 380),
			_field_row("Surgical Prep", "Consent for Surgery Obtained", _C, "", 1, 390),
			_field_row("Surgical Prep", "Surgical Site Marking", _C, "", 0, 400),
			_field_row("Surgical Prep", "Pre-op Checklist Complete", _C, "", 0, 410),
		],
		"scored": [
			"Numeric Pain Rating Scale (NRS)",
			"Morse Fall Scale",
			"Braden Scale",
		],
	},
	{
		"template_name": "ICU — Nursing Intake",
		"target_role": "Nursing User",
		"description": "Critical care nursing intake assessment.",
		"fields": [_field_row(*f) for f in _COMMON_NURSING_FIELDS] + [
			_field_row("ICU Specific", "Ventilator Support", _S, "None\nNon-Invasive\nInvasive", 1, 380),
			_field_row("ICU Specific", "Ventilator Settings", _T, "", 0, 390),
			_field_row("ICU Specific", "Sedation Score", _S, "0 - Alert\n1 - Drowsy\n2 - Light Sedation\n3 - Moderate\n4 - Deep\n5 - Unarousable", 0, 400),
			_field_row("ICU Specific", "Vasopressor Support", _C, "", 0, 410),
		],
		"scored": [
			"Glasgow Coma Scale (GCS)",
			"Numeric Pain Rating Scale (NRS)",
			"Braden Scale",
		],
	},
	{
		"template_name": "Pediatrics — Nursing Intake",
		"target_role": "Nursing User",
		"description": "Pediatric nursing intake assessment.",
		"fields": [
			_field_row("Vitals on Admission", "Blood Pressure (mmHg)", _T, "", 0, 10),
			_field_row("Vitals on Admission", "Pulse Rate (bpm)", _I, "", 0, 20),
			_field_row("Vitals on Admission", "Temperature (°F)", _F, "", 0, 30),
			_field_row("Vitals on Admission", "SpO2 (%)", _I, "", 0, 40),
			_field_row("Vitals on Admission", "Respiratory Rate", _I, "", 0, 50),
			_field_row("Vitals on Admission", "Weight (kg)", _F, "", 1, 60),
			_field_row("Vitals on Admission", "Height (cm)", _F, "", 0, 70),
			_field_row("Chief Complaint", "Chief Complaint", _ST, "", 1, 80),
			_field_row("Chief Complaint", "Duration of Symptoms", _T, "", 0, 90),
			_field_row("Allergy Status", "Known Allergies", _S, "None Known\nDrug Allergy\nFood Allergy\nEnvironmental\nMultiple", 1, 100),
			_field_row("Allergy Status", "Allergy Details", _ST, "", 0, 110),
			_field_row("Pediatric Assessment", "Age (Months)", _I, "", 0, 120),
			_field_row("Pediatric Assessment", "Immunisation Status", _S, "Up to Date\nPartially Immunised\nNot Immunised\nUnknown", 0, 130),
			_field_row("Pediatric Assessment", "Feeding Pattern", _S, "Breastfed\nFormula Fed\nMixed\nSolid Foods\nAge Appropriate Diet", 0, 140),
			_field_row("Pediatric Assessment", "Developmental Milestones", _S, "Age Appropriate\nDelayed\nNot Assessed", 0, 150),
			_field_row("Parent / Guardian", "Parent/Guardian Present", _C, "", 1, 160),
			_field_row("Parent / Guardian", "Parent/Guardian Name", _T, "", 0, 170),
			_field_row("Parent / Guardian", "Contact Number", _T, "", 0, 180),
		],
		"scored": [
			"Numeric Pain Rating Scale (NRS)",
		],
	},
	{
		"template_name": "Obstetrics — Nursing Intake",
		"target_role": "Nursing User",
		"description": "Obstetric nursing intake assessment.",
		"fields": [_field_row(*f) for f in _COMMON_NURSING_FIELDS] + [
			_field_row("Obstetric History", "Gravida", _I, "", 1, 380),
			_field_row("Obstetric History", "Para", _I, "", 1, 390),
			_field_row("Obstetric History", "Abortion", _I, "", 0, 400),
			_field_row("Obstetric History", "Living", _I, "", 0, 410),
			_field_row("Obstetric History", "Gestational Age (Weeks)", _I, "", 0, 420),
			_field_row("Obstetric History", "Expected Date of Delivery", "Date", "", 0, 430),
			_field_row("Obstetric Status", "Fetal Heart Rate (bpm)", _I, "", 0, 440),
			_field_row("Obstetric Status", "Contractions Present", _C, "", 0, 450),
			_field_row("Obstetric Status", "Membrane Status", _S, "Intact\nRuptured\nUnknown", 0, 460),
			_field_row("Obstetric Status", "Cervical Dilation (cm)", _I, "", 0, 470),
			_field_row("Obstetric Status", "Blood Group", _S, "A+\nA-\nB+\nB-\nAB+\nAB-\nO+\nO-", 0, 480),
		],
		"scored": [
			"Numeric Pain Rating Scale (NRS)",
			"Morse Fall Scale",
		],
	},
]


# ── Setup Functions ──────────────────────────────────────────────────


def setup_intake_fixtures():
	"""Create all intake assessment fixture data. Safe to call repeatedly."""
	_create_parameters()
	_create_scored_templates()
	_create_intake_templates()
	frappe.logger("alcura_ipd_ext").info("Intake assessment fixtures installed.")


def _create_parameters():
	for param_name in PARAMETERS:
		if not frappe.db.exists("Patient Assessment Parameter", param_name):
			frappe.get_doc({
				"doctype": "Patient Assessment Parameter",
				"assessment_parameter": param_name,
			}).insert(ignore_permissions=True)


def _create_scored_templates():
	for tmpl in SCORED_TEMPLATES:
		name = tmpl["assessment_name"]
		if frappe.db.exists("Patient Assessment Template", name):
			# Update IPD custom fields on existing template
			doc = frappe.get_doc("Patient Assessment Template", name)
			doc.db_set({
				"custom_assessment_context": tmpl.get("custom_assessment_context", ""),
				"custom_ipd_sort_order": tmpl.get("custom_ipd_sort_order", 0),
				"custom_is_ipd_active": tmpl.get("custom_is_ipd_active", 0),
			}, update_modified=False)
			continue

		doc = frappe.get_doc({
			"doctype": "Patient Assessment Template",
			"assessment_name": name,
			"assessment_description": tmpl["assessment_description"],
			"scale_min": tmpl["scale_min"],
			"scale_max": tmpl["scale_max"],
			"custom_assessment_context": tmpl.get("custom_assessment_context", ""),
			"custom_ipd_sort_order": tmpl.get("custom_ipd_sort_order", 0),
			"custom_is_ipd_active": tmpl.get("custom_is_ipd_active", 0),
		})

		for param_name in tmpl["parameters"]:
			doc.append("parameters", {"assessment_parameter": param_name})

		doc.insert(ignore_permissions=True)


def _create_intake_templates():
	for tmpl in INTAKE_TEMPLATES:
		name = tmpl["template_name"]
		if frappe.db.exists("IPD Intake Assessment Template", name):
			continue

		doc = frappe.get_doc({
			"doctype": "IPD Intake Assessment Template",
			"template_name": name,
			"target_role": tmpl["target_role"],
			"description": tmpl.get("description", ""),
			"is_active": 1,
			"version": 1,
		})

		for field_data in tmpl["fields"]:
			doc.append("form_fields", field_data)

		for scored_name in tmpl.get("scored", []):
			if frappe.db.exists("Patient Assessment Template", scored_name):
				doc.append("scored_assessments", {
					"assessment_template": scored_name,
					"is_mandatory": 0,
				})

		doc.insert(ignore_permissions=True)


def teardown_intake_fixtures():
	"""Remove fixture data created by this module (used during uninstall)."""
	for tmpl in INTAKE_TEMPLATES:
		name = tmpl["template_name"]
		if frappe.db.exists("IPD Intake Assessment Template", name):
			frappe.delete_doc("IPD Intake Assessment Template", name, force=True)

	for tmpl in SCORED_TEMPLATES:
		name = tmpl["assessment_name"]
		if frappe.db.exists("Patient Assessment Template", name):
			frappe.delete_doc("Patient Assessment Template", name, force=True)
