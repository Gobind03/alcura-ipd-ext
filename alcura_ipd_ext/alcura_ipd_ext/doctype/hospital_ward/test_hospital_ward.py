"""Tests for Hospital Ward DocType.

Covers: autoname, validation, uniqueness, critical-care flag, HSU linkage,
capacity computation, and deactivation.
"""

import frappe
import frappe.defaults
import pytest
from frappe.tests import IntegrationTestCase


def _get_or_create_company(abbr="TST", name="Test Hospital Pvt Ltd"):
	if frappe.db.exists("Company", name):
		return name
	company = frappe.get_doc(
		{
			"doctype": "Company",
			"company_name": name,
			"abbr": abbr,
			"default_currency": "INR",
			"country": "India",
		}
	)
	company.insert(ignore_if_duplicate=True)
	return company.name


def _get_or_create_second_company(abbr="TS2", name="Second Hospital Pvt Ltd"):
	return _get_or_create_company(abbr=abbr, name=name)


def _make_ward(ward_code="GW01", company=None, **overrides):
	company = company or _get_or_create_company()
	doc = frappe.get_doc(
		{
			"doctype": "Hospital Ward",
			"ward_code": ward_code,
			"ward_name": overrides.pop("ward_name", f"Test Ward {ward_code}"),
			"company": company,
			"ward_classification": overrides.pop("ward_classification", "General"),
			**overrides,
		}
	)
	doc.insert()
	return doc


class TestHospitalWard(IntegrationTestCase):
	"""Integration tests for Hospital Ward."""

	def tearDown(self):
		frappe.db.rollback()

	def test_create_ward(self):
		"""A valid Hospital Ward saves without error."""
		ward = _make_ward(ward_code="CRE01")
		self.assertTrue(ward.name)
		self.assertEqual(ward.ward_name, "Test Ward CRE01")
		self.assertEqual(ward.is_active, 1)

	def test_autoname_format(self):
		"""Name follows {company_abbr}-{WARD_CODE} pattern."""
		company = _get_or_create_company(abbr="TST", name="Test Hospital Pvt Ltd")
		ward = _make_ward(ward_code="ICU01", company=company)
		self.assertEqual(ward.name, "TST-ICU01")

	def test_ward_code_uppercased(self):
		"""ward_code is normalised to uppercase on save."""
		ward = _make_ward(ward_code="gen02")
		self.assertEqual(ward.ward_code, "GEN02")

	def test_ward_code_unique_per_company(self):
		"""Duplicate ward_code within the same company raises ValidationError."""
		company = _get_or_create_company()
		_make_ward(ward_code="DUP01", company=company)
		with self.assertRaises(frappe.ValidationError):
			_make_ward(ward_code="DUP01", company=company)

	def test_ward_code_same_code_different_company(self):
		"""Same ward_code in different companies is allowed."""
		co1 = _get_or_create_company(abbr="TST", name="Test Hospital Pvt Ltd")
		co2 = _get_or_create_second_company(abbr="TS2", name="Second Hospital Pvt Ltd")
		w1 = _make_ward(ward_code="SHARED01", company=co1)
		w2 = _make_ward(ward_code="SHARED01", company=co2)
		self.assertNotEqual(w1.name, w2.name)

	def test_ward_code_format_validation_rejects_spaces(self):
		"""Ward codes with spaces are rejected."""
		with self.assertRaises(frappe.ValidationError):
			_make_ward(ward_code="GW 01")

	def test_ward_code_format_validation_rejects_special_chars(self):
		"""Ward codes with special characters are rejected."""
		with self.assertRaises(frappe.ValidationError):
			_make_ward(ward_code="GW@01")

	def test_ward_code_allows_hyphens(self):
		"""Hyphens are valid in ward codes."""
		ward = _make_ward(ward_code="ICU-A1")
		self.assertEqual(ward.ward_code, "ICU-A1")

	def test_auto_critical_care_flag_icu(self):
		"""ICU classification auto-sets is_critical_care=1."""
		ward = _make_ward(ward_code="CC01", ward_classification="ICU")
		self.assertEqual(ward.is_critical_care, 1)

	def test_auto_critical_care_flag_micu(self):
		"""MICU classification auto-sets is_critical_care=1."""
		ward = _make_ward(ward_code="CC02", ward_classification="MICU")
		self.assertEqual(ward.is_critical_care, 1)

	def test_auto_critical_care_flag_hdu(self):
		"""HDU classification auto-sets is_critical_care=1."""
		ward = _make_ward(ward_code="CC03", ward_classification="HDU")
		self.assertEqual(ward.is_critical_care, 1)

	def test_auto_critical_care_flag_general(self):
		"""General classification sets is_critical_care=0."""
		ward = _make_ward(ward_code="CC04", ward_classification="General")
		self.assertEqual(ward.is_critical_care, 0)

	def test_auto_critical_care_flag_private(self):
		"""Private classification sets is_critical_care=0."""
		ward = _make_ward(ward_code="CC05", ward_classification="Private")
		self.assertEqual(ward.is_critical_care, 0)

	def test_available_beds_computed(self):
		"""available_beds = total_beds - occupied_beds."""
		ward = _make_ward(ward_code="CAP01", total_beds=10, occupied_beds=3)
		self.assertEqual(ward.available_beds, 7)

	def test_available_beds_zero_when_full(self):
		"""available_beds is zero when ward is at capacity."""
		ward = _make_ward(ward_code="CAP02", total_beds=5, occupied_beds=5)
		self.assertEqual(ward.available_beds, 0)

	def test_available_beds_defaults_to_zero(self):
		"""When no bed counts are set, available_beds defaults to 0."""
		ward = _make_ward(ward_code="CAP03")
		self.assertEqual(ward.available_beds, 0)

	def test_deactivation_allowed_when_no_beds(self):
		"""Ward with no linked beds can be deactivated."""
		ward = _make_ward(ward_code="DEACT01")
		ward.is_active = 0
		ward.save()
		self.assertEqual(ward.is_active, 0)

	def test_hsu_must_be_group(self):
		"""Linking a non-group Healthcare Service Unit raises ValidationError."""
		if not frappe.db.exists("Healthcare Service Unit Type", "Test Ward Type"):
			frappe.get_doc(
				{
					"doctype": "Healthcare Service Unit Type",
					"healthcare_service_unit_type": "Test Ward Type",
					"inpatient_occupancy": 1,
				}
			).insert(ignore_if_duplicate=True)

		if not frappe.db.exists("Healthcare Service Unit", "Test Non-Group HSU"):
			company = _get_or_create_company()
			frappe.get_doc(
				{
					"doctype": "Healthcare Service Unit",
					"healthcare_service_unit_name": "Test Non-Group HSU",
					"is_group": 0,
					"company": company,
					"healthcare_service_unit_type": "Test Ward Type",
				}
			).insert(ignore_if_duplicate=True)

		hsu = frappe.db.get_value(
			"Healthcare Service Unit",
			{"healthcare_service_unit_name": "Test Non-Group HSU"},
			"name",
		)
		with self.assertRaises(frappe.ValidationError):
			_make_ward(ward_code="HSUT01", healthcare_service_unit=hsu)

	def test_company_abbreviation_required(self):
		"""Company without abbreviation raises error on autoname."""
		co_name = "No Abbr Hospital"
		if frappe.db.exists("Company", co_name):
			frappe.delete_doc("Company", co_name, force=True)

		with self.assertRaises(Exception):
			_make_ward(ward_code="NOABBR01", company=co_name)
