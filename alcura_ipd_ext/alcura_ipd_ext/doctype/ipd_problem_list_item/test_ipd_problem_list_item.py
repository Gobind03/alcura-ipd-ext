"""Tests for IPD Problem List Item controller (US-E5)."""

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import today, now_datetime


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


def _make_patient(suffix):
	patient_name = f"Test Patient PLI-{suffix}"
	existing = frappe.db.exists("Patient", {"patient_name": patient_name})
	if existing:
		return existing
	doc = frappe.get_doc({
		"doctype": "Patient",
		"first_name": f"Test PLI-{suffix}",
		"last_name": "Patient",
		"sex": "Male",
	})
	doc.insert(ignore_permissions=True)
	return doc.name


def _make_practitioner(suffix):
	fname = f"Dr PLI Test {suffix}"
	existing = frappe.db.exists("Healthcare Practitioner", {"practitioner_name": fname})
	if existing:
		return existing
	doc = frappe.get_doc({
		"doctype": "Healthcare Practitioner",
		"first_name": "Dr PLI Test",
		"last_name": suffix,
	})
	doc.insert(ignore_permissions=True)
	return doc.name


def _make_ir(patient=None, status="Admitted"):
	patient = patient or _make_patient("default")
	company = _get_or_create_company()
	practitioner = _make_practitioner("default")

	if not frappe.db.exists("Medical Department", "Test PLI Dept"):
		frappe.get_doc({"doctype": "Medical Department", "department": "Test PLI Dept"}).insert(ignore_permissions=True)

	doc = frappe.get_doc({
		"doctype": "Inpatient Record",
		"patient": patient,
		"company": company,
		"primary_practitioner": practitioner,
		"medical_department": "Test PLI Dept",
		"scheduled_date": today(),
		"status": status,
	})
	doc.insert(ignore_permissions=True)
	return doc


class TestIPDProblemListItem(IntegrationTestCase):
	def tearDown(self):
		frappe.db.rollback()
		frappe.set_user("Administrator")

	def test_auto_sets_added_on(self):
		"""added_on is automatically set on insert."""
		ir = _make_ir(patient=_make_patient("AO1"))
		doc = frappe.get_doc({
			"doctype": "IPD Problem List Item",
			"patient": ir.patient,
			"inpatient_record": ir.name,
			"company": ir.company,
			"problem_description": "Test problem",
		})
		doc.insert(ignore_permissions=True)
		self.assertIsNotNone(doc.added_on)

	def test_status_defaults_to_active(self):
		"""Default status is Active."""
		ir = _make_ir(patient=_make_patient("SD1"))
		doc = frappe.get_doc({
			"doctype": "IPD Problem List Item",
			"patient": ir.patient,
			"inpatient_record": ir.name,
			"company": ir.company,
			"problem_description": "Test problem",
		})
		doc.insert(ignore_permissions=True)
		self.assertEqual(doc.status, "Active")

	def test_resolved_fields_set_on_resolve(self):
		"""resolved_on is set when status changes to Resolved."""
		ir = _make_ir(patient=_make_patient("RF1"))
		doc = frappe.get_doc({
			"doctype": "IPD Problem List Item",
			"patient": ir.patient,
			"inpatient_record": ir.name,
			"company": ir.company,
			"problem_description": "Test resolve",
		})
		doc.insert(ignore_permissions=True)
		self.assertIsNone(doc.resolved_on)

		doc.status = "Resolved"
		doc.save(ignore_permissions=True)
		self.assertIsNotNone(doc.resolved_on)

	def test_resolved_fields_cleared_on_reactivate(self):
		"""resolved_on/by cleared when status changes back from Resolved."""
		ir = _make_ir(patient=_make_patient("RC1"))
		doc = frappe.get_doc({
			"doctype": "IPD Problem List Item",
			"patient": ir.patient,
			"inpatient_record": ir.name,
			"company": ir.company,
			"problem_description": "Test reactivate",
		})
		doc.insert(ignore_permissions=True)

		doc.status = "Resolved"
		doc.save(ignore_permissions=True)
		self.assertIsNotNone(doc.resolved_on)

		doc.status = "Active"
		doc.save(ignore_permissions=True)
		self.assertIsNone(doc.resolved_on)
		self.assertIsNone(doc.resolved_by)

	def test_validates_ir_status(self):
		"""Cannot add problem when IR is discharged."""
		ir = _make_ir(patient=_make_patient("VS1"), status="Discharged")
		doc = frappe.get_doc({
			"doctype": "IPD Problem List Item",
			"patient": ir.patient,
			"inpatient_record": ir.name,
			"company": ir.company,
			"problem_description": "Should fail",
		})
		with self.assertRaises(frappe.ValidationError):
			doc.insert(ignore_permissions=True)

	def test_ir_count_updated_on_insert(self):
		"""custom_active_problems_count is updated when a problem is inserted."""
		ir = _make_ir(patient=_make_patient("IC1"))

		doc = frappe.get_doc({
			"doctype": "IPD Problem List Item",
			"patient": ir.patient,
			"inpatient_record": ir.name,
			"company": ir.company,
			"problem_description": "Count test",
		})
		doc.insert(ignore_permissions=True)

		count = frappe.db.get_value(
			"Inpatient Record", ir.name, "custom_active_problems_count"
		)
		self.assertEqual(count, 1)

	def test_ir_count_updated_on_trash(self):
		"""custom_active_problems_count decreases on delete."""
		ir = _make_ir(patient=_make_patient("IC2"))

		doc = frappe.get_doc({
			"doctype": "IPD Problem List Item",
			"patient": ir.patient,
			"inpatient_record": ir.name,
			"company": ir.company,
			"problem_description": "Delete test",
		})
		doc.insert(ignore_permissions=True)

		count = frappe.db.get_value(
			"Inpatient Record", ir.name, "custom_active_problems_count"
		)
		self.assertEqual(count, 1)

		doc.delete(ignore_permissions=True)

		count = frappe.db.get_value(
			"Inpatient Record", ir.name, "custom_active_problems_count"
		)
		self.assertEqual(count, 0)
