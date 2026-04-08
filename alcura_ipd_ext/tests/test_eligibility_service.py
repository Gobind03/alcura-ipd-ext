"""Tests for Payer Eligibility Check and eligibility service.

Covers:
- DocType creation and defaults
- Status transition validation
- Audit field population
- Eligibility service queries
- Admission eligibility check with policy enforcement levels
- Date validation
- Patient-payer profile cross-validation
"""

from __future__ import annotations

import frappe
import pytest
from frappe.utils import add_days, now_datetime, today


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_patient(first_name="EligTest", last_name="Patient", **kwargs):
	doc = frappe.new_doc("Patient")
	doc.first_name = first_name
	doc.last_name = last_name
	doc.sex = kwargs.pop("sex", "Male")
	doc.update(kwargs)
	doc.insert(ignore_permissions=True)
	return doc


def _make_payer_profile(patient, payer_type="Insurance TPA", **kwargs):
	doc = frappe.new_doc("Patient Payer Profile")
	doc.patient = patient.name
	doc.payer_type = payer_type
	doc.valid_from = kwargs.pop("valid_from", today())
	doc.company = kwargs.pop(
		"company",
		frappe.defaults.get_global_default("company") or "_Test Company",
	)
	if payer_type == "Insurance TPA":
		ip = frappe.db.exists("Insurance Payor")
		if ip:
			doc.insurance_payor = kwargs.pop("insurance_payor", ip)
		else:
			pytest.skip("No Insurance Payor in test database")
	elif payer_type in ("Corporate", "PSU"):
		doc.payer = kwargs.pop("payer", _make_customer().name)
	doc.update(kwargs)
	doc.insert(ignore_permissions=True)
	return doc


def _make_customer(name="Elig Test Customer"):
	if frappe.db.exists("Customer", name):
		return frappe.get_doc("Customer", name)
	doc = frappe.new_doc("Customer")
	doc.customer_name = name
	doc.customer_group = (
		frappe.db.get_value("Customer Group", {"is_group": 0})
		or "All Customer Groups"
	)
	doc.territory = (
		frappe.db.get_value("Territory", {"is_group": 0}) or "All Territories"
	)
	doc.insert(ignore_permissions=True)
	return doc


def _make_eligibility_check(patient, profile, **kwargs):
	doc = frappe.new_doc("Payer Eligibility Check")
	doc.patient = patient.name
	doc.patient_payer_profile = profile.name
	doc.company = kwargs.pop(
		"company",
		frappe.defaults.get_global_default("company") or "_Test Company",
	)
	doc.verification_status = kwargs.pop("verification_status", "Pending")
	doc.update(kwargs)
	doc.insert(ignore_permissions=True)
	return doc


def _set_policy_field(fieldname, value):
	"""Set a field on the IPD Bed Policy single doc."""
	try:
		doc = frappe.get_doc("IPD Bed Policy")
	except frappe.DoesNotExistError:
		doc = frappe.new_doc("IPD Bed Policy")
		doc.insert(ignore_permissions=True)

	doc.set(fieldname, value)
	doc.save(ignore_permissions=True)
	frappe.clear_cache(doctype="IPD Bed Policy")


# ---------------------------------------------------------------------------
# Test: Creation and defaults
# ---------------------------------------------------------------------------


class TestPayerEligibilityCheckCreation:
	def test_create_pending_check(self, admin_session):
		patient = _make_patient(first_name="CreatePending")
		profile = _make_payer_profile(patient)
		check = _make_eligibility_check(patient, profile)
		assert check.name
		assert check.verification_status == "Pending"
		assert check.submitted_by == "Administrator"
		assert check.submitted_on is not None

	def test_create_check_with_inpatient_record(self, admin_session):
		patient = _make_patient(first_name="CreateIR")
		profile = _make_payer_profile(patient)
		check = _make_eligibility_check(
			patient, profile, inpatient_record=None
		)
		assert check.name
		assert not check.inpatient_record

	def test_payer_type_fetched_from_profile(self, admin_session):
		patient = _make_patient(first_name="FetchType")
		profile = _make_payer_profile(patient, payer_type="Cash")
		check = _make_eligibility_check(patient, profile)
		check.reload()
		assert check.payer_type == "Cash"


# ---------------------------------------------------------------------------
# Test: Status transitions
# ---------------------------------------------------------------------------


