"""Tests for discharge advice service (US-J1).

Covers discharge advice creation, status transitions, cancellation,
duplicate prevention, and aggregate discharge status.
"""

from __future__ import annotations

import frappe
import pytest
from frappe.utils import add_days, now_datetime, today

from alcura_ipd_ext.services.discharge_advice_service import (
	acknowledge_advice,
	cancel_advice,
	complete_advice,
	create_discharge_advice,
	get_discharge_status,
)


# ── Helpers ──────────────────────────────────────────────────────────


def _ensure_company():
	if not frappe.db.exists("Company", "_Test HK Company"):
		frappe.get_doc({
			"doctype": "Company",
			"company_name": "_Test HK Company",
			"abbr": "THK",
			"default_currency": "INR",
			"country": "India",
		}).insert(ignore_permissions=True)
	return "_Test HK Company"


def _ensure_patient():
	if not frappe.db.exists("Patient", {"first_name": "_Test Discharge Patient"}):
		doc = frappe.get_doc({
			"doctype": "Patient",
			"first_name": "_Test Discharge Patient",
			"sex": "Male",
		})
		doc.insert(ignore_permissions=True)
		return doc.name
	return frappe.db.get_value("Patient", {"first_name": "_Test Discharge Patient"}, "name")


def _ensure_practitioner():
	if not frappe.db.exists("Healthcare Practitioner", {"practitioner_name": "_Test Discharge Dr"}):
		doc = frappe.get_doc({
			"doctype": "Healthcare Practitioner",
			"first_name": "_Test Discharge Dr",
		})
		doc.insert(ignore_permissions=True)
		return doc.name
	return frappe.db.get_value(
		"Healthcare Practitioner", {"practitioner_name": "_Test Discharge Dr"}, "name"
	)


def _ensure_ir(patient, company, status="Admitted"):
	doc = frappe.get_doc({
		"doctype": "Inpatient Record",
		"patient": patient,
		"company": company,
		"status": status,
		"scheduled_date": today(),
	})
	doc.insert(ignore_permissions=True)
	if status == "Admitted":
		doc.db_set("status", "Admitted")
		doc.db_set("admitted_datetime", now_datetime())
	return doc.name


# ── Tests ────────────────────────────────────────────────────────────


class TestDischargeAdviceCreation:
	def test_create_advice_for_admitted_patient(self, admin_session):
		company = _ensure_company()
		patient = _ensure_patient()
		practitioner = _ensure_practitioner()
		ir = _ensure_ir(patient, company, status="Admitted")

		name = create_discharge_advice(
			inpatient_record=ir,
			consultant=practitioner,
			expected_discharge_datetime=str(add_days(now_datetime(), 1)),
			discharge_type="Normal",
			primary_diagnosis="Test diagnosis",
		)

		assert name
		doc = frappe.get_doc("IPD Discharge Advice", name)
		assert doc.status == "Advised"
		assert doc.patient == patient
		assert doc.advised_by == "Administrator"
		assert doc.advised_on is not None

	def test_reject_for_non_admitted_patient(self, admin_session):
		company = _ensure_company()
		patient = _ensure_patient()
		practitioner = _ensure_practitioner()
		ir = _ensure_ir(patient, company, status="Admission Scheduled")

		with pytest.raises(frappe.ValidationError):
			create_discharge_advice(
				inpatient_record=ir,
				consultant=practitioner,
				expected_discharge_datetime=str(add_days(now_datetime(), 1)),
			)

	def test_reject_duplicate_active_advice(self, admin_session):
		company = _ensure_company()
		patient = _ensure_patient()
		practitioner = _ensure_practitioner()
		ir = _ensure_ir(patient, company)

		create_discharge_advice(
			inpatient_record=ir,
			consultant=practitioner,
			expected_discharge_datetime=str(add_days(now_datetime(), 1)),
		)

		with pytest.raises(frappe.ValidationError, match="active discharge advice"):
			create_discharge_advice(
				inpatient_record=ir,
				consultant=practitioner,
				expected_discharge_datetime=str(add_days(now_datetime(), 2)),
			)


class TestDischargeAdviceTransitions:
	def test_acknowledge_from_advised(self, admin_session):
		company = _ensure_company()
		patient = _ensure_patient()
		practitioner = _ensure_practitioner()
		ir = _ensure_ir(patient, company)

		name = create_discharge_advice(
			inpatient_record=ir,
			consultant=practitioner,
			expected_discharge_datetime=str(add_days(now_datetime(), 1)),
		)

		acknowledge_advice(name)
		doc = frappe.get_doc("IPD Discharge Advice", name)
		assert doc.status == "Acknowledged"
		assert doc.acknowledged_by == "Administrator"

	def test_complete_from_acknowledged(self, admin_session):
		company = _ensure_company()
		patient = _ensure_patient()
		practitioner = _ensure_practitioner()
		ir = _ensure_ir(patient, company)

		name = create_discharge_advice(
			inpatient_record=ir,
			consultant=practitioner,
			expected_discharge_datetime=str(add_days(now_datetime(), 1)),
		)

		acknowledge_advice(name)
		complete_advice(name)

		doc = frappe.get_doc("IPD Discharge Advice", name)
		assert doc.status == "Completed"
		assert doc.actual_discharge_datetime is not None

	def test_cancel_with_reason(self, admin_session):
		company = _ensure_company()
		patient = _ensure_patient()
		practitioner = _ensure_practitioner()
		ir = _ensure_ir(patient, company)

		name = create_discharge_advice(
			inpatient_record=ir,
			consultant=practitioner,
			expected_discharge_datetime=str(add_days(now_datetime(), 1)),
		)

		cancel_advice(name, reason="Patient condition worsened")
		doc = frappe.get_doc("IPD Discharge Advice", name)
		assert doc.status == "Cancelled"
		assert doc.cancellation_reason == "Patient condition worsened"

	def test_cancel_without_reason_fails(self, admin_session):
		company = _ensure_company()
		patient = _ensure_patient()
		practitioner = _ensure_practitioner()
		ir = _ensure_ir(patient, company)

		name = create_discharge_advice(
			inpatient_record=ir,
			consultant=practitioner,
			expected_discharge_datetime=str(add_days(now_datetime(), 1)),
		)

		with pytest.raises(Exception, match="[Rr]eason"):
			cancel_advice(name, reason="")


class TestDischargeStatus:
	def test_aggregate_status_with_no_advice(self, admin_session):
		result = get_discharge_status("NON-EXISTENT-IR")
		assert result["advice"] is None
		assert result["ready_to_vacate"] is False

	def test_aggregate_status_with_advice(self, admin_session):
		company = _ensure_company()
		patient = _ensure_patient()
		practitioner = _ensure_practitioner()
		ir = _ensure_ir(patient, company)

		name = create_discharge_advice(
			inpatient_record=ir,
			consultant=practitioner,
			expected_discharge_datetime=str(add_days(now_datetime(), 1)),
		)

		result = get_discharge_status(ir)
		assert result["advice"]["name"] == name
		assert result["advice"]["status"] == "Advised"
		assert result["ready_to_vacate"] is False
