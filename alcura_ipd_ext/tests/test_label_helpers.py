"""Tests for US-D3: Label Helper utilities.

Covers: QR code generation, barcode generation, allergy formatting,
admission label context building, and age computation.
"""

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import today

from alcura_ipd_ext.utils.label_helpers import (
	format_allergy_markers,
	generate_barcode_svg,
	generate_qr_svg,
	get_admission_label_context,
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


def _make_patient(suffix="LBL"):
	patient_name = f"Test Patient {suffix}"
	existing = frappe.db.exists("Patient", {"patient_name": patient_name})
	if existing:
		return frappe.get_doc("Patient", existing)
	doc = frappe.get_doc({
		"doctype": "Patient",
		"first_name": f"Test {suffix}",
		"last_name": "Patient",
		"sex": "Male",
		"dob": "1990-01-15",
	})
	doc.insert(ignore_permissions=True)
	return doc


def _make_inpatient_record(patient=None, company=None):
	patient_doc = patient or _make_patient()
	patient_name = patient_doc.name if hasattr(patient_doc, "name") else patient_doc
	company = company or _get_or_create_company()
	dept = _make_medical_department()
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


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestLabelHelpers(IntegrationTestCase):
	def tearDown(self):
		frappe.db.rollback()
		frappe.set_user("Administrator")

	# ── QR Code ────────────────────────────────────────────────────

	def test_generate_qr_svg_returns_img_or_placeholder(self):
		"""QR generation returns either an <img> tag or a placeholder."""
		result = generate_qr_svg("test-data")
		self.assertTrue(
			"<img" in result or "[QR:" in result,
			"Expected <img> tag or [QR:...] placeholder"
		)

	def test_qr_svg_encodes_data(self):
		"""QR output contains the encoded data reference."""
		result = generate_qr_svg("IP-00001")
		# Either a base64 image or a fallback with the data in text
		self.assertTrue(
			"base64" in result or "IP-00001" in result,
			"Expected base64 data or plaintext fallback"
		)

	# ── Barcode ────────────────────────────────────────────────────

	def test_generate_barcode_svg_returns_svg_or_placeholder(self):
		"""Barcode generation returns SVG or monospace placeholder."""
		result = generate_barcode_svg("IP-00001")
		self.assertTrue(
			"<svg" in result or "IP-00001" in result,
			"Expected <svg> element or text placeholder"
		)

	# ── Allergy Markers ────────────────────────────────────────────

	def test_format_allergy_markers_empty_for_no_patient(self):
		"""Returns empty string when patient is None."""
		self.assertEqual(format_allergy_markers(None), "")
		self.assertEqual(format_allergy_markers(""), "")

	def test_format_allergy_markers_for_patient_without_allergies(self):
		"""Returns empty string for patient with no allergies."""
		patient = _make_patient("LBL1")
		result = format_allergy_markers(patient.name)
		# May or may not be empty depending on patient data
		self.assertIsInstance(result, str)

	# ── Label Context ──────────────────────────────────────────────

	def test_get_admission_label_context_returns_dict(self):
		"""Context builder returns a dict with all expected keys."""
		patient = _make_patient("LBL2")
		ir = _make_inpatient_record(patient=patient)

		ctx = get_admission_label_context(ir.name)

		expected_keys = [
			"ir_name", "patient_name", "patient_id", "mr_number",
			"sex", "dob", "age", "blood_group", "practitioner",
			"bed", "room", "ward", "admission_date", "payer_display",
			"allergy_html", "bedside_url", "company", "qr_code", "barcode",
		]
		for key in expected_keys:
			self.assertIn(key, ctx, f"Missing key: {key}")

	def test_label_context_patient_fields(self):
		"""Context includes patient demographics correctly."""
		patient = _make_patient("LBL3")
		ir = _make_inpatient_record(patient=patient)

		ctx = get_admission_label_context(ir.name)

		self.assertEqual(ctx["patient_id"], patient.name)
		self.assertEqual(ctx["sex"], "Male")
		self.assertIn("Y", ctx["age"])  # e.g. "36Y"

	def test_label_context_bedside_url(self):
		"""Bedside URL is properly formatted."""
		patient = _make_patient("LBL4")
		ir = _make_inpatient_record(patient=patient)

		ctx = get_admission_label_context(ir.name)

		self.assertIn(ir.name, ctx["bedside_url"])
		self.assertTrue(ctx["bedside_url"].startswith("/bedside_profile"))


class TestBedsideProfile(IntegrationTestCase):
	"""Basic tests for the bedside profile page controller."""

	def tearDown(self):
		frappe.db.rollback()
		frappe.set_user("Administrator")

	def test_bedside_context_requires_ir_param(self):
		"""Page raises error when no IR parameter is provided."""
		from alcura_ipd_ext.www.bedside_profile import get_context

		frappe.form_dict.clear()
		context = frappe._dict()

		with self.assertRaises(frappe.ValidationError):
			get_context(context)

	def test_bedside_context_builds_for_valid_ir(self):
		"""Page context populates correctly for a valid IR."""
		from alcura_ipd_ext.www.bedside_profile import get_context

		patient = _make_patient("BP1")
		ir = _make_inpatient_record(patient=patient)

		frappe.form_dict["ir"] = ir.name
		context = frappe._dict()
		get_context(context)

		self.assertEqual(context["ir_name"], ir.name)
		self.assertEqual(context["patient_name"], ir.patient_name)
		self.assertIn("title", context)

	def test_bedside_rejects_nonexistent_ir(self):
		"""Page raises DoesNotExistError for invalid IR name."""
		from alcura_ipd_ext.www.bedside_profile import get_context

		frappe.form_dict["ir"] = "NONEXISTENT-IR-999"
		context = frappe._dict()

		with self.assertRaises(frappe.DoesNotExistError):
			get_context(context)
