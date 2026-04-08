"""Tests for US-E2: Nursing Risk Service.

Covers: risk classification functions, risk flag updates on IR,
allergy extraction from intake, alert/ToDo generation, idempotent
alert creation, timestamp recording, and API layer.
"""

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import today

from alcura_ipd_ext.services.nursing_risk_service import (
	classify_braden_risk,
	classify_fall_risk,
	classify_nutrition_risk,
	extract_allergy_data,
	get_risk_summary,
	get_ward_risk_overview,
	update_risk_flags,
)
from alcura_ipd_ext.services.nursing_alert_service import raise_risk_alerts


# ---------------------------------------------------------------------------
# Factories
# ---------------------------------------------------------------------------


def _get_or_create_company(abbr="TST", name="Test Hospital Pvt Ltd"):
	if frappe.db.exists("Company", name):
		return name
	company = frappe.get_doc({
		"doctype": "Company",
		"company_name": name,
		"abbr": abbr,
		"default_currency": "INR",
		"country": "India",
	})
	company.insert(ignore_if_duplicate=True)
	return company.name


def _make_medical_department(name="Test General"):
	if frappe.db.exists("Medical Department", name):
		return name
	doc = frappe.get_doc({
		"doctype": "Medical Department",
		"department": name,
	})
	doc.insert(ignore_permissions=True)
	return doc.name


def _make_patient(suffix="NR"):
	patient_name = f"Test Patient {suffix}"
	existing = frappe.db.exists("Patient", {"patient_name": patient_name})
	if existing:
		return frappe.get_doc("Patient", existing)
	doc = frappe.get_doc({
		"doctype": "Patient",
		"first_name": f"Test {suffix}",
		"last_name": "Patient",
		"sex": "Male",
	})
	doc.insert(ignore_permissions=True)
	return doc


def _make_inpatient_record(patient=None, company=None, department=None, status="Admitted"):
	patient_doc = patient or _make_patient()
	patient_name = patient_doc.name if hasattr(patient_doc, "name") else patient_doc
	company = company or _get_or_create_company()
	dept = department or _make_medical_department()
	doc = frappe.get_doc({
		"doctype": "Inpatient Record",
		"patient": patient_name,
		"company": company,
		"status": status,
		"scheduled_date": today(),
		"medical_department": dept,
	})
	doc.insert(ignore_permissions=True)
	return doc


def _make_assessment_parameter(name):
	if not frappe.db.exists("Patient Assessment Parameter", name):
		frappe.get_doc({
			"doctype": "Patient Assessment Parameter",
			"assessment_parameter": name,
		}).insert(ignore_permissions=True)
	return name


def _make_scored_template(name, params, scale_min=0, scale_max=4):
	if frappe.db.exists("Patient Assessment Template", name):
		frappe.delete_doc("Patient Assessment Template", name, force=True)

	for p in params:
		_make_assessment_parameter(p)

	doc = frappe.get_doc({
		"doctype": "Patient Assessment Template",
		"assessment_name": name,
		"scale_min": scale_min,
		"scale_max": scale_max,
		"custom_assessment_context": "Intake",
		"custom_is_ipd_active": 1,
	})
	for p in params:
		doc.append("parameters", {"assessment_parameter": p})
	doc.insert(ignore_permissions=True)
	return doc


def _make_patient_assessment(ir, template_name, scores, submit=True):
	"""Create a Patient Assessment with the given scores and optionally submit it."""
	template = frappe.get_doc("Patient Assessment Template", template_name)
	pa = frappe.get_doc({
		"doctype": "Patient Assessment",
		"patient": ir.patient,
		"assessment_template": template_name,
		"assessment_datetime": frappe.utils.now_datetime(),
		"company": ir.company,
		"custom_inpatient_record": ir.name,
	})

	for i, detail in enumerate(template.parameters or []):
		score_val = scores[i] if i < len(scores) else template.scale_min
		pa.append("assessment_sheet", {
			"parameter": detail.assessment_parameter,
			"score": str(score_val),
		})

	pa.insert(ignore_permissions=True)
	if submit:
		pa.submit()
	return pa