class TestStatusTransitions:
	def test_pending_to_verified(self, admin_session):
		patient = _make_patient(first_name="PendToVer")
		profile = _make_payer_profile(patient)
		check = _make_eligibility_check(patient, profile)

		check.verification_status = "Verified"
		check.reference_number = "PRE-001"
		check.save(ignore_permissions=True)
		check.reload()
		assert check.verification_status == "Verified"
		assert check.verified_by == "Administrator"
		assert check.verification_datetime is not None

	def test_pending_to_conditional(self, admin_session):
		patient = _make_patient(first_name="PendToCond")
		profile = _make_payer_profile(patient)
		check = _make_eligibility_check(patient, profile)

		check.verification_status = "Conditional"
		check.save(ignore_permissions=True)
		assert check.verification_status == "Conditional"

	def test_pending_to_rejected(self, admin_session):
		patient = _make_patient(first_name="PendToRej")
		profile = _make_payer_profile(patient)
		check = _make_eligibility_check(patient, profile)

		check.verification_status = "Rejected"
		check.save(ignore_permissions=True)
		assert check.verification_status == "Rejected"

	def test_verified_to_expired(self, admin_session):
		patient = _make_patient(first_name="VerToExp")
		profile = _make_payer_profile(patient)
		check = _make_eligibility_check(patient, profile)

		check.verification_status = "Verified"
		check.save(ignore_permissions=True)

		check.verification_status = "Expired"
		check.save(ignore_permissions=True)
		assert check.verification_status == "Expired"

	def test_rejected_to_pending(self, admin_session):
		patient = _make_patient(first_name="RejToPend")
		profile = _make_payer_profile(patient)
		check = _make_eligibility_check(patient, profile)

		check.verification_status = "Rejected"
		check.save(ignore_permissions=True)

		check.verification_status = "Pending"
		check.save(ignore_permissions=True)
		assert check.verification_status == "Pending"

	def test_expired_to_pending(self, admin_session):
		patient = _make_patient(first_name="ExpToPend")
		profile = _make_payer_profile(patient)
		check = _make_eligibility_check(patient, profile)

		check.verification_status = "Verified"
		check.save(ignore_permissions=True)
		check.verification_status = "Expired"
		check.save(ignore_permissions=True)

		check.verification_status = "Pending"
		check.save(ignore_permissions=True)
		assert check.verification_status == "Pending"

	def test_invalid_transition_throws(self, admin_session):
		patient = _make_patient(first_name="InvalidTrans")
		profile = _make_payer_profile(patient)
		check = _make_eligibility_check(patient, profile)

		check.verification_status = "Verified"
		check.save(ignore_permissions=True)

		with pytest.raises(
			frappe.exceptions.ValidationError, match="Cannot change status"
		):
			check.verification_status = "Rejected"
			check.save(ignore_permissions=True)

	def test_pending_to_expired_invalid(self, admin_session):
		patient = _make_patient(first_name="PendToExpInv")
		profile = _make_payer_profile(patient)
		check = _make_eligibility_check(patient, profile)

		with pytest.raises(
			frappe.exceptions.ValidationError, match="Cannot change status"
		):
			check.verification_status = "Expired"
			check.save(ignore_permissions=True)


# ---------------------------------------------------------------------------
# Test: Audit fields
# ---------------------------------------------------------------------------


class TestAuditFields:
	def test_submitted_by_set_on_insert(self, admin_session):
		patient = _make_patient(first_name="AuditInsert")
		profile = _make_payer_profile(patient)
		check = _make_eligibility_check(patient, profile)
		assert check.submitted_by == "Administrator"
		assert check.submitted_on is not None

	def test_verified_by_set_on_verification(self, admin_session):
		patient = _make_patient(first_name="AuditVerify")
		profile = _make_payer_profile(patient)
		check = _make_eligibility_check(patient, profile)

		check.verification_status = "Verified"
		check.save(ignore_permissions=True)
		check.reload()
		assert check.verified_by == "Administrator"
		assert check.verification_datetime is not None

	def test_last_status_change_updated(self, admin_session):
		patient = _make_patient(first_name="AuditChange")
		profile = _make_payer_profile(patient)
		check = _make_eligibility_check(patient, profile)

		check.verification_status = "Rejected"
		check.save(ignore_permissions=True)
		check.reload()
		assert check.last_status_change_by == "Administrator"
		assert check.last_status_change_on is not None


# ---------------------------------------------------------------------------
# Test: Eligibility service
# ---------------------------------------------------------------------------


