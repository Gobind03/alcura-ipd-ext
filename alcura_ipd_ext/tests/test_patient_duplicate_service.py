"""Integration tests for patient duplicate detection service.

Requires a running Frappe test site with the Healthcare app installed so
that the Patient doctype is available.
"""

import frappe
import pytest

from alcura_ipd_ext.services.patient_duplicate_service import check_duplicates


def _make_patient(first_name="Test", last_name="Patient", **kwargs):
	"""Create a Patient doc with sensible defaults."""
	doc = frappe.get_doc(
		{
			"doctype": "Patient",
			"first_name": first_name,
			"last_name": last_name,
			"sex": kwargs.pop("sex", "Male"),
			**kwargs,
		}
	)
	doc.insert(ignore_permissions=True)
	return doc


class TestDuplicateByMobile:
	def test_exact_mobile_match(self, admin_session):
		p1 = _make_patient(first_name="Aarav", mobile="9876543210")
		matches = check_duplicates(mobile="9876543210", exclude_patient=None)
		assert any(m["patient"] == p1.name for m in matches)
		assert "mobile" in matches[0]["match_reasons"]

	def test_no_match_different_mobile(self, admin_session):
		_make_patient(first_name="Aarav", mobile="9876543210")
		matches = check_duplicates(mobile="9000000001")
		assert len(matches) == 0

	def test_exclude_self(self, admin_session):
		p1 = _make_patient(first_name="Aarav", mobile="9876543210")
		matches = check_duplicates(mobile="9876543210", exclude_patient=p1.name)
		assert not any(m["patient"] == p1.name for m in matches)


class TestDuplicateByAadhaar:
	def test_exact_aadhaar_match(self, admin_session):
		p1 = _make_patient(
			first_name="Bharat",
			custom_aadhaar_number="499118665246",
		)
		matches = check_duplicates(aadhaar="499118665246")
		assert any(m["patient"] == p1.name for m in matches)
		assert "Aadhaar" in matches[0]["match_reasons"]

	def test_aadhaar_with_whitespace_normalised(self, admin_session):
		p1 = _make_patient(
			first_name="Bharat",
			custom_aadhaar_number="499118665246",
		)
		matches = check_duplicates(aadhaar="4991 1866 5246")
		assert any(m["patient"] == p1.name for m in matches)


class TestDuplicateByAbha:
	def test_exact_abha_match(self, admin_session):
		p1 = _make_patient(
			first_name="Chandra",
			custom_abha_number="12345678901234",
		)
		matches = check_duplicates(abha="12345678901234")
		assert any(m["patient"] == p1.name for m in matches)
		assert "ABHA Number" in matches[0]["match_reasons"]


class TestDuplicateByMrNumber:
	def test_exact_mr_match(self, admin_session):
		p1 = _make_patient(
			first_name="Deepak",
			custom_mr_number="MR-2025-00001",
		)
		matches = check_duplicates(mr_number="MR-2025-00001")
		assert any(m["patient"] == p1.name for m in matches)
		assert "MR Number" in matches[0]["match_reasons"]


class TestFuzzyNameDob:
	def test_same_dob_similar_name(self, admin_session):
		_make_patient(first_name="Rajesh", dob="1990-05-15")
		matches = check_duplicates(first_name="Rajesh", dob="1990-05-15")
		assert len(matches) > 0
		assert any("Similar Name" in r for r in matches[0]["match_reasons"])

	def test_same_dob_different_name(self, admin_session):
		_make_patient(first_name="Rajesh", dob="1990-05-15")
		matches = check_duplicates(first_name="Zzzzz", dob="1990-05-15")
		assert len(matches) == 0

	def test_different_dob_same_name(self, admin_session):
		_make_patient(first_name="Rajesh", dob="1990-05-15")
		matches = check_duplicates(first_name="Rajesh", dob="2000-01-01")
		assert len(matches) == 0


class TestMultipleMatchReasons:
	def test_mobile_and_aadhaar_same_patient(self, admin_session):
		p1 = _make_patient(
			first_name="Esha",
			mobile="8765432109",
			custom_aadhaar_number="499118665246",
		)
		matches = check_duplicates(mobile="8765432109", aadhaar="499118665246")
		match = next(m for m in matches if m["patient"] == p1.name)
		assert len(match["match_reasons"]) >= 2

	def test_results_sorted_by_match_count(self, admin_session):
		_make_patient(first_name="Aarav", mobile="9876543210")
		_make_patient(
			first_name="Bharat",
			mobile="9876543210",
			custom_aadhaar_number="499118665246",
		)
		matches = check_duplicates(mobile="9876543210", aadhaar="499118665246")
		if len(matches) >= 2:
			assert len(matches[0]["match_reasons"]) >= len(matches[1]["match_reasons"])


class TestNoFalsePositives:
	def test_completely_distinct_patients(self, admin_session):
		_make_patient(first_name="Farhan", mobile="9111111111", dob="1985-01-01")
		matches = check_duplicates(
			mobile="9222222222",
			first_name="Gita",
			dob="1995-12-31",
		)
		assert len(matches) == 0

	def test_empty_inputs_returns_empty(self, admin_session):
		matches = check_duplicates()
		assert matches == []
