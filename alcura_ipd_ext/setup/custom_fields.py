"""Custom field definitions for alcura_ipd_ext.

All custom fields are tagged with module = "Alcura IPD Extensions" so they
are picked up by the fixture export filter in hooks.py.
"""

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

IPD_ROOM_CATEGORY_OPTIONS = (
	"\nGeneral\nTwin Sharing\nSemi-Private\nPrivate\nDeluxe\nSuite"
	"\nICU\nCICU\nMICU\nNICU\nPICU\nSICU\nHDU\nBurns\nIsolation\nOther"
)

OCCUPANCY_CLASS_OPTIONS = "\nSingle\nDouble\nTriple\nMulti-Bed\nDormitory"

NURSING_INTENSITY_OPTIONS = "\nStandard\nEnhanced\nHigh\nCritical"

EMERGENCY_CONTACT_RELATION_OPTIONS = (
	"\nParent\nSpouse\nChild\nSibling\nGuardian\nOther"
)

ADMISSION_PRIORITY_OPTIONS = "\nRoutine\nUrgent\nEmergency"

IPD_NOTE_TYPE_OPTIONS = (
	"\nAdmission Note\nProgress Note\nProcedure Note"
	"\nConsultation Note\nDischarge Summary"
)

MODULE = "Alcura IPD Extensions"
DEPENDS_ON_IPD = "eval:doc.inpatient_occupancy"


def get_custom_fields() -> dict[str, list[dict]]:
	"""Return the map of {doctype: [field_defs]} to be installed."""
	return {
		"Patient": _patient_fields(),
		"Patient Encounter": _patient_encounter_fields(),
		"Inpatient Record": _inpatient_record_fields(),
		"Patient Assessment Template": _patient_assessment_template_fields(),
		"Patient Assessment": _patient_assessment_fields(),
		"Healthcare Service Unit Type": [
			# ── IPD Room Classification section ──────────────────────
			{
				"fieldname": "ipd_classification_section",
				"fieldtype": "Section Break",
				"label": "IPD Room Classification",
				"insert_after": "disabled",
				"depends_on": DEPENDS_ON_IPD,
				"module": MODULE,
			},
			{
				"fieldname": "ipd_room_category",
				"fieldtype": "Select",
				"label": "IPD Room Category",
				"options": IPD_ROOM_CATEGORY_OPTIONS,
				"insert_after": "ipd_classification_section",
				"depends_on": DEPENDS_ON_IPD,
				"in_standard_filter": 1,
				"module": MODULE,
			},
			{
				"fieldname": "occupancy_class",
				"fieldtype": "Select",
				"label": "Occupancy Class",
				"options": OCCUPANCY_CLASS_OPTIONS,
				"insert_after": "ipd_room_category",
				"depends_on": DEPENDS_ON_IPD,
				"module": MODULE,
			},
			{
				"fieldname": "column_break_ipd_1",
				"fieldtype": "Column Break",
				"insert_after": "occupancy_class",
				"depends_on": DEPENDS_ON_IPD,
				"module": MODULE,
			},
			{
				"fieldname": "nursing_intensity",
				"fieldtype": "Select",
				"label": "Nursing Intensity",
				"options": NURSING_INTENSITY_OPTIONS,
				"insert_after": "column_break_ipd_1",
				"depends_on": DEPENDS_ON_IPD,
				"module": MODULE,
			},
			{
				"fieldname": "is_critical_care_unit",
				"fieldtype": "Check",
				"label": "Is Critical Care Unit",
				"insert_after": "nursing_intensity",
				"depends_on": DEPENDS_ON_IPD,
				"read_only": 1,
				"module": MODULE,
			},
			{
				"fieldname": "supports_isolation",
				"fieldtype": "Check",
				"label": "Supports Isolation",
				"insert_after": "is_critical_care_unit",
				"depends_on": DEPENDS_ON_IPD,
				"module": MODULE,
			},
			# ── Package & Tariff section ─────────────────────────────
			{
				"fieldname": "ipd_tariff_section",
				"fieldtype": "Section Break",
				"label": "Package & Tariff",
				"insert_after": "supports_isolation",
				"depends_on": DEPENDS_ON_IPD,
				"collapsible": 1,
				"module": MODULE,
			},
			{
				"fieldname": "package_eligible",
				"fieldtype": "Check",
				"label": "Package Eligible",
				"insert_after": "ipd_tariff_section",
				"depends_on": DEPENDS_ON_IPD,
				"module": MODULE,
			},
			{
				"fieldname": "column_break_ipd_2",
				"fieldtype": "Column Break",
				"insert_after": "package_eligible",
				"depends_on": DEPENDS_ON_IPD,
				"module": MODULE,
			},
			{
				"fieldname": "default_price_list",
				"fieldtype": "Link",
				"label": "Default Price List",
				"options": "Price List",
				"insert_after": "column_break_ipd_2",
				"depends_on": DEPENDS_ON_IPD,
				"module": MODULE,
			},
		],
	}


