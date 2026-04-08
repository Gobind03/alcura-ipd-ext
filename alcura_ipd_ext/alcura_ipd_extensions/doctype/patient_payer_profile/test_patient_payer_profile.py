"""Co-located unit tests for Patient Payer Profile.

These tests focus on the DocType controller's validate() logic in isolation.
For integration tests, see alcura_ipd_ext/tests/test_patient_payer_profile.py.
"""

from __future__ import annotations

import frappe
import pytest
from frappe.utils import add_days, today


def _make_patient(**kwargs):
	doc = frappe.new_doc("Patient")
	doc.first_name = kwargs.pop("first_name", "Unit")
	doc.last_name = kwargs.pop("last_name", "Test")
	doc.sex = kwargs.pop("sex", "Male")
	doc.update(kwargs)
	doc.insert(ignore_permissions=True)
	return doc


def _build_profile(patient, **kwargs):
	"""Build (but don't insert) a Patient Payer Profile."""
	doc = frappe.new_doc("Patient Payer Profile")
	doc.patient = patient.name
	doc.payer_type = kwargs.pop("payer_type", "Cash")
	doc.valid_from = kwargs.pop("valid_from", today())
	doc.company = kwargs.pop("company", frappe.defaults.get_global_default("company") or "_Test Company")
	doc.update(kwargs)
	return doc


class TestValidateDateRange:
	def test_valid_range_passes(self, admin_session):
		patient = _make_patient(first_name="DR1")
		doc = _build_profile(patient, valid_from=today(), valid_to=add_days(today(), 30))
		doc.insert(ignore_permissions=True)
		assert doc.name

	def test_reversed_range_fails(self, admin_session):
		patient = _make_patient(first_name="DR2")
		doc = _build_profile(
			patient,
			valid_from=add_days(today(), 30),
			valid_to=today(),
		)
		with pytest.raises(frappe.ValidationError, match="cannot be after"):
			doc.insert(ignore_permissions=True)

	def test_same_date_passes(self, admin_session):
		patient = _make_patient(first_name="DR3")
		doc = _build_profile(patient, valid_from=today(), valid_to=today())
		doc.insert(ignore_permissions=True)
		assert doc.name


class TestPayerTypeMandatory:
	def test_corporate_needs_customer(self, admin_session):
		patient = _make_patient(first_name="CM1")
		doc = _build_profile(patient, payer_type="Corporate")
		with pytest.raises(frappe.ValidationError, match="Payer.*is required"):
			doc.insert(ignore_permissions=True)

	def test_psu_needs_customer(self, admin_session):
		patient = _make_patient(first_name="PM1")
		doc = _build_profile(patient, payer_type="PSU")
		with pytest.raises(frappe.ValidationError, match="Payer.*is required"):
			doc.insert(ignore_permissions=True)

	def test_insurance_tpa_needs_payor(self, admin_session):
		patient = _make_patient(first_name="TP1")
		doc = _build_profile(patient, payer_type="Insurance TPA")
		with pytest.raises(frappe.ValidationError, match="Insurance Payor is required"):
			doc.insert(ignore_permissions=True)

	def test_cash_no_mandatory_payer(self, admin_session):
		patient = _make_patient(first_name="CS1")
		doc = _build_profile(patient, payer_type="Cash")
		doc.insert(ignore_permissions=True)
		assert doc.payer_type == "Cash"

	def test_government_scheme_no_mandatory_customer(self, admin_session):
		patient = _make_patient(first_name="GS1")
		doc = _build_profile(patient, payer_type="Government Scheme", scheme_name="CGHS")
		doc.insert(ignore_permissions=True)
		assert doc.payer_type == "Government Scheme"


class TestFetchBehavior:
	def test_patient_name_fetched(self, admin_session):
		patient = _make_patient(first_name="Fetch", last_name="Name")
		doc = _build_profile(patient)
		doc.insert(ignore_permissions=True)
		doc.reload()
		assert doc.patient_name == "Fetch Name"