class TestEligibilityService:
	def test_get_latest_returns_verified(self, admin_session):
		from alcura_ipd_ext.services.eligibility_service import (
			get_latest_active_eligibility,
		)

		patient = _make_patient(first_name="SvcVer")
		profile = _make_payer_profile(patient)
		check = _make_eligibility_check(patient, profile)

		check.verification_status = "Verified"
		check.reference_number = "REF-SVC-01"
		check.save(ignore_permissions=True)

		result = get_latest_active_eligibility(
			patient=patient.name, patient_payer_profile=profile.name
		)
		assert result is not None
		assert result["name"] == check.name
		assert result["verification_status"] == "Verified"

	def test_get_latest_returns_conditional(self, admin_session):
		from alcura_ipd_ext.services.eligibility_service import (
			get_latest_active_eligibility,
		)

		patient = _make_patient(first_name="SvcCond")
		profile = _make_payer_profile(patient)
		check = _make_eligibility_check(patient, profile)

		check.verification_status = "Conditional"
		check.save(ignore_permissions=True)

		result = get_latest_active_eligibility(
			patient=patient.name, patient_payer_profile=profile.name
		)
		assert result is not None
		assert result["verification_status"] == "Conditional"

	def test_get_latest_returns_none_for_pending(self, admin_session):
		from alcura_ipd_ext.services.eligibility_service import (
			get_latest_active_eligibility,
		)

		patient = _make_patient(first_name="SvcPending")
		profile = _make_payer_profile(patient)
		_make_eligibility_check(patient, profile)

		result = get_latest_active_eligibility(
			patient=patient.name, patient_payer_profile=profile.name
		)
		assert result is None

	def test_get_latest_returns_none_for_rejected(self, admin_session):
		from alcura_ipd_ext.services.eligibility_service import (
			get_latest_active_eligibility,
		)

		patient = _make_patient(first_name="SvcRej")
		profile = _make_payer_profile(patient)
		check = _make_eligibility_check(patient, profile)

		check.verification_status = "Rejected"
		check.save(ignore_permissions=True)

		result = get_latest_active_eligibility(
			patient=patient.name, patient_payer_profile=profile.name
		)
		assert result is None

	def test_get_latest_ignores_expired_by_date(self, admin_session):
		from alcura_ipd_ext.services.eligibility_service import (
			get_latest_active_eligibility,
		)

		patient = _make_patient(first_name="SvcExpDate")
		profile = _make_payer_profile(patient)
		check = _make_eligibility_check(
			patient,
			profile,
			valid_from=add_days(today(), -30),
			valid_to=add_days(today(), -1),
		)
		check.verification_status = "Verified"
		check.save(ignore_permissions=True)

		result = get_latest_active_eligibility(
			patient=patient.name, patient_payer_profile=profile.name
		)
		assert result is None

	def test_get_latest_returns_none_when_none_exist(self, admin_session):
		from alcura_ipd_ext.services.eligibility_service import (
			get_latest_active_eligibility,
		)

		patient = _make_patient(first_name="SvcNone")
		result = get_latest_active_eligibility(patient=patient.name)
		assert result is None


# ---------------------------------------------------------------------------
# Test: Admission eligibility check
# ---------------------------------------------------------------------------


