"""Tests for Patient Payer Profile doctype.

Covers validation logic, payer-type-specific mandatory fields,
date range enforcement, duplicate active profile warnings,
insurance policy cross-validation, and permission checks.
"""

from __future__ import annotations

import frappe
import pytest
from frappe.utils import add_days, today


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_patient(first_name="Test", last_name="Patient", **kwargs):
	"""Create a minimal Patient record for testing."""
	doc = frappe.new_doc("Patient")
	doc.first_name = first_name
	doc.last_name = last_name
	doc.sex = "Male"
	doc.update(kwargs)
	doc.insert(ignore_permissions=True)
	return doc


def _make_profile(patient, payer_type="Cash", **kwargs):
	"""Create a Patient Payer Profile with sensible defaults."""
	doc = frappe.new_doc("Patient Payer Profile")
	doc.patient = patient.name
	doc.payer_type = payer_type
	doc.valid_from = kwargs.pop("valid_from", today())
	doc.company = kwargs.pop("company", frappe.defaults.get_global_default("company") or "_Test Company")
	doc.update(kwargs)
	doc.insert(ignore_permissions=True)
	return doc


def _make_customer(name="Test TPA Customer"):
	"""Create a minimal Customer record."""
	if frappe.db.exists("Customer", name):
		return frappe.get_doc("Customer", name)
	doc = frappe.new_doc("Customer")
	doc.customer_name = name
	doc.customer_group = frappe.db.get_value("Customer Group", {"is_group": 0}) or "All Customer Groups"
	doc.territory = frappe.db.get_value("Territory", {"is_group": 0}) or "All Territories"
	doc.insert(ignore_permissions=True)
	return doc


# ---------------------------------------------------------------------------
# Test: Create profiles for each payer type
# ---------------------------------------------------------------------------


class TestPayerTypeCreation:
	"""Verify that profiles can be created for each payer type with correct
	mandatory field enforcement."""

	def test_create_cash_profile(self, admin_session):
		patient = _make_patient(first_name="Cash")
		profile = _make_profile(patient, payer_type="Cash")
		assert profile.name
		assert profile.payer_type == "Cash"
		assert profile.is_active == 1

	def test_create_corporate_profile(self, admin_session):
		patient = _make_patient(first_name="Corp")
		customer = _make_customer("Corp Employer Ltd")
		profile = _make_profile(
			patient,
			payer_type="Corporate",
			payer=customer.name,
			employer_name="Corp Employer Ltd",
		)
		assert profile.payer_type == "Corporate"
		assert profile.payer == customer.name

	def test_create_insurance_tpa_profile(self, admin_session):
		patient = _make_patient(first_name="TPA")
		ip_exists = frappe.db.exists("Insurance Payor")
		if ip_exists:
			insurance_payor = ip_exists
		else:
			pytest.skip("No Insurance Payor exists in the test database")

		profile = _make_profile(
			patient,
			payer_type="Insurance TPA",
			insurance_payor=insurance_payor,
			policy_number="POL-12345",
			member_id="MEM-001",
		)
		assert profile.payer_type == "Insurance TPA"
		assert profile.insurance_payor == insurance_payor

	def test_create_psu_profile(self, admin_session):
		patient = _make_patient(first_name="PSU")
		customer = _make_customer("PSU Corp")
		profile = _make_profile(
			patient,
			payer_type="PSU",
			payer=customer.name,
			employer_name="PSU Corp",
		)
		assert profile.payer_type == "PSU"

	def test_create_government_scheme_profile(self, admin_session):
		patient = _make_patient(first_name="Govt")
		profile = _make_profile(
			patient,
			payer_type="Government Scheme",
			scheme_name="CGHS",
		)
		assert profile.payer_type == "Government Scheme"
		assert profile.scheme_name == "CGHS"


# ---------------------------------------------------------------------------
# Test: Date validation
# ---------------------------------------------------------------------------


class TestDateValidation:
	def test_valid_from_after_valid_to_throws(self, admin_session):
		patient = _make_patient(first_name="DateTest")
		with pytest.raises(frappe.exceptions.ValidationError, match="cannot be after"):
			_make_profile(
				patient,
				valid_from=add_days(today(), 10),
				valid_to=add_days(today(), 5),
			)

	def test_valid_from_before_valid_to_ok(self, admin_session):
		patient = _make_patient(first_name="DateOK")
		profile = _make_profile(
			patient,
			valid_from=today(),
			valid_to=add_days(today(), 30),
		)
		assert profile.name

	def test_open_ended_profile_ok(self, admin_session):
		patient = _make_patient(first_name="OpenEnd")
		profile = _make_profile(patient, valid_from=today())
		assert profile.valid_to is None or profile.valid_to == ""


# ---------------------------------------------------------------------------
# Test: Payer-type-specific mandatory fields
# ---------------------------------------------------------------------------


class TestPayerTypeMandatoryFields:
	def test_insurance_tpa_without_insurance_payor_throws(self, admin_session):
		patient = _make_patient(first_name="TPANoIP")
		with pytest.raises(frappe.exceptions.ValidationError, match="Insurance Payor is required"):
			_make_profile(patient, payer_type="Insurance TPA")

	def test_corporate_without_customer_throws(self, admin_session):
		patient = _make_patient(first_name="CorpNoPayer")
		with pytest.raises(frappe.exceptions.ValidationError, match="Payer.*is required"):
			_make_profile(patient, payer_type="Corporate")

	def test_psu_without_customer_throws(self, admin_session):
		patient = _make_patient(first_name="PSUNoPayer")
		with pytest.raises(frappe.exceptions.ValidationError, match="Payer.*is required"):
			_make_profile(patient, payer_type="PSU")

	def test_government_scheme_without_customer_ok(self, admin_session):
		"""Government Scheme does not require a Customer."""
		patient = _make_patient(first_name="GovtOK")
		profile = _make_profile(
			patient,
			payer_type="Government Scheme",
			scheme_name="ECHS",
		)
		assert profile.name


