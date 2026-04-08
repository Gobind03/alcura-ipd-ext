"""Integration tests for Patient registration with custom fields.

Verifies that custom fields exist, server-side validation hooks fire,
consent auto-timestamp works, and MR uniqueness is enforced.
"""

import frappe
import pytest

from alcura_ipd_ext.setup.custom_fields import get_custom_fields


def _make_patient(first_name="Test", last_name="Registration", **kwargs):
	doc = frappe.get_doc(
		{
			"doctype": "Patient",
			"first_name": first_name,
			"last_name": last_name,
			"sex": kwargs.pop("sex", "Female"),
			**kwargs,
		}
	)
	doc.insert(ignore_permissions=True)
	return doc


# ---------------------------------------------------------------------------
# Custom field presence
# ---------------------------------------------------------------------------

class TestCustomFieldDefinitions:
	"""Verify that Patient custom fields are defined in the registry."""

	def test_patient_key_exists(self):
		fields = get_custom_fields()
		assert "Patient" in fields

	def test_aadhaar_field_defined(self):
		fields = get_custom_fields()["Patient"]
		names = [f["fieldname"] for f in fields]
		assert "custom_aadhaar_number" in names

	def test_abha_number_field_defined(self):
		fields = get_custom_fields()["Patient"]
		names = [f["fieldname"] for f in fields]
		assert "custom_abha_number" in names

	def test_pan_field_defined(self):
		fields = get_custom_fields()["Patient"]
		names = [f["fieldname"] for f in fields]
		assert "custom_pan_number" in names

	def test_mr_number_field_defined(self):
		fields = get_custom_fields()["Patient"]
		names = [f["fieldname"] for f in fields]
		assert "custom_mr_number" in names

	def test_emergency_contact_fields_defined(self):
		fields = get_custom_fields()["Patient"]
		names = [f["fieldname"] for f in fields]
		assert "custom_emergency_contact_name" in names
		assert "custom_emergency_contact_phone" in names
		assert "custom_emergency_contact_relation" in names

	def test_consent_fields_defined(self):
		fields = get_custom_fields()["Patient"]
		names = [f["fieldname"] for f in fields]
		assert "custom_consent_collected" in names
		assert "custom_consent_datetime" in names
		assert "custom_consent_given_by" in names
		assert "custom_privacy_notice_acknowledged" in names

	def test_mr_number_has_unique_flag(self):
		fields = get_custom_fields()["Patient"]
		mr = next(f for f in fields if f["fieldname"] == "custom_mr_number")
		assert mr.get("unique") == 1

	def test_aadhaar_has_search_index(self):
		fields = get_custom_fields()["Patient"]
		aadhaar = next(f for f in fields if f["fieldname"] == "custom_aadhaar_number")
		assert aadhaar.get("search_index") == 1


# ---------------------------------------------------------------------------
# Aadhaar validation on save
# ---------------------------------------------------------------------------

class TestAadhaarValidationOnSave:
	def test_valid_aadhaar_saves(self, admin_session):
		doc = _make_patient(custom_aadhaar_number="499118665246")
		assert doc.name

	def test_invalid_aadhaar_rejects(self, admin_session):
		with pytest.raises(frappe.ValidationError):
			_make_patient(custom_aadhaar_number="123456789012")

	def test_no_aadhaar_saves(self, admin_session):
		doc = _make_patient()
		assert doc.name


# ---------------------------------------------------------------------------
# PAN validation on save
# ---------------------------------------------------------------------------

class TestPanValidationOnSave:
	def test_valid_pan_saves(self, admin_session):
		doc = _make_patient(custom_pan_number="ABCDE1234F")
		assert doc.name

	def test_pan_normalised_to_uppercase(self, admin_session):
		doc = _make_patient(custom_pan_number="abcde1234f")
		assert doc.custom_pan_number == "ABCDE1234F"

	def test_invalid_pan_rejects(self, admin_session):
		with pytest.raises(frappe.ValidationError):
			_make_patient(custom_pan_number="INVALID")


# ---------------------------------------------------------------------------
# ABHA validation on save
# ---------------------------------------------------------------------------

class TestAbhaValidationOnSave:
	def test_valid_abha_saves(self, admin_session):
		doc = _make_patient(custom_abha_number="12345678901234")
		assert doc.name

	def test_invalid_abha_rejects(self, admin_session):
		with pytest.raises(frappe.ValidationError):
			_make_patient(custom_abha_number="12345")


# ---------------------------------------------------------------------------
# Emergency contact phone validation
# ---------------------------------------------------------------------------

class TestEmergencyPhoneValidation:
	def test_valid_emergency_phone(self, admin_session):
		doc = _make_patient(custom_emergency_contact_phone="9876543210")
		assert doc.name

	def test_invalid_emergency_phone_rejects(self, admin_session):
		with pytest.raises(frappe.ValidationError):
			_make_patient(custom_emergency_contact_phone="12345")


# ---------------------------------------------------------------------------
# Consent auto-timestamp
# ---------------------------------------------------------------------------

class TestConsentTimestamp:
	def test_consent_datetime_auto_set(self, admin_session):
		doc = _make_patient(custom_consent_collected=1)
		assert doc.custom_consent_datetime is not None

	def test_consent_datetime_cleared_when_unchecked(self, admin_session):
		doc = _make_patient(custom_consent_collected=1)
		assert doc.custom_consent_datetime
		doc.custom_consent_collected = 0
		doc.save(ignore_permissions=True)
		assert doc.custom_consent_datetime is None

	def test_consent_datetime_preserved_on_re_save(self, admin_session):
		doc = _make_patient(custom_consent_collected=1)
		first_ts = doc.custom_consent_datetime
		doc.save(ignore_permissions=True)
		assert doc.custom_consent_datetime == first_ts


# ---------------------------------------------------------------------------
# MR number uniqueness
# ---------------------------------------------------------------------------

class TestMrNumberUniqueness:
	def test_unique_mr_saves(self, admin_session):
		doc = _make_patient(custom_mr_number="MR-2025-00001")
		assert doc.name

	def test_duplicate_mr_rejects(self, admin_session):
		_make_patient(first_name="Alpha", custom_mr_number="MR-2025-00002")
		with pytest.raises(frappe.ValidationError, match="Duplicate MR Number"):
			_make_patient(first_name="Beta", custom_mr_number="MR-2025-00002")

	def test_same_patient_can_keep_mr(self, admin_session):
		doc = _make_patient(custom_mr_number="MR-2025-00003")
		doc.first_name = "Updated"
		doc.save(ignore_permissions=True)
		assert doc.custom_mr_number == "MR-2025-00003"