def _patient_fields() -> list[dict]:
	"""Custom fields added to the standard Patient for Indian statutory IDs,
	emergency contact, and consent tracking."""
	return [
		# ── Indian Statutory Identifiers ─────────────────────────
		{
			"fieldname": "custom_indian_ids_section",
			"fieldtype": "Section Break",
			"label": "Indian Statutory Identifiers",
			"insert_after": "uid",
			"module": MODULE,
		},
		{
			"fieldname": "custom_aadhaar_number",
			"fieldtype": "Data",
			"label": "Aadhaar Number",
			"insert_after": "custom_indian_ids_section",
			"length": 12,
			"search_index": 1,
			"module": MODULE,
		},
		{
			"fieldname": "custom_abha_number",
			"fieldtype": "Data",
			"label": "ABHA Number",
			"insert_after": "custom_aadhaar_number",
			"length": 14,
			"search_index": 1,
			"module": MODULE,
		},
		{
			"fieldname": "custom_abha_address",
			"fieldtype": "Data",
			"label": "ABHA Address",
			"insert_after": "custom_abha_number",
			"description": "e.g. username@abdm",
			"module": MODULE,
		},
		{
			"fieldname": "custom_column_break_ids_1",
			"fieldtype": "Column Break",
			"insert_after": "custom_abha_address",
			"module": MODULE,
		},
		{
			"fieldname": "custom_pan_number",
			"fieldtype": "Data",
			"label": "PAN Number",
			"insert_after": "custom_column_break_ids_1",
			"length": 10,
			"module": MODULE,
		},
		{
			"fieldname": "custom_mr_number",
			"fieldtype": "Data",
			"label": "MR Number",
			"insert_after": "custom_pan_number",
			"unique": 1,
			"search_index": 1,
			"in_standard_filter": 1,
			"description": "Hospital Medical Record Number",
			"module": MODULE,
		},
		# ── Emergency Contact ────────────────────────────────────
		{
			"fieldname": "custom_emergency_contact_section",
			"fieldtype": "Section Break",
			"label": "Emergency Contact",
			"insert_after": "phone",
			"collapsible": 1,
			"module": MODULE,
		},
		{
			"fieldname": "custom_emergency_contact_name",
			"fieldtype": "Data",
			"label": "Emergency Contact Name",
			"insert_after": "custom_emergency_contact_section",
			"module": MODULE,
		},
		{
			"fieldname": "custom_emergency_contact_relation",
			"fieldtype": "Select",
			"label": "Relation",
			"options": EMERGENCY_CONTACT_RELATION_OPTIONS,
			"insert_after": "custom_emergency_contact_name",
			"module": MODULE,
		},
		{
			"fieldname": "custom_column_break_emergency_1",
			"fieldtype": "Column Break",
			"insert_after": "custom_emergency_contact_relation",
			"module": MODULE,
		},
		{
			"fieldname": "custom_emergency_contact_phone",
			"fieldtype": "Data",
			"label": "Emergency Contact Phone",
			"insert_after": "custom_column_break_emergency_1",
			"options": "Phone",
			"module": MODULE,
		},
		{
			"fieldname": "custom_emergency_contact_address",
			"fieldtype": "Small Text",
			"label": "Emergency Contact Address",
			"insert_after": "custom_emergency_contact_phone",
			"module": MODULE,
		},
		# ── Consent and Privacy ──────────────────────────────────
		{
			"fieldname": "custom_consent_section",
			"fieldtype": "Section Break",
			"label": "Consent and Privacy",
			"insert_after": "custom_emergency_contact_address",
			"collapsible": 1,
			"module": MODULE,
		},
		{
			"fieldname": "custom_consent_collected",
			"fieldtype": "Check",
			"label": "Consent Collected",
			"insert_after": "custom_consent_section",
			"module": MODULE,
		},
		{
			"fieldname": "custom_consent_datetime",
			"fieldtype": "Datetime",
			"label": "Consent Date/Time",
			"insert_after": "custom_consent_collected",
			"read_only": 1,
			"module": MODULE,
		},
		{
			"fieldname": "custom_consent_given_by",
			"fieldtype": "Data",
			"label": "Consent Given By",
			"insert_after": "custom_consent_datetime",
			"description": "Name of person giving consent (if not the patient)",
			"module": MODULE,
		},
		{
			"fieldname": "custom_column_break_consent_1",
			"fieldtype": "Column Break",
			"insert_after": "custom_consent_given_by",
			"module": MODULE,
		},
		{
			"fieldname": "custom_privacy_notice_acknowledged",
			"fieldtype": "Check",
			"label": "Privacy Notice Acknowledged",
			"insert_after": "custom_column_break_consent_1",
			"module": MODULE,
		},
		# ── Payer Profile ────────────────────────────────────────
		{
			"fieldname": "custom_payer_profile_section",
			"fieldtype": "Section Break",
			"label": "Default Payer",
			"insert_after": "custom_privacy_notice_acknowledged",
			"collapsible": 1,
			"module": MODULE,
		},
		{
			"fieldname": "custom_default_payer_profile",
			"fieldtype": "Link",
			"label": "Default Payer Profile",
			"options": "Patient Payer Profile",
			"insert_after": "custom_payer_profile_section",
			"description": "Preferred payer profile used as default during admission",
			"module": MODULE,
		},
	]