class TestAdmissionEligibilityCheck:
	def test_ignore_enforcement_always_eligible(self, admin_session):
		from alcura_ipd_ext.services.eligibility_service import (
			check_admission_eligibility,
		)

		_set_policy_field("enforce_eligibility_verification", "Ignore")

		patient = _make_patient(first_name="AdmIgnore")
		profile = _make_payer_profile(patient)

		ir = frappe.new_doc("Inpatient Record")
		ir.patient = patient.name
		ir.company = profile.company
		ir.custom_patient_payer_profile = profile.name
		ir.status = "Admission Scheduled"
		ir.scheduled_date = today()
		ir.flags.ignore_validate = True
		ir.flags.ignore_mandatory = True
		ir.insert(ignore_permissions=True)

		result = check_admission_eligibility(ir.name)
		assert result["eligible"] is True
		assert result["status"] == "Skipped"

	def test_cash_payer_always_eligible(self, admin_session):
		from alcura_ipd_ext.services.eligibility_service import (
			check_admission_eligibility,
		)

		_set_policy_field("enforce_eligibility_verification", "Strict")

		patient = _make_patient(first_name="AdmCash")
		profile = _make_payer_profile(patient, payer_type="Cash")

		ir = frappe.new_doc("Inpatient Record")
		ir.patient = patient.name
		ir.company = profile.company
		ir.custom_patient_payer_profile = profile.name
		ir.status = "Admission Scheduled"
		ir.scheduled_date = today()
		ir.flags.ignore_validate = True
		ir.flags.ignore_mandatory = True
		ir.insert(ignore_permissions=True)

		result = check_admission_eligibility(ir.name)
		assert result["eligible"] is True
		assert result["status"] == "Cash"

	def test_no_profile_treated_as_cash(self, admin_session):
		from alcura_ipd_ext.services.eligibility_service import (
			check_admission_eligibility,
		)

		_set_policy_field("enforce_eligibility_verification", "Strict")

		patient = _make_patient(first_name="AdmNoProfile")

		ir = frappe.new_doc("Inpatient Record")
		ir.patient = patient.name
		ir.company = frappe.defaults.get_global_default("company") or "_Test Company"
		ir.status = "Admission Scheduled"
		ir.scheduled_date = today()
		ir.flags.ignore_validate = True
		ir.flags.ignore_mandatory = True
		ir.insert(ignore_permissions=True)

		result = check_admission_eligibility(ir.name)
		assert result["eligible"] is True
		assert result["status"] == "No Profile"

	def test_strict_blocks_without_eligibility(self, admin_session):
		from alcura_ipd_ext.services.eligibility_service import (
			check_admission_eligibility,
		)

		_set_policy_field("enforce_eligibility_verification", "Strict")

		patient = _make_patient(first_name="AdmStrict")
		profile = _make_payer_profile(patient)

		ir = frappe.new_doc("Inpatient Record")
		ir.patient = patient.name
		ir.company = profile.company
		ir.custom_patient_payer_profile = profile.name
		ir.status = "Admission Scheduled"
		ir.scheduled_date = today()
		ir.flags.ignore_validate = True
		ir.flags.ignore_mandatory = True
		ir.insert(ignore_permissions=True)

		result = check_admission_eligibility(ir.name)
		assert result["eligible"] is False
		assert result["enforcement"] == "Strict"

	def test_advisory_allows_without_eligibility(self, admin_session):
		from alcura_ipd_ext.services.eligibility_service import (
			check_admission_eligibility,
		)

		_set_policy_field("enforce_eligibility_verification", "Advisory")

		patient = _make_patient(first_name="AdmAdvisory")
		profile = _make_payer_profile(patient)

		ir = frappe.new_doc("Inpatient Record")
		ir.patient = patient.name
		ir.company = profile.company
		ir.custom_patient_payer_profile = profile.name
		ir.status = "Admission Scheduled"
		ir.scheduled_date = today()
		ir.flags.ignore_validate = True
		ir.flags.ignore_mandatory = True
		ir.insert(ignore_permissions=True)

		result = check_admission_eligibility(ir.name)
		assert result["eligible"] is True
		assert result["enforcement"] == "Advisory"
		assert result["status"] == "Not Verified"

	def test_verified_eligibility_passes(self, admin_session):
		from alcura_ipd_ext.services.eligibility_service import (
			check_admission_eligibility,
		)

		_set_policy_field("enforce_eligibility_verification", "Strict")

		patient = _make_patient(first_name="AdmVerified")
		profile = _make_payer_profile(patient)
		check = _make_eligibility_check(patient, profile)
		check.verification_status = "Verified"
		check.reference_number = "PRE-ADM-001"
		check.approved_amount = 100000
		check.save(ignore_permissions=True)

		ir = frappe.new_doc("Inpatient Record")
		ir.patient = patient.name
		ir.company = profile.company
		ir.custom_patient_payer_profile = profile.name
		ir.status = "Admission Scheduled"
		ir.scheduled_date = today()
		ir.flags.ignore_validate = True
		ir.flags.ignore_mandatory = True
		ir.insert(ignore_permissions=True)

		result = check_admission_eligibility(ir.name)
		assert result["eligible"] is True
		assert result["status"] == "Verified"
		assert result["eligibility_check"] == check.name


# ---------------------------------------------------------------------------
# Test: Date validation
# ---------------------------------------------------------------------------


class TestDateValidation:
	def test_valid_from_after_valid_to_throws(self, admin_session):
		patient = _make_patient(first_name="DateInvalid")
		profile = _make_payer_profile(patient)

		with pytest.raises(
			frappe.exceptions.ValidationError, match="cannot be after"
		):
			_make_eligibility_check(
				patient,
				profile,
				valid_from=add_days(today(), 10),
				valid_to=add_days(today(), 5),
			)

	def test_valid_range_ok(self, admin_session):
		patient = _make_patient(first_name="DateOK")
		profile = _make_payer_profile(patient)
		check = _make_eligibility_check(
			patient,
			profile,
			valid_from=today(),
			valid_to=add_days(today(), 30),
		)
		assert check.name

	def test_no_dates_ok(self, admin_session):
		patient = _make_patient(first_name="NoDate")
		profile = _make_payer_profile(patient)
		check = _make_eligibility_check(patient, profile)
		assert check.name


# ---------------------------------------------------------------------------
# Test: Patient-profile cross-validation
# ---------------------------------------------------------------------------


class TestPatientProfileCrossValidation:
	def test_mismatched_patient_throws(self, admin_session):
		patient_a = _make_patient(first_name="CrossA")
		patient_b = _make_patient(first_name="CrossB")
		profile_b = _make_payer_profile(patient_b, payer_type="Cash")

		with pytest.raises(
			frappe.exceptions.ValidationError, match="Patient Mismatch"
		):
			_make_eligibility_check(patient_a, profile_b)

	def test_matching_patient_ok(self, admin_session):
		patient = _make_patient(first_name="CrossOK")
		profile = _make_payer_profile(patient, payer_type="Cash")
		check = _make_eligibility_check(patient, profile)
		assert check.name