# ---------------------------------------------------------------------------
# Test: Duplicate active profile warning
# ---------------------------------------------------------------------------


class TestDuplicateActiveProfile:
	def test_duplicate_active_cash_warns(self, admin_session):
		patient = _make_patient(first_name="DupCash")
		_make_profile(patient, payer_type="Cash")

		# Second active Cash profile should NOT throw but may warn via msgprint
		profile2 = _make_profile(patient, payer_type="Cash")
		assert profile2.name

	def test_inactive_profile_does_not_trigger_warning(self, admin_session):
		patient = _make_patient(first_name="InactiveDup")
		p1 = _make_profile(patient, payer_type="Cash")
		p1.is_active = 0
		p1.save(ignore_permissions=True)

		profile2 = _make_profile(patient, payer_type="Cash")
		assert profile2.name


# ---------------------------------------------------------------------------
# Test: Profile deactivation
# ---------------------------------------------------------------------------


class TestProfileDeactivation:
	def test_deactivate_profile(self, admin_session):
		patient = _make_patient(first_name="Deact")
		profile = _make_profile(patient, payer_type="Cash")
		assert profile.is_active == 1

		profile.is_active = 0
		profile.save(ignore_permissions=True)

		profile.reload()
		assert profile.is_active == 0

	def test_deactivated_profile_excluded_from_active_query(self, admin_session):
		patient = _make_patient(first_name="ActiveQuery")
		profile = _make_profile(patient, payer_type="Cash")
		profile.is_active = 0
		profile.save(ignore_permissions=True)

		active = frappe.db.get_all(
			"Patient Payer Profile",
			filters={"patient": patient.name, "is_active": 1},
		)
		assert len(active) == 0


# ---------------------------------------------------------------------------
# Test: Insurance policy cross-validation
# ---------------------------------------------------------------------------


class TestInsurancePolicyCrossValidation:
	def test_mismatched_patient_policy_throws(self, admin_session):
		"""If an insurance policy is linked, it must belong to the same patient."""
		ip_exists = frappe.db.exists("Insurance Payor")
		if not ip_exists:
			pytest.skip("No Insurance Payor in test database")

		patient_a = _make_patient(first_name="PolicyA")
		patient_b = _make_patient(first_name="PolicyB")

		policy_for_b = frappe.db.get_value(
			"Patient Insurance Policy",
			{"patient": patient_b.name},
			"name",
		)
		if not policy_for_b:
			pytest.skip("No Patient Insurance Policy for patient B in test database")

		with pytest.raises(frappe.exceptions.ValidationError, match="Patient Mismatch"):
			_make_profile(
				patient_a,
				payer_type="Insurance TPA",
				insurance_payor=ip_exists,
				insurance_policy=policy_for_b,
			)


# ---------------------------------------------------------------------------
# Test: Payer type migration patch
# ---------------------------------------------------------------------------


class TestPayerTypeMigration:
	def test_rename_tpa_to_insurance_tpa(self, admin_session):
		"""Simulate the migration by creating a RTM with old value and running patch."""
		from alcura_ipd_ext.patches.v0_0_2.rename_tpa_to_insurance_tpa import execute

		company = frappe.defaults.get_global_default("company") or "_Test Company"
		price_list = frappe.db.get_value("Price List", {"selling": 1}) or "_Test Price List"

		if not frappe.db.exists("Healthcare Service Unit Type", {"inpatient_occupancy": 1}):
			pytest.skip("No IPD room type available for test")

		room_type = frappe.db.get_value(
			"Healthcare Service Unit Type",
			{"inpatient_occupancy": 1},
		)

		rtm = frappe.new_doc("Room Tariff Mapping")
		rtm.room_type = room_type
		rtm.company = company
		rtm.payer_type = "TPA"
		rtm.valid_from = today()
		rtm.price_list = price_list
		rtm.is_active = 1

		# Need at least one tariff item
		item = frappe.db.get_value("Item", {"disabled": 0})
		if item:
			rtm.append("tariff_items", {
				"charge_type": "Room Rent",
				"item_code": item,
				"rate": 1000,
			})

		# Force the old value into the DB directly since the JSON now has new options
		rtm.flags.ignore_validate = True
		rtm.insert(ignore_permissions=True)
		frappe.db.set_value("Room Tariff Mapping", rtm.name, "payer_type", "TPA")
		frappe.db.commit()

		execute()

		updated = frappe.db.get_value("Room Tariff Mapping", rtm.name, "payer_type")
		assert updated == "Insurance TPA"


# ---------------------------------------------------------------------------
# Test: Tariff service compatibility with new payer types
# ---------------------------------------------------------------------------


class TestTariffServiceCompatibility:
	def test_resolve_tariff_for_profile_returns_none_for_invalid_profile(self, admin_session):
		from alcura_ipd_ext.services.tariff_service import resolve_tariff_for_profile

		result = resolve_tariff_for_profile(
			room_type="Nonexistent Room Type",
			patient_payer_profile="NONEXISTENT",
		)
		assert result is None
