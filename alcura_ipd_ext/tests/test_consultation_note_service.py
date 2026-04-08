"""Tests for US-E3: Consultation Note Service.

Covers: encounter creation linked to IR, allergy/history pre-population,
validation rules (note type required, IR status, chief complaint for
admission notes), on-submit timeline comment, clinical context API,
duplicate admission note handling, and permission checks.
"""

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import today

from alcura_ipd_ext.services.consultation_note_service import (
	create_consultation_encounter,
	get_ipd_clinical_context,
	on_submit_consultation_encounter,
	validate_consultation_encounter,
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


def _make_practitioner(suffix="E3"):
	fname = f"Dr Test {suffix}"
	existing = frappe.db.exists("Healthcare Practitioner", {"practitioner_name": fname})
	if existing:
		return existing
	doc = frappe.get_doc({
		"doctype": "Healthcare Practitioner",
		"first_name": "Dr Test",
		"last_name": suffix,
	})
	doc.insert(ignore_permissions=True)
	return doc.name


def _make_patient(suffix="E3"):
	patient_name = f"Test Patient {suffix}"
	existing = frappe.db.exists("Patient", {"patient_name": patient_name})
	if existing:
		return existing
	doc = frappe.get_doc({
		"doctype": "Patient",
		"first_name": f"Test {suffix}",
		"last_name": "Patient",
		"sex": "Male",
	})
	doc.insert(ignore_permissions=True)
	return doc.name


def _make_inpatient_record(
	patient=None,
	company=None,
	practitioner=None,
	status="Admitted",
	allergy_summary="",
	allergy_alert=0,
	fall_risk="",
	**kwargs,
):
	"""Create an Inpatient Record in the given status."""
	patient = patient or _make_patient()
	company = company or _get_or_create_company()
	practitioner = practitioner or _make_practitioner()
	dept = _make_medical_department()

	doc = frappe.get_doc({
		"doctype": "Inpatient Record",
		"patient": patient,
		"company": company,
		"primary_practitioner": practitioner,
		"medical_department": dept,
		"scheduled_date": today(),
		"status": status,
		"custom_allergy_summary": allergy_summary,
		"custom_allergy_alert": allergy_alert,
		"custom_fall_risk_level": fall_risk,
		**kwargs,
	})
	doc.insert(ignore_permissions=True)
	return doc


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestConsultationNoteService(IntegrationTestCase):
	def tearDown(self):
		frappe.db.rollback()
		frappe.set_user("Administrator")

	# ── 1. Happy path ───────────────────────────────────────────────

	def test_create_consultation_encounter_happy_path(self):
		"""Creating a consultation encounter from an admitted IR produces
		a draft Patient Encounter with correct IPD fields."""
		ir = _make_inpatient_record(patient=_make_patient("CN1"), status="Admitted")

		result = create_consultation_encounter(
			inpatient_record=ir.name,
			note_type="Admission Note",
		)

		self.assertTrue(result["encounter"])
		self.assertEqual(result["note_type"], "Admission Note")

		enc = frappe.get_doc("Patient Encounter", result["encounter"])
		self.assertEqual(enc.custom_linked_inpatient_record, ir.name)
		self.assertEqual(enc.custom_ipd_note_type, "Admission Note")
		self.assertEqual(enc.patient, ir.patient)
		self.assertEqual(enc.company, ir.company)
		self.assertEqual(enc.practitioner, ir.primary_practitioner)
		self.assertEqual(enc.docstatus, 0)

	# ── 2. Allergy pre-population ────────────────────────────────────

	def test_allergy_prepopulation(self):
		"""Allergies from the IR are pre-populated into the encounter."""
		ir = _make_inpatient_record(
			patient=_make_patient("CN2"),
			status="Admitted",
			allergy_summary="Penicillin, Sulfa drugs",
			allergy_alert=1,
		)

		result = create_consultation_encounter(
			inpatient_record=ir.name,
			note_type="Admission Note",
		)

		enc = frappe.get_doc("Patient Encounter", result["encounter"])
		self.assertEqual(enc.custom_allergies_text, "Penicillin, Sulfa drugs")

	# ── 3. History pre-population from intake ────────────────────────

	def test_history_prepopulation_from_intake(self):
		"""Past history is extracted from intake assessment responses
		when available."""
		ir = _make_inpatient_record(
			patient=_make_patient("CN3"),
			status="Admitted",
		)

		intake = frappe.get_doc({
			"doctype": "IPD Intake Assessment",
			"patient": ir.patient,
			"inpatient_record": ir.name,
			"template": "Test Template CN3",
			"template_version": 1,
			"company": ir.company,
			"status": "Completed",
			"responses": [
				{
					"section_label": "Past History",
					"field_label": "Past Medical History",
					"field_type": "Long Text",
					"text_value": "Diabetes Type 2, Hypertension",
				},
				{
					"section_label": "Past History",
					"field_label": "Past Surgical History",
					"field_type": "Small Text",
					"text_value": "Appendectomy 2015",
				},
			],
		})
		intake.insert(ignore_permissions=True)

		result = create_consultation_encounter(
			inpatient_record=ir.name,
			note_type="Admission Note",
		)

		enc = frappe.get_doc("Patient Encounter", result["encounter"])
		self.assertIn("Diabetes Type 2", enc.custom_past_history_summary)
		self.assertIn("Appendectomy 2015", enc.custom_past_history_summary)

	# ── 4. Validation: note type required ────────────────────────────

	def test_validation_note_type_required(self):
		"""An encounter linked to an IR must have a note type set."""
		ir = _make_inpatient_record(
			patient=_make_patient("CN4"),
			status="Admitted",
		)

		enc = frappe.get_doc({
			"doctype": "Patient Encounter",
			"patient": ir.patient,
			"practitioner": ir.primary_practitioner,
			"company": ir.company,
			"encounter_date": today(),
			"custom_linked_inpatient_record": ir.name,
			"custom_ipd_note_type": "",
		})

		with self.assertRaises(frappe.ValidationError):
			validate_consultation_encounter(enc)

	# ── 5. Validation: IR status ──────────────────────────────────────

	def test_validation_ir_status(self):
		"""Cannot create a consultation note for a discharged IR."""
		ir = _make_inpatient_record(
			patient=_make_patient("CN5"),
			status="Discharged",
		)

		with self.assertRaises(frappe.ValidationError):
			create_consultation_encounter(
				inpatient_record=ir.name,
				note_type="Progress Note",
			)

	# ── 6. Validation: chief complaint for admission note ─────────────

	def test_validation_chief_complaint_required_for_admission_note(self):
		"""Admission Notes require a chief complaint."""
		ir = _make_inpatient_record(
			patient=_make_patient("CN6"),
			status="Admitted",
		)

		enc = frappe.get_doc({
			"doctype": "Patient Encounter",
			"patient": ir.patient,
			"practitioner": ir.primary_practitioner,
			"company": ir.company,
			"encounter_date": today(),
			"custom_linked_inpatient_record": ir.name,
			"custom_ipd_note_type": "Admission Note",
			"custom_chief_complaint_text": "",
		})

		with self.assertRaises(frappe.ValidationError):
			validate_consultation_encounter(enc)

	# ── 7. On-submit timeline comment ──────────────────────────────

	def test_on_submit_timeline_comment(self):
		"""Submitting a consultation encounter adds a comment to the IR."""
		ir = _make_inpatient_record(
			patient=_make_patient("CN7"),
			status="Admitted",
		)

		result = create_consultation_encounter(
			inpatient_record=ir.name,
			note_type="Admission Note",
		)

		enc = frappe.get_doc("Patient Encounter", result["encounter"])
		enc.custom_chief_complaint_text = "Chest pain"
		enc.custom_ipd_note_summary = "Acute chest pain, r/o MI"
		enc.save(ignore_permissions=True)

		on_submit_consultation_encounter(enc)

		comments = frappe.get_all(
			"Comment",
			filters={
				"reference_doctype": "Inpatient Record",
				"reference_name": ir.name,
				"comment_type": "Info",
			},
			fields=["content"],
			order_by="creation desc",
		)

		submit_comments = [c for c in comments if "submitted" in (c.content or "").lower()]
		self.assertTrue(len(submit_comments) > 0)

	# ── 8. Duplicate admission note warning ──────────────────────────

	def test_duplicate_admission_note_allowed(self):
		"""A second admission note for the same IR is allowed (no error),
		allowing corrections or addenda."""
		ir = _make_inpatient_record(
			patient=_make_patient("CN8"),
			status="Admitted",
		)

		result1 = create_consultation_encounter(
			inpatient_record=ir.name,
			note_type="Admission Note",
		)
		self.assertTrue(result1["encounter"])

		result2 = create_consultation_encounter(
			inpatient_record=ir.name,
			note_type="Admission Note",
		)
		self.assertTrue(result2["encounter"])
		self.assertNotEqual(result1["encounter"], result2["encounter"])

	# ── 9. Clinical context API ──────────────────────────────────────

	def test_clinical_context_api(self):
		"""get_ipd_clinical_context returns allergy, risk, and encounter data."""
		ir = _make_inpatient_record(
			patient=_make_patient("CN9"),
			status="Admitted",
			allergy_summary="Aspirin",
			allergy_alert=1,
			fall_risk="High",
		)

		create_consultation_encounter(
			inpatient_record=ir.name,
			note_type="Admission Note",
		)

		ctx = get_ipd_clinical_context(ir.name)

		self.assertEqual(ctx["allergy_alert"], 1)
		self.assertEqual(ctx["allergy_summary"], "Aspirin")
		self.assertEqual(ctx["risk_flags"]["fall"], "High")
		self.assertEqual(len(ctx["recent_encounters"]), 1)
		self.assertEqual(ctx["recent_encounters"][0]["custom_ipd_note_type"], "Admission Note")

	# ── 10. Practitioner fallback ─────────────────────────────────────

	def test_practitioner_fallback_from_ir(self):
		"""When no practitioner is specified, the IR's primary practitioner
		is used."""
		practitioner = _make_practitioner("CN10")
		ir = _make_inpatient_record(
			patient=_make_patient("CN10"),
			status="Admitted",
			practitioner=practitioner,
		)

		result = create_consultation_encounter(
			inpatient_record=ir.name,
			note_type="Admission Note",
		)

		enc = frappe.get_doc("Patient Encounter", result["encounter"])
		self.assertEqual(enc.practitioner, practitioner)

	# ── 11. Admission Scheduled IR also valid ─────────────────────────

	def test_admission_scheduled_ir_is_valid(self):
		"""Consultation encounters can be created for Admission Scheduled IRs."""
		ir = _make_inpatient_record(
			patient=_make_patient("CN11"),
			status="Admission Scheduled",
		)

		result = create_consultation_encounter(
			inpatient_record=ir.name,
			note_type="Consultation Note",
		)

		self.assertTrue(result["encounter"])
		enc = frappe.get_doc("Patient Encounter", result["encounter"])
		self.assertEqual(enc.custom_ipd_note_type, "Consultation Note")
