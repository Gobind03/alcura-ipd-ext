"""Tests for US-E5: Round Sheet Service.

Covers: doctor census, patient round summary, problem list CRUD,
problem list validation, progress note creation with problem snapshot,
pending lab test detection, IR count updates, and permission checks.
"""

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import today, add_days, now_datetime

from alcura_ipd_ext.services.round_sheet_service import (
	add_problem,
	create_progress_note_encounter,
	get_active_problems,
	get_doctor_census,
	get_patient_round_summary,
	get_pending_lab_tests,
	resolve_problem,
	update_ir_problem_count,
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


def _make_medical_department(name="Test General E5"):
	if frappe.db.exists("Medical Department", name):
		return name
	doc = frappe.get_doc({
		"doctype": "Medical Department",
		"department": name,
	})
	doc.insert(ignore_permissions=True)
	return doc.name


def _make_practitioner(suffix="E5"):
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


def _make_patient(suffix="E5"):
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
	**kwargs,
):
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
		**kwargs,
	})
	doc.insert(ignore_permissions=True)
	return doc


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestRoundSheetService(IntegrationTestCase):
	def tearDown(self):
		frappe.db.rollback()
		frappe.set_user("Administrator")

	# ── 1. Doctor Census ────────────────────────────────────────────

	def test_census_returns_admitted_patients(self):
		"""Census returns only admitted patients for the specified practitioner."""
		practitioner = _make_practitioner("CEN1")
		ir1 = _make_inpatient_record(
			patient=_make_patient("CEN1a"),
			practitioner=practitioner,
			status="Admitted",
		)
		ir2 = _make_inpatient_record(
			patient=_make_patient("CEN1b"),
			practitioner=practitioner,
			status="Admitted",
		)

		census = get_doctor_census(practitioner)

		ir_names = [r["inpatient_record"] for r in census]
		self.assertIn(ir1.name, ir_names)
		self.assertIn(ir2.name, ir_names)

	def test_census_excludes_discharged(self):
		"""Census excludes patients with non-Admitted status."""
		practitioner = _make_practitioner("CEN2")
		ir_admitted = _make_inpatient_record(
			patient=_make_patient("CEN2a"),
			practitioner=practitioner,
			status="Admitted",
		)
		ir_discharged = _make_inpatient_record(
			patient=_make_patient("CEN2b"),
			practitioner=practitioner,
			status="Discharged",
		)

		census = get_doctor_census(practitioner)

		ir_names = [r["inpatient_record"] for r in census]
		self.assertIn(ir_admitted.name, ir_names)
		self.assertNotIn(ir_discharged.name, ir_names)

	def test_census_excludes_other_practitioner(self):
		"""Census only returns patients for the specified practitioner."""
		p1 = _make_practitioner("CEN3a")
		p2 = _make_practitioner("CEN3b")

		ir1 = _make_inpatient_record(
			patient=_make_patient("CEN3a"),
			practitioner=p1,
			status="Admitted",
		)
		ir2 = _make_inpatient_record(
			patient=_make_patient("CEN3b"),
			practitioner=p2,
			status="Admitted",
		)

		census_p1 = get_doctor_census(p1)
		ir_names = [r["inpatient_record"] for r in census_p1]
		self.assertIn(ir1.name, ir_names)
		self.assertNotIn(ir2.name, ir_names)

	def test_census_includes_days_admitted(self):
		"""Census includes computed days_admitted field."""
		practitioner = _make_practitioner("CEN4")
		ir = _make_inpatient_record(
			patient=_make_patient("CEN4"),
			practitioner=practitioner,
			status="Admitted",
		)

		census = get_doctor_census(practitioner)
		row = next(r for r in census if r["inpatient_record"] == ir.name)
		self.assertEqual(row["days_admitted"], 1)

	# ── 2. Problem List CRUD ─────────────────────────────────────────

	def test_add_problem(self):
		"""Adding a problem creates an IPD Problem List Item."""
		ir = _make_inpatient_record(patient=_make_patient("PL1"), status="Admitted")

		result = add_problem(
			inpatient_record=ir.name,
			problem_description="Uncontrolled DM Type 2",
			severity="Moderate",
		)

		self.assertTrue(result["name"])
		doc = frappe.get_doc("IPD Problem List Item", result["name"])
		self.assertEqual(doc.problem_description, "Uncontrolled DM Type 2")
		self.assertEqual(doc.severity, "Moderate")
		self.assertEqual(doc.status, "Active")
		self.assertEqual(doc.patient, ir.patient)

	def test_resolve_problem(self):
		"""Resolving a problem sets status, resolved_by, resolved_on."""
		ir = _make_inpatient_record(patient=_make_patient("PL2"), status="Admitted")
		practitioner = _make_practitioner("PL2")

		result = add_problem(
			inpatient_record=ir.name,
			problem_description="Acute kidney injury",
		)

		resolve_result = resolve_problem(
			problem_name=result["name"],
			resolution_notes="Creatinine normalised",
			practitioner=practitioner,
		)

		self.assertEqual(resolve_result["status"], "Resolved")
		doc = frappe.get_doc("IPD Problem List Item", result["name"])
		self.assertEqual(doc.status, "Resolved")
		self.assertEqual(doc.resolution_notes, "Creatinine normalised")
		self.assertEqual(doc.resolved_by, practitioner)
		self.assertIsNotNone(doc.resolved_on)

	def test_resolve_already_resolved_throws(self):
		"""Cannot resolve an already-resolved problem."""
		ir = _make_inpatient_record(patient=_make_patient("PL3"), status="Admitted")

		result = add_problem(
			inpatient_record=ir.name,
			problem_description="Test problem",
		)
		resolve_problem(problem_name=result["name"])

		with self.assertRaises(Exception):
			resolve_problem(problem_name=result["name"])

	def test_get_active_problems(self):
		"""get_active_problems returns Active and Monitoring items, sorted."""
		ir = _make_inpatient_record(patient=_make_patient("PL4"), status="Admitted")

		add_problem(ir.name, "Problem A", severity="Mild")
		add_problem(ir.name, "Problem B", severity="Severe")

		res = add_problem(ir.name, "Problem C")
		resolve_problem(res["name"])

		problems = get_active_problems(ir.name)
		descriptions = [p["problem_description"] for p in problems]
		self.assertIn("Problem A", descriptions)
		self.assertIn("Problem B", descriptions)
		self.assertNotIn("Problem C", descriptions)

	def test_ir_problem_count_updated(self):
		"""Adding/resolving problems updates the IR custom field."""
		ir = _make_inpatient_record(patient=_make_patient("PL5"), status="Admitted")

		add_problem(ir.name, "Problem 1")
		res2 = add_problem(ir.name, "Problem 2")

		count = frappe.db.get_value(
			"Inpatient Record", ir.name, "custom_active_problems_count"
		)
		self.assertEqual(count, 2)

		resolve_problem(res2["name"])

		count = frappe.db.get_value(
			"Inpatient Record", ir.name, "custom_active_problems_count"
		)
		self.assertEqual(count, 1)

	# ── 3. Problem List Validation ────────────────────────────────────

	def test_problem_cannot_be_added_to_discharged_ir(self):
		"""Cannot add a problem to a discharged Inpatient Record."""
		ir = _make_inpatient_record(patient=_make_patient("PL6"), status="Discharged")

		with self.assertRaises(frappe.ValidationError):
			add_problem(
				inpatient_record=ir.name,
				problem_description="Should fail",
			)

	def test_problem_sequence_auto_increments(self):
		"""Each new problem gets an auto-incremented sequence_number."""
		ir = _make_inpatient_record(patient=_make_patient("PL7"), status="Admitted")

		r1 = add_problem(ir.name, "First")
		r2 = add_problem(ir.name, "Second")

		doc1 = frappe.get_doc("IPD Problem List Item", r1["name"])
		doc2 = frappe.get_doc("IPD Problem List Item", r2["name"])
		self.assertLess(doc1.sequence_number, doc2.sequence_number)

	# ── 4. Progress Note Encounter ──────────────────────────────────

	def test_create_progress_note_encounter(self):
		"""Progress note encounter is created with problem snapshot."""
		ir = _make_inpatient_record(patient=_make_patient("PN1"), status="Admitted")

		add_problem(ir.name, "Hypertension", severity="Moderate")
		add_problem(ir.name, "DM Type 2", severity="Mild")

		result = create_progress_note_encounter(inpatient_record=ir.name)

		self.assertTrue(result["encounter"])
		self.assertEqual(result["note_type"], "Progress Note")

		enc = frappe.get_doc("Patient Encounter", result["encounter"])
		self.assertEqual(enc.custom_ipd_note_type, "Progress Note")
		self.assertIn("Hypertension", enc.custom_active_problems_text)
		self.assertIn("DM Type 2", enc.custom_active_problems_text)

	def test_progress_note_updates_last_note_date(self):
		"""Creating a progress note updates the IR's last progress note date."""
		ir = _make_inpatient_record(patient=_make_patient("PN2"), status="Admitted")

		create_progress_note_encounter(inpatient_record=ir.name)

		last_date = frappe.db.get_value(
			"Inpatient Record", ir.name, "custom_last_progress_note_date"
		)
		self.assertEqual(str(last_date), today())

	def test_progress_note_without_problems(self):
		"""Progress note works even with no active problems."""
		ir = _make_inpatient_record(patient=_make_patient("PN3"), status="Admitted")

		result = create_progress_note_encounter(inpatient_record=ir.name)
		self.assertTrue(result["encounter"])

		enc = frappe.get_doc("Patient Encounter", result["encounter"])
		self.assertFalse(enc.custom_active_problems_text)

	# ── 5. Patient Round Summary ─────────────────────────────────────

	def test_patient_round_summary_structure(self):
		"""Round summary returns all expected data sections."""
		ir = _make_inpatient_record(
			patient=_make_patient("RS1"),
			status="Admitted",
			custom_allergy_alert=1,
			custom_allergy_summary="Penicillin",
		)

		add_problem(ir.name, "Chest pain")

		summary = get_patient_round_summary(ir.name)

		self.assertIn("patient", summary)
		self.assertIn("location", summary)
		self.assertIn("alerts", summary)
		self.assertIn("active_problems", summary)
		self.assertIn("recent_vitals", summary)
		self.assertIn("pending_lab_tests", summary)
		self.assertIn("due_medications", summary)
		self.assertIn("fluid_balance", summary)
		self.assertIn("recent_notes", summary)

		self.assertEqual(len(summary["active_problems"]), 1)
		self.assertEqual(summary["active_problems"][0]["problem_description"], "Chest pain")

		allergy_alerts = [a for a in summary["alerts"] if a["type"] == "allergy"]
		self.assertEqual(len(allergy_alerts), 1)

	def test_round_summary_nonexistent_ir(self):
		"""Querying a non-existent IR raises DoesNotExistError."""
		with self.assertRaises(frappe.DoesNotExistError):
			get_patient_round_summary("IR-NONEXISTENT-999")

	# ── 6. Pending Lab Tests ─────────────────────────────────────────

	def test_pending_labs_empty_when_no_prescriptions(self):
		"""No pending labs when there are no encounters with prescriptions."""
		ir = _make_inpatient_record(patient=_make_patient("LT1"), status="Admitted")

		pending = get_pending_lab_tests(ir.name)
		self.assertEqual(pending, [])

	# ── 7. Update IR Problem Count ───────────────────────────────────

	def test_update_ir_problem_count_explicit(self):
		"""Explicit recount updates the IR field correctly."""
		ir = _make_inpatient_record(patient=_make_patient("UC1"), status="Admitted")

		add_problem(ir.name, "Problem X")
		add_problem(ir.name, "Problem Y")

		frappe.db.set_value(
			"Inpatient Record", ir.name,
			"custom_active_problems_count", 999,
			update_modified=False,
		)

		new_count = update_ir_problem_count(ir.name)
		self.assertEqual(new_count, 2)

		stored = frappe.db.get_value(
			"Inpatient Record", ir.name, "custom_active_problems_count"
		)
		self.assertEqual(stored, 2)