def _patient_encounter_fields() -> list[dict]:
	"""Custom fields added to Patient Encounter for IPD admission ordering
	and consultant clinical documentation (US-D1, US-E3)."""
	return [
		# ── US-D1: IPD Admission Order ───────────────────────────
		{
			"fieldname": "custom_ipd_admission_section",
			"fieldtype": "Section Break",
			"label": "IPD Admission Order",
			"insert_after": "encounter_comment",
			"collapsible": 1,
			"module": MODULE,
		},
		{
			"fieldname": "custom_ipd_admission_ordered",
			"fieldtype": "Check",
			"label": "IPD Admission Ordered",
			"insert_after": "custom_ipd_admission_section",
			"read_only": 1,
			"module": MODULE,
		},
		{
			"fieldname": "custom_ipd_inpatient_record",
			"fieldtype": "Link",
			"label": "Inpatient Record",
			"options": "Inpatient Record",
			"insert_after": "custom_ipd_admission_ordered",
			"read_only": 1,
			"module": MODULE,
		},
		*_patient_encounter_consultation_fields(),
	]


def _patient_encounter_consultation_fields() -> list[dict]:
	"""US-E3/E5: IPD consultation note fields on Patient Encounter.

	Adds note-type categorisation, IR linking, and structured clinical
	documentation sections (history, examination, assessment/plan).
	US-E5 adds progress-note-specific fields (overnight events, active
	problems snapshot).
	All clinical sections are hidden unless the encounter is an IPD note.
	"""
	depends_on_note = 'eval:doc.custom_ipd_note_type'
	depends_on_progress = "eval:doc.custom_ipd_note_type === 'Progress Note'"
	return [
		# ── IPD Consultation Context ─────────────────────────────
		{
			"fieldname": "custom_ipd_consultation_section",
			"fieldtype": "Section Break",
			"label": "IPD Consultation",
			"insert_after": "custom_ipd_inpatient_record",
			"collapsible": 1,
			"module": MODULE,
		},
		{
			"fieldname": "custom_linked_inpatient_record",
			"fieldtype": "Link",
			"label": "Inpatient Record",
			"options": "Inpatient Record",
			"insert_after": "custom_ipd_consultation_section",
			"search_index": 1,
			"module": MODULE,
		},
		{
			"fieldname": "custom_ipd_note_type",
			"fieldtype": "Select",
			"label": "Note Type",
			"options": IPD_NOTE_TYPE_OPTIONS,
			"insert_after": "custom_linked_inpatient_record",
			"in_standard_filter": 1,
			"depends_on": "eval:doc.custom_linked_inpatient_record",
			"mandatory_depends_on": "eval:doc.custom_linked_inpatient_record",
			"module": MODULE,
		},
		{
			"fieldname": "custom_column_break_consult_1",
			"fieldtype": "Column Break",
			"insert_after": "custom_ipd_note_type",
			"module": MODULE,
		},
		{
			"fieldname": "custom_ipd_note_summary",
			"fieldtype": "Small Text",
			"label": "Note Summary",
			"insert_after": "custom_column_break_consult_1",
			"depends_on": depends_on_note,
			"description": "Brief summary for list view and dashboard display",
			"module": MODULE,
		},
		# ── US-F1: Clinical Order flag ──────────────────────────
		{
			"fieldname": "custom_has_ipd_orders",
			"fieldtype": "Check",
			"label": "Has IPD Orders",
			"insert_after": "custom_ipd_note_summary",
			"read_only": 1,
			"module": MODULE,
		},
		# ── US-E5: Progress Note Fields ─────────────────────────
		{
			"fieldname": "custom_progress_note_section",
			"fieldtype": "Section Break",
			"label": "Progress Note Context",
			"insert_after": "custom_ipd_note_summary",
			"depends_on": depends_on_progress,
			"module": MODULE,
		},
		{
			"fieldname": "custom_active_problems_text",
			"fieldtype": "Small Text",
			"label": "Active Problems",
			"insert_after": "custom_progress_note_section",
			"read_only": 1,
			"description": "Snapshot of active problems at the time of this note",
			"module": MODULE,
		},
		{
			"fieldname": "custom_column_break_progress_1",
			"fieldtype": "Column Break",
			"insert_after": "custom_active_problems_text",
			"module": MODULE,
		},
		{
			"fieldname": "custom_overnight_events",
			"fieldtype": "Small Text",
			"label": "Overnight / Interval Events",
			"insert_after": "custom_column_break_progress_1",
			"description": "Events since last round",
			"module": MODULE,
		},
		# ── Clinical History ─────────────────────────────────────
		{
			"fieldname": "custom_clinical_history_section",
			"fieldtype": "Section Break",
			"label": "Clinical History",
			"insert_after": "custom_overnight_events",
			"depends_on": depends_on_note,
			"module": MODULE,
		},
		{
			"fieldname": "custom_chief_complaint_text",
			"fieldtype": "Small Text",
			"label": "Chief Complaint",
			"insert_after": "custom_clinical_history_section",
			"module": MODULE,
		},
		{
			"fieldname": "custom_history_of_present_illness",
			"fieldtype": "Text Editor",
			"label": "History of Present Illness",
			"insert_after": "custom_chief_complaint_text",
			"module": MODULE,
		},
		{
			"fieldname": "custom_column_break_history_1",
			"fieldtype": "Column Break",
			"insert_after": "custom_history_of_present_illness",
			"module": MODULE,
		},
		{
			"fieldname": "custom_past_history_summary",
			"fieldtype": "Small Text",
			"label": "Past History",
			"insert_after": "custom_column_break_history_1",
			"description": "Combined medical, surgical, family, and social history",
			"module": MODULE,
		},
		{
			"fieldname": "custom_allergies_text",
			"fieldtype": "Small Text",
			"label": "Known Allergies",
			"insert_after": "custom_past_history_summary",
			"description": "Pre-populated from Inpatient Record allergy data",
			"module": MODULE,
		},
		# ── Examination ──────────────────────────────────────────
		{
			"fieldname": "custom_examination_section",
			"fieldtype": "Section Break",
			"label": "Examination",
			"insert_after": "custom_allergies_text",
			"depends_on": depends_on_note,
			"module": MODULE,
		},
		{
			"fieldname": "custom_general_examination",
			"fieldtype": "Text Editor",
			"label": "General Examination",
			"insert_after": "custom_examination_section",
			"module": MODULE,
		},
		{
			"fieldname": "custom_column_break_exam_1",
			"fieldtype": "Column Break",
			"insert_after": "custom_general_examination",
			"module": MODULE,
		},
		{
			"fieldname": "custom_systemic_examination",
			"fieldtype": "Text Editor",
			"label": "Systemic Examination",
			"insert_after": "custom_column_break_exam_1",
			"module": MODULE,
		},
		# ── Assessment and Plan ──────────────────────────────────
		{
			"fieldname": "custom_assessment_plan_section",
			"fieldtype": "Section Break",
			"label": "Assessment and Plan",
			"insert_after": "custom_systemic_examination",
			"depends_on": depends_on_note,
			"module": MODULE,
		},
		{
			"fieldname": "custom_provisional_diagnosis_text",
			"fieldtype": "Small Text",
			"label": "Provisional Diagnosis",
			"insert_after": "custom_assessment_plan_section",
			"description": "Narrative diagnosis; use the Diagnosis child table for ICD codes",
			"module": MODULE,
		},
		{
			"fieldname": "custom_column_break_plan_1",
			"fieldtype": "Column Break",
			"insert_after": "custom_provisional_diagnosis_text",
			"module": MODULE,
		},
		{
			"fieldname": "custom_plan_of_care",
			"fieldtype": "Text Editor",
			"label": "Plan of Care",
			"insert_after": "custom_column_break_plan_1",
			"module": MODULE,
		},
	]