def _make_intake_with_allergy(ir, allergy_type, allergy_details=""):
	"""Create a minimal IPD Intake Assessment with allergy fields filled."""
	template = None
	if frappe.db.exists("IPD Intake Assessment Template", "Test Allergy Template"):
		frappe.delete_doc("IPD Intake Assessment Template", "Test Allergy Template", force=True)

	template = frappe.get_doc({
		"doctype": "IPD Intake Assessment Template",
		"template_name": "Test Allergy Template",
		"target_role": "Nursing User",
		"is_active": 1,
		"version": 1,
	})
	template.append("form_fields", {
		"section_label": "Allergy Status",
		"field_label": "Known Allergies",
		"field_type": "Select",
		"options": "None Known\nDrug Allergy\nFood Allergy\nMultiple",
		"is_mandatory": 1,
		"display_order": 10,
		"role_visibility": "All",
	})
	template.append("form_fields", {
		"section_label": "Allergy Status",
		"field_label": "Allergy Details",
		"field_type": "Small Text",
		"is_mandatory": 0,
		"display_order": 20,
		"role_visibility": "All",
	})
	template.insert(ignore_permissions=True)

	assessment = frappe.get_doc({
		"doctype": "IPD Intake Assessment",
		"patient": ir.patient,
		"inpatient_record": ir.name,
		"template": template.name,
		"template_version": 1,
		"company": ir.company,
		"assessment_datetime": frappe.utils.now_datetime(),
		"status": "Draft",
	})
	assessment.append("responses", {
		"section_label": "Allergy Status",
		"field_label": "Known Allergies",
		"field_type": "Select",
		"text_value": allergy_type,
		"is_mandatory": 1,
	})
	assessment.append("responses", {
		"section_label": "Allergy Status",
		"field_label": "Allergy Details",
		"field_type": "Small Text",
		"text_value": allergy_details,
		"is_mandatory": 0,
	})
	assessment.insert(ignore_permissions=True)

	ir.db_set("custom_intake_assessment", assessment.name, update_modified=False)
	return assessment


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestNursingRiskService(IntegrationTestCase):
	def tearDown(self):
		frappe.db.rollback()
		frappe.set_user("Administrator")

	# ── 1–3. Fall Risk Classification ─────────────────────────

	def test_classify_fall_risk_low(self):
		"""Morse Fall Scale score 0-24 returns Low."""
		self.assertEqual(classify_fall_risk(0), "Low")
		self.assertEqual(classify_fall_risk(20), "Low")
		self.assertEqual(classify_fall_risk(24), "Low")

	def test_classify_fall_risk_moderate(self):
		"""Morse Fall Scale score 25-44 returns Moderate."""
		self.assertEqual(classify_fall_risk(25), "Moderate")
		self.assertEqual(classify_fall_risk(35), "Moderate")
		self.assertEqual(classify_fall_risk(44), "Moderate")

	def test_classify_fall_risk_high(self):
		"""Morse Fall Scale score >= 45 returns High."""
		self.assertEqual(classify_fall_risk(45), "High")
		self.assertEqual(classify_fall_risk(100), "High")

	# ── 4–8. Braden Risk Classification ──────────────────────

	def test_classify_braden_no_risk(self):
		"""Braden Scale score >= 19 returns No Risk."""
		self.assertEqual(classify_braden_risk(19), "No Risk")
		self.assertEqual(classify_braden_risk(23), "No Risk")

	def test_classify_braden_low(self):
		"""Braden Scale score 15-18 returns Low."""
		self.assertEqual(classify_braden_risk(15), "Low")
		self.assertEqual(classify_braden_risk(18), "Low")

	def test_classify_braden_moderate(self):
		"""Braden Scale score 13-14 returns Moderate."""
		self.assertEqual(classify_braden_risk(13), "Moderate")
		self.assertEqual(classify_braden_risk(14), "Moderate")

	def test_classify_braden_high(self):
		"""Braden Scale score 10-12 returns High."""
		self.assertEqual(classify_braden_risk(10), "High")
		self.assertEqual(classify_braden_risk(12), "High")

	def test_classify_braden_very_high(self):
		"""Braden Scale score <= 9 returns Very High."""
		self.assertEqual(classify_braden_risk(9), "Very High")
		self.assertEqual(classify_braden_risk(6), "Very High")

	# ── 9–11. Nutrition Risk Classification ──────────────────

	def test_classify_nutrition_low(self):
		"""MUST score 0 returns Low."""
		self.assertEqual(classify_nutrition_risk(0), "Low")

	def test_classify_nutrition_medium(self):
		"""MUST score 1 returns Medium."""
		self.assertEqual(classify_nutrition_risk(1), "Medium")

	def test_classify_nutrition_high(self):
		"""MUST score >= 2 returns High."""
		self.assertEqual(classify_nutrition_risk(2), "High")
		self.assertEqual(classify_nutrition_risk(5), "High")

	# ── 12. Risk Flag Update from Scored Assessments ─────────

	def test_update_risk_flags_from_scored_assessments(self):
		"""Submitting scored assessments updates IR custom risk fields."""
		ir = _make_inpatient_record(patient=_make_patient("NR12"))

		morse = _make_scored_template(
			"Morse Fall Scale",
			["History of Falling", "Secondary Diagnosis", "Ambulatory Aid",
			 "IV / Heparin Lock", "Gait", "Mental Status"],
			scale_min=0, scale_max=4,
		)
		# Scores: 4+3+2+1+3+2 = 15 → Low
		_make_patient_assessment(ir, morse.name, [4, 3, 2, 1, 3, 2])

		flags = update_risk_flags(ir.name)
		self.assertEqual(flags.get("custom_fall_risk_level"), "Low")

	# ── 13. Allergy Extraction from Intake ───────────────────

	def test_allergy_extraction_from_intake(self):
		"""Allergy data is extracted from intake assessment responses."""
		ir = _make_inpatient_record(patient=_make_patient("NR13"))
		_make_intake_with_allergy(ir, "Drug Allergy", "Penicillin")

		has_allergy, summary = extract_allergy_data(ir.custom_intake_assessment)
		self.assertTrue(has_allergy)
		self.assertIn("Penicillin", summary)

	def test_allergy_none_known(self):
		"""None Known allergy returns no alert."""
		ir = _make_inpatient_record(patient=_make_patient("NR13b"))
		_make_intake_with_allergy(ir, "None Known")

		has_allergy, summary = extract_allergy_data(ir.custom_intake_assessment)
		self.assertFalse(has_allergy)
		self.assertEqual(summary, "")

	# ── 14. High Fall Risk Creates ToDo ──────────────────────

	def test_high_fall_risk_creates_todo(self):
		"""High fall risk triggers a ToDo assignment."""
		ir = _make_inpatient_record(patient=_make_patient("NR14"))

		flags = {"custom_fall_risk_level": "High"}
		created = raise_risk_alerts(ir.name, flags)

		self.assertTrue(len(created) >= 1)
		todo = frappe.get_doc("ToDo", created[0])
		self.assertEqual(todo.reference_type, "Inpatient Record")
		self.assertEqual(todo.reference_name, ir.name)
		self.assertIn("Fall Prevention Protocol", todo.description)

	# ── 15. High Pressure Risk Creates ToDo ──────────────────

	def test_high_pressure_risk_creates_todo(self):
		"""High pressure injury risk triggers a ToDo assignment."""
		ir = _make_inpatient_record(patient=_make_patient("NR15"))

		flags = {"custom_pressure_risk_level": "Very High"}
		created = raise_risk_alerts(ir.name, flags)

		self.assertTrue(len(created) >= 1)
		todo = frappe.get_doc("ToDo", created[0])
		self.assertIn("Pressure Injury Prevention", todo.description)

	# ── 16. Duplicate Alert Prevention ───────────────────────

	def test_duplicate_alert_prevention(self):
		"""Same alert is not created twice for the same IR."""
		ir = _make_inpatient_record(patient=_make_patient("NR16"))

		flags = {"custom_fall_risk_level": "High"}
		created1 = raise_risk_alerts(ir.name, flags)
		created2 = raise_risk_alerts(ir.name, flags)

		self.assertTrue(len(created1) >= 1)
		self.assertEqual(len(created2), 0)

	# ── 17. Allergy Alert Creates Comment ────────────────────

	def test_allergy_alert_creates_comment(self):
		"""Allergy alert adds a timeline comment on the IR."""
		ir = _make_inpatient_record(patient=_make_patient("NR17"))

		flags = {
			"custom_allergy_alert": 1,
			"custom_allergy_summary": "Drug Allergy: Sulfa",
		}
		raise_risk_alerts(ir.name, flags)

		comments = frappe.get_all(
			"Comment",
			filters={
				"reference_doctype": "Inpatient Record",
				"reference_name": ir.name,
				"content": ("like", "%ALLERGY ALERT%"),
			},
		)
		self.assertTrue(len(comments) >= 1)

	# ── 18. Risk Flags Updated Timestamp ─────────────────────

	def test_risk_flags_updated_timestamp(self):
		"""Timestamp and user are recorded when risk flags are updated."""
		ir = _make_inpatient_record(patient=_make_patient("NR18"))

		_make_scored_template(
			"Morse Fall Scale",
			["History of Falling", "Secondary Diagnosis", "Ambulatory Aid",
			 "IV / Heparin Lock", "Gait", "Mental Status"],
			scale_min=0, scale_max=4,
		)
		_make_patient_assessment(ir, "Morse Fall Scale", [1, 1, 1, 1, 1, 1])

		flags = update_risk_flags(ir.name)
		self.assertTrue(flags.get("custom_risk_flags_updated_on"))
		self.assertTrue(flags.get("custom_risk_flags_updated_by"))

	# ── 19. Risk Summary API ─────────────────────────────────

	def test_risk_summary_api(self):
		"""get_risk_summary returns correct risk data."""
		ir = _make_inpatient_record(patient=_make_patient("NR19"))

		frappe.db.set_value("Inpatient Record", ir.name, {
			"custom_fall_risk_level": "High",
			"custom_pressure_risk_level": "Moderate",
			"custom_allergy_alert": 1,
			"custom_allergy_summary": "Latex",
			"custom_risk_flags_updated_on": frappe.utils.now_datetime(),
			"custom_risk_flags_updated_by": "Administrator",
		}, update_modified=False)

		summary = get_risk_summary(ir.name)
		self.assertEqual(summary["fall_risk_level"], "High")
		self.assertEqual(summary["pressure_risk_level"], "Moderate")
		self.assertEqual(summary["allergy_alert"], 1)
		self.assertIn("Latex", summary["allergy_summary"])

	# ── 20. Ward Risk Overview ───────────────────────────────

	def test_ward_risk_overview(self):
		"""get_ward_risk_overview returns all admitted patients with risk data."""
		ir = _make_inpatient_record(patient=_make_patient("NR20"))

		frappe.db.set_value("Inpatient Record", ir.name, {
			"custom_fall_risk_level": "Moderate",
			"custom_risk_flags_updated_on": frappe.utils.now_datetime(),
		}, update_modified=False)

		overview = get_ward_risk_overview()
		matching = [r for r in overview if r["inpatient_record"] == ir.name]
		self.assertEqual(len(matching), 1)
		self.assertEqual(matching[0]["fall_risk_level"], "Moderate")
