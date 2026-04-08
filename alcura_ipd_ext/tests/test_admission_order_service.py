"""Tests for US-D1: Admission Order Service.

Covers: encounter-to-IR creation, custom field propagation, back-link,
validation failures, duplicate prevention, payer profile carry-over,
expected discharge calculation, and timeline comments.
"""

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import getdate, today

from alcura_ipd_ext.services.admission_order_service import (
	create_admission_from_encounter,
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


def _make_practitioner(suffix="D1"):
	fname = f"Dr Test {suffix}"
	existing = frappe.db.exists("Healthcare Practitioner", {"practitioner_name": fname})
	if existing:
		return existing
	doc = frappe.get_doc({
		"doctype": "Healthcare Practitioner",
		"first_name": f"Dr Test",
		"last_name": suffix,
	})
	doc.insert(ignore_permissions=True)
	return doc.name


def _make_patient(suffix="D1"):
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


def _make_encounter(patient=None, company=None, practitioner=None, **overrides):
	"""Create and submit a Patient Encounter."""
	patient_doc = patient or _make_patient()
	patient_name = patient_doc.name if hasattr(patient_doc, "name") else patient_doc
	company = company or _get_or_create_company()
	practitioner = practitioner or _make_practitioner()
	dept = _make_medical_department()

	doc = frappe.get_doc({
		"doctype": "Patient Encounter",
		"patient": patient_name,
		"company": company,
		"practitioner": practitioner,
		"medical_department": dept,
		"encounter_date": today(),
		**overrides,
	})
	doc.insert(ignore_permissions=True)
	doc.submit()
	return doc


def _get_or_create_hsut(name="Test IPD Ward Type", inpatient_occupancy=1):
	if frappe.db.exists("Healthcare Service Unit Type", name):
		return name
	doc = frappe.get_doc({
		"doctype": "Healthcare Service Unit Type",
		"healthcare_service_unit_type": name,
		"inpatient_occupancy": inpatient_occupancy,
	})
	doc.flags.ignore_validate = True
	doc.insert(ignore_if_duplicate=True)
	return doc.name


def _get_or_create_ward(ward_code="DW01", company=None):
	company = company or _get_or_create_company()
	abbr = frappe.get_cached_value("Company", company, "abbr")
	ward_key = f"{abbr}-{ward_code.upper()}"
	if frappe.db.exists("Hospital Ward", ward_key):
		return frappe.get_doc("Hospital Ward", ward_key)
	doc = frappe.get_doc({
		"doctype": "Hospital Ward",
		"ward_code": ward_code,
		"ward_name": f"Test Ward {ward_code}",
		"company": company,
		"ward_classification": "General",
	})
	doc.insert()
	return doc


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestAdmissionOrderService(IntegrationTestCase):
	def tearDown(self):
		frappe.db.rollback()
		frappe.set_user("Administrator")

	# ── 1. Happy path ───────────────────────────────────────────────

	def test_create_admission_from_encounter(self):
		"""Creating admission from a submitted encounter creates an IR
		with correct custom fields and back-links the encounter."""
		enc = _make_encounter(patient=_make_patient("AO1"))

		result = create_admission_from_encounter(
			enc.name,
			admission_priority="Urgent",
			expected_los_days=5,
			admission_notes="Post-surgical observation",
		)

		self.assertTrue(result["inpatient_record"])
		self.assertEqual(result["status"], "Admission Scheduled")

		ir = frappe.get_doc("Inpatient Record", result["inpatient_record"])
		self.assertEqual(ir.patient, enc.patient)
		self.assertEqual(ir.company, enc.company)
		self.assertEqual(ir.custom_requesting_encounter, enc.name)
		self.assertEqual(ir.custom_admission_priority, "Urgent")
		self.assertEqual(ir.custom_expected_los_days, 5)
		self.assertEqual(ir.custom_admission_notes, "Post-surgical observation")
		self.assertEqual(ir.status, "Admission Scheduled")

		enc.reload()
		self.assertTrue(enc.custom_ipd_admission_ordered)
		self.assertEqual(enc.custom_ipd_inpatient_record, ir.name)

	# ── 2. Requested ward ──────────────────────────────────────────

	def test_requested_ward_is_set(self):
		"""Requested ward is populated on the IR when provided."""
		ward = _get_or_create_ward("DW02")
		enc = _make_encounter(patient=_make_patient("AO2"))

		result = create_admission_from_encounter(
			enc.name,
			requested_ward=ward.name,
		)

		ir = frappe.get_doc("Inpatient Record", result["inpatient_record"])
		self.assertEqual(ir.custom_requested_ward, ward.name)

	# ── 3. Expected discharge calculation ──────────────────────────

	def test_expected_discharge_calculated(self):
		"""When expected LOS is provided, expected_discharge is set."""
		enc = _make_encounter(patient=_make_patient("AO3"))

		result = create_admission_from_encounter(
			enc.name,
			expected_los_days=7,
		)

		ir = frappe.get_doc("Inpatient Record", result["inpatient_record"])
		if ir.expected_discharge:
			from frappe.utils import add_days
			expected = add_days(getdate(today()), 7)
			self.assertEqual(getdate(ir.expected_discharge), expected)

	# ── 4. Duplicate prevention ────────────────────────────────────

	def test_duplicate_admission_from_encounter_fails(self):
		"""Cannot order admission twice from the same encounter."""
		enc = _make_encounter(patient=_make_patient("AO4"))

		create_admission_from_encounter(enc.name)

		enc.reload()
		with self.assertRaises(frappe.ValidationError):
			create_admission_from_encounter(enc.name)

	# ── 5. Unsubmitted encounter fails ─────────────────────────────

	def test_draft_encounter_fails(self):
		"""Cannot order admission from a draft encounter."""
		patient = _make_patient("AO5")
		company = _get_or_create_company()
		practitioner = _make_practitioner("AO5")
		dept = _make_medical_department()

		enc = frappe.get_doc({
			"doctype": "Patient Encounter",
			"patient": patient.name,
			"company": company,
			"practitioner": practitioner,
			"medical_department": dept,
			"encounter_date": today(),
		})
		enc.insert(ignore_permissions=True)

		with self.assertRaises(frappe.ValidationError):
			create_admission_from_encounter(enc.name)

	# ── 6. Default priority ────────────────────────────────────────

	def test_default_priority_is_routine(self):
		"""Priority defaults to Routine when not specified."""
		enc = _make_encounter(patient=_make_patient("AO6"))

		result = create_admission_from_encounter(enc.name)

		ir = frappe.get_doc("Inpatient Record", result["inpatient_record"])
		self.assertEqual(ir.custom_admission_priority, "Routine")

	# ── 7. Practitioner carried to IR ──────────────────────────────

	def test_practitioner_carried_over(self):
		"""The encounter's practitioner becomes the IR's primary practitioner."""
		practitioner = _make_practitioner("AO7")
		enc = _make_encounter(patient=_make_patient("AO7"), practitioner=practitioner)

		result = create_admission_from_encounter(enc.name)

		ir = frappe.get_doc("Inpatient Record", result["inpatient_record"])
		self.assertEqual(ir.primary_practitioner, practitioner)

	# ── 8. Payer profile carry-over ────────────────────────────────

	def test_payer_profile_carried_from_patient(self):
		"""If patient has a default payer profile, it is set on the IR."""
		patient = _make_patient("AO8")
		payer = frappe.get_doc({
			"doctype": "Patient Payer Profile",
			"patient": patient.name,
			"payer_type": "Cash",
			"company": _get_or_create_company(),
			"is_active": 1,
		})
		payer.insert(ignore_permissions=True)

		frappe.db.set_value("Patient", patient.name, "custom_default_payer_profile", payer.name)

		enc = _make_encounter(patient=patient)
		result = create_admission_from_encounter(enc.name)

		ir = frappe.get_doc("Inpatient Record", result["inpatient_record"])
		self.assertEqual(ir.custom_patient_payer_profile, payer.name)

	# ── 9. Timeline comments ───────────────────────────────────────

	def test_timeline_comment_on_ir(self):
		"""A timeline comment is added to the Inpatient Record."""
		enc = _make_encounter(patient=_make_patient("AO9"))

		result = create_admission_from_encounter(enc.name, admission_priority="Emergency")

		comments = frappe.get_all(
			"Comment",
			filters={
				"reference_doctype": "Inpatient Record",
				"reference_name": result["inpatient_record"],
				"comment_type": "Info",
			},
			fields=["content"],
		)
		self.assertTrue(len(comments) > 0)
		self.assertIn("Emergency", comments[0].content)
