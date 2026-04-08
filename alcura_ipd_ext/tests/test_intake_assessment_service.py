"""Tests for US-E1: Intake Assessment Service.

Covers: template selection, assessment creation, response saving,
mandatory validation, status transitions, duplicate prevention,
scored assessment auto-creation, IR link sync, and template versioning.
"""

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import today

from alcura_ipd_ext.services.intake_assessment_service import (
	complete_intake_assessment,
	create_intake_assessment,
	get_intake_assessments_for_ir,
	get_pending_scored_assessments,
	save_responses,
	select_template,
)


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


def _make_patient(suffix="IA"):
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


def _make_inpatient_record(patient=None, company=None, department=None):
	patient_doc = patient or _make_patient()
	patient_name = patient_doc.name if hasattr(patient_doc, "name") else patient_doc
	company = company or _get_or_create_company()
	dept = department or _make_medical_department()
	doc = frappe.get_doc({
		"doctype": "Inpatient Record",
		"patient": patient_name,
		"company": company,
		"status": "Admission Scheduled",
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


def _make_scored_template(name="Test GCS", params=None, scale_min=1, scale_max=6):
	if frappe.db.exists("Patient Assessment Template", name):
		frappe.delete_doc("Patient Assessment Template", name, force=True)

	params = params or ["Eye Opening", "Verbal Response", "Motor Response"]
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


def _make_intake_template(
	name="Test Medicine Nursing Intake",
	target_role="Nursing User",
	specialty=None,
	fields=None,
	scored_templates=None,
	**overrides,
):
	if frappe.db.exists("IPD Intake Assessment Template", name):
		frappe.delete_doc("IPD Intake Assessment Template", name, force=True)

	default_fields = fields or [
		{
			"section_label": "Chief Complaint",
			"field_label": "Chief Complaint",
			"field_type": "Small Text",
			"is_mandatory": 1,
			"display_order": 10,
			"role_visibility": "All",
		},
		{
			"section_label": "Vitals",
			"field_label": "Blood Pressure",
			"field_type": "Text",
			"is_mandatory": 0,
			"display_order": 20,
			"role_visibility": "All",
		},
		{
			"section_label": "Vitals",
			"field_label": "Temperature",
			"field_type": "Float",
			"is_mandatory": 0,
			"display_order": 30,
			"role_visibility": "All",
		},
		{
			"section_label": "Allergy Status",
			"field_label": "Known Allergies",
			"field_type": "Select",
			"options": "None Known\nDrug Allergy\nFood Allergy",
			"is_mandatory": 1,
			"display_order": 40,
			"role_visibility": "All",
		},
		{
			"section_label": "Mobility",
			"field_label": "Fall Risk Identified",
			"field_type": "Check",
			"is_mandatory": 0,
			"display_order": 50,
			"role_visibility": "Nursing User",
		},
	]

	doc = frappe.get_doc({
		"doctype": "IPD Intake Assessment Template",
		"template_name": name,
		"target_role": target_role,
		"specialty": specialty,
		"is_active": overrides.get("is_active", 1),
		"version": overrides.get("version", 1),
		"description": overrides.get("description", "Test template"),
	})

	for f in default_fields:
		doc.append("form_fields", f)

	for scored_name in (scored_templates or []):
		doc.append("scored_assessments", {
			"assessment_template": scored_name,
			"is_mandatory": 0,
		})

	doc.insert(ignore_permissions=True)
	return doc


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestIntakeAssessmentService(IntegrationTestCase):
	def tearDown(self):
		frappe.db.rollback()
		frappe.set_user("Administrator")

	# ── 1. Template selection ─────────────────────────────────────

	def test_select_template_exact_specialty(self):
		"""Template matching exact specialty is returned."""
		dept = _make_medical_department("Cardiology")
		_make_intake_template(
			name="Cardio Nursing",
			specialty=dept,
			target_role="Nursing User",
		)
		_make_intake_template(
			name="Generic Nursing",
			target_role="Nursing User",
		)

		result = select_template(specialty="Cardiology", target_role="Nursing User")
		self.assertEqual(result.name, "Cardio Nursing")

	def test_select_template_fallback_to_both(self):
		"""Falls back to target_role=Both when exact role not found."""
		_make_intake_template(
			name="Universal Template",
			target_role="Both",
		)

		result = select_template(target_role="Physician")
		self.assertEqual(result.name, "Universal Template")

	def test_select_template_returns_none(self):
		"""Returns None when no active template exists."""
		for t in frappe.get_all("IPD Intake Assessment Template"):
			frappe.delete_doc("IPD Intake Assessment Template", t.name, force=True)

		result = select_template()
		self.assertIsNone(result)

	def test_select_template_inactive_skipped(self):
		"""Inactive templates are not returned."""
		_make_intake_template(name="Inactive Template", is_active=0)
		result = select_template()
		self.assertIsNone(result)

	# ── 2. Assessment creation ────────────────────────────────────

	def test_create_assessment_from_template(self):
		"""Creates assessment with response rows from template fields."""
		template = _make_intake_template()
		ir = _make_inpatient_record(patient=_make_patient("IA1"))

		result = create_intake_assessment(ir.name, template_name=template.name)

		self.assertTrue(result["assessment"])
		self.assertEqual(result["status"], "Draft")
		self.assertEqual(result["template"], template.name)

		doc = frappe.get_doc("IPD Intake Assessment", result["assessment"])
		self.assertEqual(doc.inpatient_record, ir.name)
		self.assertEqual(doc.template_version, 1)
		self.assertEqual(len(doc.responses), 5)

		# All mandatory flags carried from template
		mandatory_labels = [r.field_label for r in doc.responses if r.is_mandatory]
		self.assertIn("Chief Complaint", mandatory_labels)
		self.assertIn("Known Allergies", mandatory_labels)

	def test_create_assessment_auto_selects_template(self):
		"""Auto-selects template based on IR medical department."""
		dept = _make_medical_department("Test Ortho")
		_make_intake_template(
			name="Ortho Nursing Intake",
			specialty=dept,
		)

		ir = _make_inpatient_record(
			patient=_make_patient("IA2"),
			department=dept,
		)

		result = create_intake_assessment(ir.name)
		self.assertEqual(result["template"], "Ortho Nursing Intake")

	def test_create_assessment_links_to_ir(self):
		"""IR's custom_intake_assessment is set after creation."""
		template = _make_intake_template(name="IR Link Template")
		ir = _make_inpatient_record(patient=_make_patient("IA3"))

		result = create_intake_assessment(ir.name, template_name=template.name)

		ir.reload()
		self.assertEqual(ir.custom_intake_assessment, result["assessment"])

	# ── 3. Duplicate prevention ───────────────────────────────────

	def test_duplicate_assessment_fails(self):
		"""Cannot create two assessments for same IR + template."""
		template = _make_intake_template(name="Dup Template")
		ir = _make_inpatient_record(patient=_make_patient("IA4"))

		create_intake_assessment(ir.name, template_name=template.name)

		with self.assertRaises(frappe.ValidationError):
			create_intake_assessment(ir.name, template_name=template.name)

	def test_different_templates_allowed(self):
		"""Different templates for the same IR are allowed."""
		tmpl1 = _make_intake_template(name="Nurse Template")
		tmpl2 = _make_intake_template(
			name="Doctor Template",
			target_role="Physician",
		)

		ir = _make_inpatient_record(patient=_make_patient("IA5"))

		r1 = create_intake_assessment(ir.name, template_name=tmpl1.name)
		r2 = create_intake_assessment(ir.name, template_name=tmpl2.name)

		self.assertNotEqual(r1["assessment"], r2["assessment"])

	# ── 4. No template fails ─────────────────────────────────────

	def test_no_template_fails(self):
		"""Assessment creation fails when no template exists."""
		for t in frappe.get_all("IPD Intake Assessment Template"):
			frappe.delete_doc("IPD Intake Assessment Template", t.name, force=True)

		ir = _make_inpatient_record(patient=_make_patient("IA6"))

		with self.assertRaises(frappe.ValidationError):
			create_intake_assessment(ir.name)

	# ── 5. Response saving ────────────────────────────────────────

	def test_save_responses(self):
		"""Saving responses updates field values and transitions to In Progress."""
		template = _make_intake_template(name="Save Template")
		ir = _make_inpatient_record(patient=_make_patient("IA7"))
		result = create_intake_assessment(ir.name, template_name=template.name)

		save_result = save_responses(result["assessment"], [
			{"idx": 1, "text_value": "Chest pain since 2 days"},
			{"idx": 3, "numeric_value": 101.2},
		])

		self.assertEqual(save_result["status"], "In Progress")

		doc = frappe.get_doc("IPD Intake Assessment", result["assessment"])
		self.assertEqual(doc.responses[0].text_value, "Chest pain since 2 days")
		self.assertEqual(doc.responses[2].numeric_value, 101.2)

	def test_save_responses_completed_fails(self):
		"""Cannot save responses to a completed assessment."""
		template = _make_intake_template(
			name="Completed Save Template",
			fields=[
				{
					"section_label": "Test",
					"field_label": "Test Field",
					"field_type": "Text",
					"is_mandatory": 0,
					"display_order": 10,
					"role_visibility": "All",
				},
			],
		)
		ir = _make_inpatient_record(patient=_make_patient("IA8"))
		result = create_intake_assessment(ir.name, template_name=template.name)

		complete_intake_assessment(result["assessment"])

		with self.assertRaises(frappe.ValidationError):
			save_responses(result["assessment"], [{"idx": 1, "text_value": "late edit"}])

	# ── 6. Status transitions ────────────────────────────────────

	def test_status_draft_to_in_progress(self):
		"""Status transitions from Draft to In Progress on first save."""
		template = _make_intake_template(name="Status Template")
		ir = _make_inpatient_record(patient=_make_patient("IA9"))
		result = create_intake_assessment(ir.name, template_name=template.name)

		doc = frappe.get_doc("IPD Intake Assessment", result["assessment"])
		self.assertEqual(doc.status, "Draft")

		save_responses(result["assessment"], [
			{"idx": 1, "text_value": "headache"},
		])

		doc.reload()
		self.assertEqual(doc.status, "In Progress")

	# ── 7. Completion ────────────────────────────────────────────

	def test_complete_assessment_success(self):
		"""Assessment completes when all mandatory fields are filled."""
		template = _make_intake_template(name="Complete Template")
		ir = _make_inpatient_record(patient=_make_patient("IA10"))
		result = create_intake_assessment(ir.name, template_name=template.name)

		# Fill mandatory fields
		save_responses(result["assessment"], [
			{"idx": 1, "text_value": "abdominal pain"},
			{"idx": 4, "text_value": "None Known"},
		])

		complete_result = complete_intake_assessment(result["assessment"])
		self.assertEqual(complete_result["status"], "Completed")
		self.assertTrue(complete_result["completed_by"])
		self.assertTrue(complete_result["completed_on"])

	def test_complete_assessment_missing_mandatory_fails(self):
		"""Cannot complete when mandatory fields are empty."""
		template = _make_intake_template(name="Incomplete Template")
		ir = _make_inpatient_record(patient=_make_patient("IA11"))
		result = create_intake_assessment(ir.name, template_name=template.name)

		# Only fill one of two mandatory fields
		save_responses(result["assessment"], [
			{"idx": 1, "text_value": "headache"},
		])

		with self.assertRaises(frappe.ValidationError):
			complete_intake_assessment(result["assessment"])

	def test_complete_already_completed_fails(self):
		"""Cannot complete an already completed assessment."""
		template = _make_intake_template(
			name="Double Complete Template",
			fields=[{
				"section_label": "Test",
				"field_label": "Test Field",
				"field_type": "Text",
				"is_mandatory": 0,
				"display_order": 10,
				"role_visibility": "All",
			}],
		)
		ir = _make_inpatient_record(patient=_make_patient("IA12"))
		result = create_intake_assessment(ir.name, template_name=template.name)

		complete_intake_assessment(result["assessment"])

		with self.assertRaises(frappe.ValidationError):
			complete_intake_assessment(result["assessment"])

	# ── 8. Scored assessment auto-creation ────────────────────────

	def test_scored_assessments_created(self):
		"""Scored Patient Assessments are auto-created and linked."""
		scored = _make_scored_template("Test GCS for Intake")
		template = _make_intake_template(
			name="Scored Template",
			scored_templates=[scored.name],
		)

		ir = _make_inpatient_record(patient=_make_patient("IA13"))
		result = create_intake_assessment(ir.name, template_name=template.name)

		self.assertEqual(len(result["scored_assessments"]), 1)
		pa_name = result["scored_assessments"][0]["name"]
		pa = frappe.get_doc("Patient Assessment", pa_name)
		self.assertEqual(pa.custom_inpatient_record, ir.name)
		self.assertEqual(pa.custom_intake_assessment, result["assessment"])
		self.assertEqual(pa.assessment_template, scored.name)

	def test_pending_scored_assessments(self):
		"""get_pending_scored_assessments returns unsubmitted PAs."""
		scored = _make_scored_template("Test GCS Pending")
		template = _make_intake_template(
			name="Pending Scored Template",
			scored_templates=[scored.name],
		)

		ir = _make_inpatient_record(patient=_make_patient("IA14"))
		result = create_intake_assessment(ir.name, template_name=template.name)

		pending = get_pending_scored_assessments(result["assessment"])
		self.assertEqual(len(pending), 1)
		self.assertEqual(pending[0]["assessment_template"], scored.name)

	# ── 9. Template versioning ───────────────────────────────────

	def test_template_version_snapshot(self):
		"""Assessment stores template version at creation time."""
		template = _make_intake_template(name="Versioned Template", version=3)
		ir = _make_inpatient_record(patient=_make_patient("IA15"))

		result = create_intake_assessment(ir.name, template_name=template.name)
		doc = frappe.get_doc("IPD Intake Assessment", result["assessment"])
		self.assertEqual(doc.template_version, 3)

	# ── 10. List by IR ───────────────────────────────────────────

	def test_get_assessments_for_ir(self):
		"""Returns all assessments for an Inpatient Record."""
		tmpl1 = _make_intake_template(name="List Template 1")
		tmpl2 = _make_intake_template(
			name="List Template 2",
			target_role="Physician",
		)

		ir = _make_inpatient_record(patient=_make_patient("IA16"))

		create_intake_assessment(ir.name, template_name=tmpl1.name)
		create_intake_assessment(ir.name, template_name=tmpl2.name)

		assessments = get_intake_assessments_for_ir(ir.name)
		self.assertEqual(len(assessments), 2)

	# ── 11. Template validation ──────────────────────────────────

	def test_template_requires_content(self):
		"""Template with no fields and no scored assessments fails."""
		with self.assertRaises(frappe.ValidationError):
			_make_intake_template(
				name="Empty Template",
				fields=[],
				scored_templates=[],
			)

	def test_template_duplicate_field_labels_fail(self):
		"""Template with duplicate field labels in same section fails."""
		with self.assertRaises(frappe.ValidationError):
			_make_intake_template(
				name="Dup Labels Template",
				fields=[
					{
						"section_label": "Vitals",
						"field_label": "BP",
						"field_type": "Text",
						"is_mandatory": 0,
						"display_order": 10,
						"role_visibility": "All",
					},
					{
						"section_label": "Vitals",
						"field_label": "BP",
						"field_type": "Text",
						"is_mandatory": 0,
						"display_order": 20,
						"role_visibility": "All",
					},
				],
			)

	def test_template_select_without_options_fails(self):
		"""Select field type without options fails validation."""
		with self.assertRaises(frappe.ValidationError):
			_make_intake_template(
				name="Bad Select Template",
				fields=[
					{
						"section_label": "Test",
						"field_label": "Bad Select",
						"field_type": "Select",
						"options": "",
						"is_mandatory": 0,
						"display_order": 10,
						"role_visibility": "All",
					},
				],
			)