def _inpatient_record_fields() -> list[dict]:
	"""Custom fields added to the standard Inpatient Record for IPD bed
	tracking, admission order details, and checklist integration."""
	return [
		# ── Admission Order Details ──────────────────────────────
		{
			"fieldname": "custom_admission_order_section",
			"fieldtype": "Section Break",
			"label": "Admission Order Details",
			"insert_after": "admission_instruction",
			"module": MODULE,
		},
		{
			"fieldname": "custom_requesting_encounter",
			"fieldtype": "Link",
			"label": "Requesting Encounter",
			"options": "Patient Encounter",
			"insert_after": "custom_admission_order_section",
			"read_only": 1,
			"search_index": 1,
			"module": MODULE,
		},
		{
			"fieldname": "custom_admission_priority",
			"fieldtype": "Select",
			"label": "Admission Priority",
			"options": ADMISSION_PRIORITY_OPTIONS,
			"insert_after": "custom_requesting_encounter",
			"default": "Routine",
			"in_standard_filter": 1,
			"module": MODULE,
		},
		{
			"fieldname": "custom_expected_los_days",
			"fieldtype": "Int",
			"label": "Expected LOS (Days)",
			"insert_after": "custom_admission_priority",
			"module": MODULE,
		},
		{
			"fieldname": "custom_column_break_admission_1",
			"fieldtype": "Column Break",
			"insert_after": "custom_expected_los_days",
			"module": MODULE,
		},
		{
			"fieldname": "custom_requested_ward",
			"fieldtype": "Link",
			"label": "Requested Ward",
			"options": "Hospital Ward",
			"insert_after": "custom_column_break_admission_1",
			"module": MODULE,
		},
		{
			"fieldname": "custom_admission_notes",
			"fieldtype": "Small Text",
			"label": "Admission Notes",
			"insert_after": "custom_requested_ward",
			"module": MODULE,
		},
		# ── Admission Checklist ──────────────────────────────────
		{
			"fieldname": "custom_admission_checklist",
			"fieldtype": "Link",
			"label": "Admission Checklist",
			"options": "Admission Checklist",
			"insert_after": "custom_admission_notes",
			"read_only": 1,
			"module": MODULE,
		},
		{
			"fieldname": "custom_checklist_status",
			"fieldtype": "Data",
			"label": "Checklist Status",
			"insert_after": "custom_admission_checklist",
			"read_only": 1,
			"fetch_from": "custom_admission_checklist.status",
			"module": MODULE,
		},
		# ── IPD Bed Details ──────────────────────────────────────
		{
			"fieldname": "custom_ipd_bed_section",
			"fieldtype": "Section Break",
			"label": "IPD Bed Details",
			"insert_after": "custom_checklist_status",
			"depends_on": "eval:doc.status !== 'Admission Scheduled'",
			"module": MODULE,
		},
		{
			"fieldname": "custom_current_bed",
			"fieldtype": "Link",
			"label": "Current Bed",
			"options": "Hospital Bed",
			"insert_after": "custom_ipd_bed_section",
			"read_only": 1,
			"in_standard_filter": 1,
			"search_index": 1,
			"module": MODULE,
		},
		{
			"fieldname": "custom_current_room",
			"fieldtype": "Link",
			"label": "Current Room",
			"options": "Hospital Room",
			"insert_after": "custom_current_bed",
			"read_only": 1,
			"module": MODULE,
		},
		{
			"fieldname": "custom_current_ward",
			"fieldtype": "Link",
			"label": "Current Ward",
			"options": "Hospital Ward",
			"insert_after": "custom_current_room",
			"read_only": 1,
			"in_standard_filter": 1,
			"search_index": 1,
			"module": MODULE,
		},
		{
			"fieldname": "custom_column_break_ipd_1",
			"fieldtype": "Column Break",
			"insert_after": "custom_current_ward",
			"module": MODULE,
		},
		{
			"fieldname": "custom_admitted_by_user",
			"fieldtype": "Link",
			"label": "Admitted By",
			"options": "User",
			"insert_after": "custom_column_break_ipd_1",
			"read_only": 1,
			"module": MODULE,
		},
		{
			"fieldname": "custom_last_movement_on",
			"fieldtype": "Datetime",
			"label": "Last Movement On",
			"insert_after": "custom_admitted_by_user",
			"read_only": 1,
			"module": MODULE,
		},
		# ── Payer Details ────────────────────────────────────────
		{
			"fieldname": "custom_payer_section",
			"fieldtype": "Section Break",
			"label": "Payer Details",
			"insert_after": "custom_last_movement_on",
			"module": MODULE,
		},
		{
			"fieldname": "custom_patient_payer_profile",
			"fieldtype": "Link",
			"label": "Patient Payer Profile",
			"options": "Patient Payer Profile",
			"insert_after": "custom_payer_section",
			"search_index": 1,
			"module": MODULE,
		},
		{
			"fieldname": "custom_payer_type",
			"fieldtype": "Data",
			"label": "Payer Type",
			"insert_after": "custom_patient_payer_profile",
			"read_only": 1,
			"fetch_from": "custom_patient_payer_profile.payer_type",
			"module": MODULE,
		},
		{
			"fieldname": "custom_column_break_payer_1",
			"fieldtype": "Column Break",
			"insert_after": "custom_payer_type",
			"module": MODULE,
		},
		{
			"fieldname": "custom_payer_display",
			"fieldtype": "Data",
			"label": "Payer",
			"insert_after": "custom_column_break_payer_1",
			"read_only": 1,
			"description": "Auto-populated from the payer profile",
			"module": MODULE,
		},
		# ── Eligibility Verification ─────────────────────────────
		{
			"fieldname": "custom_payer_eligibility_check",
			"fieldtype": "Link",
			"label": "Payer Eligibility Check",
			"options": "Payer Eligibility Check",
			"insert_after": "custom_payer_display",
			"read_only": 1,
			"search_index": 1,
			"module": MODULE,
		},
		{
			"fieldname": "custom_eligibility_status",
			"fieldtype": "Data",
			"label": "Eligibility Status",
			"insert_after": "custom_payer_eligibility_check",
			"read_only": 1,
			"fetch_from": "custom_payer_eligibility_check.verification_status",
			"module": MODULE,
		},
		# ── Intake Assessment ────────────────────────────────────
		{
			"fieldname": "custom_intake_section",
			"fieldtype": "Section Break",
			"label": "Intake Assessments",
			"insert_after": "custom_eligibility_status",
			"collapsible": 1,
			"module": MODULE,
		},
		{
			"fieldname": "custom_intake_assessment",
			"fieldtype": "Link",
			"label": "Intake Assessment",
			"options": "IPD Intake Assessment",
			"insert_after": "custom_intake_section",
			"read_only": 1,
			"module": MODULE,
		},
		{
			"fieldname": "custom_intake_status",
			"fieldtype": "Data",
			"label": "Intake Status",
			"insert_after": "custom_intake_assessment",
			"read_only": 1,
			"fetch_from": "custom_intake_assessment.status",
			"module": MODULE,
		},
		# ── Nursing Risk Indicators (US-E2) ──────────────────────
		{
			"fieldname": "custom_nursing_risk_section",
			"fieldtype": "Section Break",
			"label": "Nursing Risk Indicators",
			"insert_after": "custom_intake_status",
			"collapsible": 1,
			"module": MODULE,
		},
		{
			"fieldname": "custom_fall_risk_level",
			"fieldtype": "Select",
			"label": "Fall Risk Level",
			"options": FALL_RISK_OPTIONS,
			"insert_after": "custom_nursing_risk_section",
			"read_only": 1,
			"in_standard_filter": 1,
			"module": MODULE,
		},
		{
			"fieldname": "custom_pressure_risk_level",
			"fieldtype": "Select",
			"label": "Pressure Injury Risk",
			"options": PRESSURE_RISK_OPTIONS,
			"insert_after": "custom_fall_risk_level",
			"read_only": 1,
			"in_standard_filter": 1,
			"module": MODULE,
		},
		{
			"fieldname": "custom_nutrition_risk_level",
			"fieldtype": "Select",
			"label": "Nutrition Risk",
			"options": NUTRITION_RISK_OPTIONS,
			"insert_after": "custom_pressure_risk_level",
			"read_only": 1,
			"module": MODULE,
		},
		{
			"fieldname": "custom_column_break_risk_1",
			"fieldtype": "Column Break",
			"insert_after": "custom_nutrition_risk_level",
			"module": MODULE,
		},
		{
			"fieldname": "custom_allergy_alert",
			"fieldtype": "Check",
			"label": "Allergy Alert",
			"insert_after": "custom_column_break_risk_1",
			"read_only": 1,
			"module": MODULE,
		},
		{
			"fieldname": "custom_allergy_summary",
			"fieldtype": "Small Text",
			"label": "Allergy Summary",
			"insert_after": "custom_allergy_alert",
			"read_only": 1,
			"module": MODULE,
		},
		{
			"fieldname": "custom_risk_flags_updated_on",
			"fieldtype": "Datetime",
			"label": "Risk Flags Updated",
			"insert_after": "custom_allergy_summary",
			"read_only": 1,
			"module": MODULE,
		},
		{
			"fieldname": "custom_risk_flags_updated_by",
			"fieldtype": "Link",
			"label": "Risk Updated By",
			"options": "User",
			"insert_after": "custom_risk_flags_updated_on",
			"read_only": 1,
			"module": MODULE,
		},
		# ── Bedside Charts (US-E4) ──────────────────────────────
		{
			"fieldname": "custom_charting_section",
			"fieldtype": "Section Break",
			"label": "Bedside Charts",
			"insert_after": "custom_risk_flags_updated_by",
			"collapsible": 1,
			"module": MODULE,
		},
		{
			"fieldname": "custom_active_charts_count",
			"fieldtype": "Int",
			"label": "Active Charts",
			"insert_after": "custom_charting_section",
			"read_only": 1,
			"module": MODULE,
		},
		{
			"fieldname": "custom_overdue_charts_count",
			"fieldtype": "Int",
			"label": "Overdue Charts",
			"insert_after": "custom_active_charts_count",
			"read_only": 1,
			"module": MODULE,
		},
		{
			"fieldname": "custom_column_break_charting_1",
			"fieldtype": "Column Break",
			"insert_after": "custom_overdue_charts_count",
			"module": MODULE,
		},
		{
			"fieldname": "custom_last_vitals_at",
			"fieldtype": "Datetime",
			"label": "Last Vitals At",
			"insert_after": "custom_column_break_charting_1",
			"read_only": 1,
			"module": MODULE,
		},
		{
			"fieldname": "custom_critical_alerts_count",
			"fieldtype": "Int",
			"label": "Critical Alerts",
			"insert_after": "custom_last_vitals_at",
			"read_only": 1,
			"description": "Count of active critical observations",
			"module": MODULE,
		},
		{
			"fieldname": "custom_due_meds_count",
			"fieldtype": "Int",
			"label": "Due Medications",
			"insert_after": "custom_critical_alerts_count",
			"read_only": 1,
			"description": "Count of today's due/scheduled MAR entries",
			"module": MODULE,
		},
		# ── Problem List & Round Notes (US-E5) ──────────────────
		{
			"fieldname": "custom_problem_list_section",
			"fieldtype": "Section Break",
			"label": "Problem List & Round Notes",
			"insert_after": "custom_due_meds_count",
			"collapsible": 1,
			"module": MODULE,
		},
		{
			"fieldname": "custom_active_problems_count",
			"fieldtype": "Int",
			"label": "Active Problems",
			"insert_after": "custom_problem_list_section",
			"read_only": 1,
			"module": MODULE,
		},
		{
			"fieldname": "custom_column_break_problems_1",
			"fieldtype": "Column Break",
			"insert_after": "custom_active_problems_count",
			"module": MODULE,
		},
		{
			"fieldname": "custom_last_progress_note_date",
			"fieldtype": "Date",
			"label": "Last Progress Note",
			"insert_after": "custom_column_break_problems_1",
			"read_only": 1,
			"module": MODULE,
		},
		# ── Clinical Orders (US-F1–F5) ──────────────────────────
		{
			"fieldname": "custom_clinical_orders_section",
			"fieldtype": "Section Break",
			"label": "Clinical Orders",
			"insert_after": "custom_last_progress_note_date",
			"collapsible": 1,
			"module": MODULE,
		},
		{
			"fieldname": "custom_active_medication_orders",
			"fieldtype": "Int",
			"label": "Active Medication Orders",
			"insert_after": "custom_clinical_orders_section",
			"read_only": 1,
			"module": MODULE,
		},
		{
			"fieldname": "custom_active_lab_orders",
			"fieldtype": "Int",
			"label": "Active Lab Orders",
			"insert_after": "custom_active_medication_orders",
			"read_only": 1,
			"module": MODULE,
		},
		{
			"fieldname": "custom_column_break_orders_1",
			"fieldtype": "Column Break",
			"insert_after": "custom_active_lab_orders",
			"module": MODULE,
		},
		{
			"fieldname": "custom_active_procedure_orders",
			"fieldtype": "Int",
			"label": "Active Procedure Orders",
			"insert_after": "custom_column_break_orders_1",
			"read_only": 1,
			"module": MODULE,
		},
		{
			"fieldname": "custom_pending_orders_count",
			"fieldtype": "Int",
			"label": "Pending Orders",
			"insert_after": "custom_active_procedure_orders",
			"read_only": 1,
			"module": MODULE,
		},
		# ── TPA Pre-authorization (US-I1) ───────────────────────
		{
			"fieldname": "custom_tpa_billing_section",
			"fieldtype": "Section Break",
			"label": "TPA & Billing",
			"insert_after": "custom_pending_orders_count",
			"collapsible": 1,
			"module": MODULE,
		},
		{
			"fieldname": "custom_preauth_request",
			"fieldtype": "Link",
			"label": "TPA Preauth Request",
			"options": "TPA Preauth Request",
			"insert_after": "custom_tpa_billing_section",
			"read_only": 1,
			"search_index": 1,
			"module": MODULE,
		},
		{
			"fieldname": "custom_preauth_status",
			"fieldtype": "Data",
			"label": "Preauth Status",
			"insert_after": "custom_preauth_request",
			"read_only": 1,
			"fetch_from": "custom_preauth_request.status",
			"module": MODULE,
		},
		{
			"fieldname": "custom_column_break_tpa_1",
			"fieldtype": "Column Break",
			"insert_after": "custom_preauth_status",
			"module": MODULE,
		},
		# ── Discharge Billing Checklist (US-I4) ─────────────────
		{
			"fieldname": "custom_discharge_checklist",
			"fieldtype": "Link",
			"label": "Discharge Billing Checklist",
			"options": "Discharge Billing Checklist",
			"insert_after": "custom_column_break_tpa_1",
			"read_only": 1,
			"search_index": 1,
			"module": MODULE,
		},
		{
			"fieldname": "custom_discharge_checklist_status",
			"fieldtype": "Data",
			"label": "Discharge Checklist Status",
			"insert_after": "custom_discharge_checklist",
			"read_only": 1,
			"fetch_from": "custom_discharge_checklist.status",
			"module": MODULE,
		},
		{
			"fieldname": "custom_column_break_tpa_2",
			"fieldtype": "Column Break",
			"insert_after": "custom_discharge_checklist_status",
			"module": MODULE,
		},
		# ── TPA Claim Pack (US-I5) ──────────────────────────────
		{
			"fieldname": "custom_claim_pack",
			"fieldtype": "Link",
			"label": "TPA Claim Pack",
			"options": "TPA Claim Pack",
			"insert_after": "custom_column_break_tpa_2",
			"read_only": 1,
			"search_index": 1,
			"module": MODULE,
		},
		# ── Discharge Journey (US-J1/J2) ────────────────────────
		{
			"fieldname": "custom_discharge_journey_section",
			"fieldtype": "Section Break",
			"label": "Discharge Journey",
			"insert_after": "custom_claim_pack",
			"collapsible": 1,
			"module": MODULE,
		},
		{
			"fieldname": "custom_discharge_advice",
			"fieldtype": "Link",
			"label": "Discharge Advice",
			"options": "IPD Discharge Advice",
			"insert_after": "custom_discharge_journey_section",
			"read_only": 1,
			"search_index": 1,
			"module": MODULE,
		},
		{
			"fieldname": "custom_discharge_advice_status",
			"fieldtype": "Data",
			"label": "Discharge Advice Status",
			"insert_after": "custom_discharge_advice",
			"read_only": 1,
			"fetch_from": "custom_discharge_advice.status",
			"module": MODULE,
		},
		{
			"fieldname": "custom_expected_discharge_datetime",
			"fieldtype": "Datetime",
			"label": "Expected Discharge",
			"insert_after": "custom_discharge_advice_status",
			"read_only": 1,
			"fetch_from": "custom_discharge_advice.expected_discharge_datetime",
			"module": MODULE,
		},
		{
			"fieldname": "custom_column_break_discharge_1",
			"fieldtype": "Column Break",
			"insert_after": "custom_expected_discharge_datetime",
			"module": MODULE,
		},
		{
			"fieldname": "custom_nursing_discharge_checklist",
			"fieldtype": "Link",
			"label": "Nursing Discharge Checklist",
			"options": "Nursing Discharge Checklist",
			"insert_after": "custom_column_break_discharge_1",
			"read_only": 1,
			"search_index": 1,
			"module": MODULE,
		},
		{
			"fieldname": "custom_nursing_discharge_status",
			"fieldtype": "Data",
			"label": "Nursing Discharge Status",
			"insert_after": "custom_nursing_discharge_checklist",
			"read_only": 1,
			"fetch_from": "custom_nursing_discharge_checklist.status",
			"module": MODULE,
		},
	]


