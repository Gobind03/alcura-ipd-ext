"""Tests for US-L1: Doctor Census Report enhancements.

Covers: enhanced columns (pending_tests, due_meds, critical_alerts),
report summary cards, filter behaviour, and the report execute function.
"""

from __future__ import annotations

import frappe
import pytest
from frappe.utils import today, getdate

from alcura_ipd_ext.services.round_sheet_service import get_doctor_census


# ── Helpers ──────────────────────────────────────────────────────────


def _get_or_create_company(name="Test Hospital L1", abbr="TL1"):
	if frappe.db.exists("Company", name):
		return name
	doc = frappe.get_doc({
		"doctype": "Company",
		"company_name": name,
		"abbr": abbr,
		"default_currency": "INR",
		"country": "India",
	})
	doc.insert(ignore_if_duplicate=True)
	return doc.name


def _make_practitioner(suffix="L1"):
	fname = f"Dr Test {suffix}"
	existing = frappe.db.exists("Healthcare Practitioner", {"practitioner_name": fname})
	if existing:
		return existing
	doc = frappe.get_doc({
		"doctype": "Healthcare Practitioner",
		"first_name": "Dr Test",
		"last_name": suffix,
	})
	doc.insert(ignore_permissions=True)
	return doc.name


def _make_patient(suffix="L1"):
	patient_name = f"Test Patient {suffix}"
	existing = frappe.db.exists("Patient", {"patient_name": patient_name})
	if existing:
		return existing
	doc = frappe.get_doc({
		"doctype": "Patient",
		"first_name": f"Test {suffix}",
		"last_name": "Patient",
		"sex": "Male",
	})
	doc.insert(ignore_permissions=True)
	return doc.name


def _make_dept(name="General L1"):
	if frappe.db.exists("Medical Department", name):
		return name
	doc = frappe.get_doc({"doctype": "Medical Department", "department": name})
	doc.insert(ignore_permissions=True)
	return doc.name


def _make_ir(patient=None, practitioner=None, company=None, **kwargs):
	patient = patient or _make_patient()
	company = company or _get_or_create_company()
	practitioner = practitioner or _make_practitioner()
	dept = _make_dept()
	doc = frappe.get_doc({
		"doctype": "Inpatient Record",
		"patient": patient,
		"company": company,
		"primary_practitioner": practitioner,
		"medical_department": dept,
		"scheduled_date": today(),
		"status": "Admitted",
		**kwargs,
	})
	doc.insert(ignore_permissions=True)
	return doc


# ── Tests ────────────────────────────────────────────────────────────


class TestDoctorCensusEnhanced:
	"""US-L1: Verify enhanced census columns and report summary."""

	def test_census_includes_pending_tests_column(self, admin_session):
		"""Census rows include pending_tests from IR custom field."""
		practitioner = _make_practitioner("L1PT")
		ir = _make_ir(
			patient=_make_patient("L1PT"),
			practitioner=practitioner,
			custom_active_lab_orders=3,
		)

		census = get_doctor_census(practitioner)
		row = next(r for r in census if r["inpatient_record"] == ir.name)
		assert row["pending_tests"] == 3

	def test_census_includes_due_meds_column(self, admin_session):
		"""Census rows include due_meds from IR custom field."""
		practitioner = _make_practitioner("L1DM")
		ir = _make_ir(
			patient=_make_patient("L1DM"),
			practitioner=practitioner,
			custom_due_meds_count=5,
		)

		census = get_doctor_census(practitioner)
		row = next(r for r in census if r["inpatient_record"] == ir.name)
		assert row["due_meds"] == 5

	def test_census_includes_critical_alerts_column(self, admin_session):
		"""Census rows include critical_alerts from IR custom field."""
		practitioner = _make_practitioner("L1CA")
		ir = _make_ir(
			patient=_make_patient("L1CA"),
			practitioner=practitioner,
			custom_critical_alerts_count=2,
		)

		census = get_doctor_census(practitioner)
		row = next(r for r in census if r["inpatient_record"] == ir.name)
		assert row["critical_alerts"] == 2

	def test_census_zero_values_for_new_admission(self, admin_session):
		"""New admission returns zero for all counter columns."""
		practitioner = _make_practitioner("L1ZR")
		ir = _make_ir(
			patient=_make_patient("L1ZR"),
			practitioner=practitioner,
		)

		census = get_doctor_census(practitioner)
		row = next(r for r in census if r["inpatient_record"] == ir.name)
		assert row["pending_tests"] == 0
		assert row["due_meds"] == 0
		assert row["critical_alerts"] == 0

	def test_report_execute_returns_summary(self, admin_session):
		"""Report execute returns 5-tuple with report_summary."""
		from alcura_ipd_ext.alcura_ipd_ext.report.doctor_census.doctor_census import execute

		practitioner = _make_practitioner("L1EX")
		_make_ir(
			patient=_make_patient("L1EXa"),
			practitioner=practitioner,
			custom_critical_alerts_count=1,
		)
		_make_ir(
			patient=_make_patient("L1EXb"),
			practitioner=practitioner,
			custom_overdue_charts_count=2,
		)

		result = execute({"practitioner": practitioner})
		assert len(result) == 5

		columns, data, _, _, report_summary = result
		assert len(data) >= 2
		assert len(report_summary) == 4

		labels = {s["label"] for s in report_summary}
		assert "Total Patients" in labels
		assert "With Critical Alerts" in labels

	def test_report_execute_empty_without_practitioner(self, admin_session):
		"""Report returns empty data when no practitioner is specified."""
		from alcura_ipd_ext.alcura_ipd_ext.report.doctor_census.doctor_census import execute

		result = execute({})
		_, data, _, _, summary = result
		assert data == []
		assert summary == []

	def test_census_ward_filter(self, admin_session):
		"""Census respects ward filter."""
		practitioner = _make_practitioner("L1WF")
		ir = _make_ir(
			patient=_make_patient("L1WF"),
			practitioner=practitioner,
			custom_current_ward="NonexistentWard",
		)

		census = get_doctor_census(practitioner, ward="NonexistentWard")
		assert any(r["inpatient_record"] == ir.name for r in census)

		census_other = get_doctor_census(practitioner, ward="OtherWard")
		assert not any(r["inpatient_record"] == ir.name for r in census_other)