FALL_RISK_OPTIONS = "\nLow\nModerate\nHigh"
PRESSURE_RISK_OPTIONS = "\nNo Risk\nLow\nModerate\nHigh\nVery High"
NUTRITION_RISK_OPTIONS = "\nLow\nMedium\nHigh"

ASSESSMENT_CONTEXT_OPTIONS = "\nIntake\nMonitoring\nDischarge"


def _patient_assessment_template_fields() -> list[dict]:
	"""Custom fields on standard Patient Assessment Template for IPD context."""
	return [
		{
			"fieldname": "custom_ipd_section",
			"fieldtype": "Section Break",
			"label": "IPD Settings",
			"insert_after": "assessment_description",
			"collapsible": 1,
			"module": MODULE,
		},
		{
			"fieldname": "custom_specialty",
			"fieldtype": "Link",
			"label": "Specialty",
			"options": "Medical Department",
			"insert_after": "custom_ipd_section",
			"in_standard_filter": 1,
			"module": MODULE,
		},
		{
			"fieldname": "custom_assessment_context",
			"fieldtype": "Select",
			"label": "Assessment Context",
			"options": ASSESSMENT_CONTEXT_OPTIONS,
			"insert_after": "custom_specialty",
			"in_standard_filter": 1,
			"module": MODULE,
		},
		{
			"fieldname": "custom_column_break_ipd_pat",
			"fieldtype": "Column Break",
			"insert_after": "custom_assessment_context",
			"module": MODULE,
		},
		{
			"fieldname": "custom_ipd_sort_order",
			"fieldtype": "Int",
			"label": "IPD Sort Order",
			"insert_after": "custom_column_break_ipd_pat",
			"description": "Display ordering within intake bundles",
			"module": MODULE,
		},
		{
			"fieldname": "custom_is_ipd_active",
			"fieldtype": "Check",
			"label": "Active for IPD",
			"insert_after": "custom_ipd_sort_order",
			"default": "0",
			"module": MODULE,
		},
	]


def _patient_assessment_fields() -> list[dict]:
	"""Custom fields on standard Patient Assessment for IPD linkage."""
	return [
		{
			"fieldname": "custom_ipd_link_section",
			"fieldtype": "Section Break",
			"label": "IPD Context",
			"insert_after": "assessment_description",
			"collapsible": 1,
			"module": MODULE,
		},
		{
			"fieldname": "custom_inpatient_record",
			"fieldtype": "Link",
			"label": "Inpatient Record",
			"options": "Inpatient Record",
			"insert_after": "custom_ipd_link_section",
			"search_index": 1,
			"module": MODULE,
		},
		{
			"fieldname": "custom_intake_assessment",
			"fieldtype": "Link",
			"label": "Intake Assessment",
			"options": "IPD Intake Assessment",
			"insert_after": "custom_inpatient_record",
			"module": MODULE,
		},
		{
			"fieldname": "custom_column_break_ipd_pa",
			"fieldtype": "Column Break",
			"insert_after": "custom_intake_assessment",
			"module": MODULE,
		},
		{
			"fieldname": "custom_assessment_context",
			"fieldtype": "Data",
			"label": "Assessment Context",
			"insert_after": "custom_column_break_ipd_pa",
			"read_only": 1,
			"fetch_from": "assessment_template.custom_assessment_context",
			"module": MODULE,
		},
	]


def setup_custom_fields():
	"""Create all custom fields owned by this app.

	Safe to call repeatedly -- Frappe's ``create_custom_fields`` is
	idempotent (creates only when the field does not already exist).
	"""
	create_custom_fields(get_custom_fields(), update=True)
	for dt in get_custom_fields():
		frappe.clear_cache(doctype=dt)


def teardown_custom_fields():
	"""Remove custom fields owned by this app (used during uninstall)."""
	for doctype, fields in get_custom_fields().items():
		for field_def in fields:
			fieldname = field_def["fieldname"]
			custom_field_name = f"{doctype}-{fieldname}"
			if frappe.db.exists("Custom Field", custom_field_name):
				frappe.delete_doc("Custom Field", custom_field_name, force=True)
	for dt in get_custom_fields():
		frappe.clear_cache(doctype=dt)
