"""Tests for US-L2: Documentation Compliance Service.

Covers: compliance scoring, admission note detection, progress note gap
calculation, intake status check, nursing chart currency, discharge
summary applicability, and batch query correctness.
"""

from __future__ import annotations

import frappe
import pytest
from frappe.utils import today, add_days, getdate

from alcura_ipd_ext.services.documentation_compliance_service import (
	get_documentation_compliance,
	_compute_compliance_score,
)


# ── Helpers ──────────────────────────────────────────────────────────


def _get_or_create_company(name="Test Hospital L2", abbr="TL2"):
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


def _make_practitioner(suffix="L2"):
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


def _make_patient(suffix="L2"):
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


def _make_dept(name="General L2"):
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


class TestDocumentationCompliance:

	def test_empty_result_for_no_admissions(self, admin_session):
		"""Returns empty list when no admitted patients exist for filters."""
		result = get_documentation_compliance(
			company="Nonexistent Company XYZ"
		)
		assert result == []

	def test_new_admission_has_low_compliance(self, admin_session):
		"""A new admission without any documentation should have low score."""
		practitioner = _make_practitioner("L2LC")
		ir = _make_ir(
			patient=_make_patient("L2LC"),
			practitioner=practitioner,
		)

		result = get_documentation_compliance(practitioner=practitioner)
		row = next(r for r in result if r["inpatient_record"] == ir.name)

		assert row["has_admission_note"] == 0
		assert row["intake_complete"] == 0
		assert row["compliance_score"] < 50

	def test_admission_note_detected(self, admin_session):
		"""When a submitted admission note exists, has_admission_note is 1."""
		practitioner = _make_practitioner("L2AN")
		patient = _make_patient("L2AN")
		ir = _make_ir(patient=patient, practitioner=practitioner)

		enc = frappe.get_doc({
			"doctype": "Patient Encounter",
			"patient": patient,
			"practitioner": practitioner,
			"company": ir.company,
			"encounter_date": today(),
			"custom_linked_inpatient_record": ir.name,
			"custom_ipd_note_type": "Admission Note",
			"custom_chief_complaint_text": "Test complaint",
		})
		enc.insert(ignore_permissions=True)
		enc.submit()

		result = get_documentation_compliance(practitioner=practitioner)
		row = next(r for r in result if r["inpatient_record"] == ir.name)

		assert row["has_admission_note"] == 1

	def test_progress_note_gap_zero_for_today(self, admin_session):
		"""When a progress note was submitted today, gap should be 0."""
		practitioner = _make_practitioner("L2PG0")
		patient = _make_patient("L2PG0")
		ir = _make_ir(patient=patient, practitioner=practitioner)

		enc = frappe.get_doc({
			"doctype": "Patient Encounter",
			"patient": patient,
			"practitioner": practitioner,
			"company": ir.company,
			"encounter_date": today(),
			"custom_linked_inpatient_record": ir.name,
			"custom_ipd_note_type": "Progress Note",
		})
		enc.insert(ignore_permissions=True)
		enc.submit()

		result = get_documentation_compliance(practitioner=practitioner)
		row = next(r for r in result if r["inpatient_record"] == ir.name)

		assert row["progress_note_gap"] == 0

	def test_progress_note_gap_increases_with_age(self, admin_session):
		"""When no progress note exists and admission was 3 days ago, gap = 3."""
		practitioner = _make_practitioner("L2PG3")
		ir = _make_ir(
			patient=_make_patient("L2PG3"),
			practitioner=practitioner,
			scheduled_date=add_days(today(), -2),
		)

		result = get_documentation_compliance(practitioner=practitioner)
		row = next(r for r in result if r["inpatient_record"] == ir.name)

		assert row["progress_note_gap"] == row["days_admitted"]

	def test_intake_complete_flag(self, admin_session):
		"""When intake status is Completed, intake_complete is 1."""
		practitioner = _make_practitioner("L2IC")
		ir = _make_ir(
			patient=_make_patient("L2IC"),
			practitioner=practitioner,
			custom_intake_status="Completed",
		)

		result = get_documentation_compliance(practitioner=practitioner)
		row = next(r for r in result if r["inpatient_record"] == ir.name)

		assert row["intake_complete"] == 1

	def test_overdue_charts_flag(self, admin_session):
		"""When overdue charts exist, nursing_charts_ok is 0."""
		practitioner = _make_practitioner("L2OC")
		ir = _make_ir(
			patient=_make_patient("L2OC"),
			practitioner=practitioner,
			custom_overdue_charts_count=3,
		)

		result = get_documentation_compliance(practitioner=practitioner)
		row = next(r for r in result if r["inpatient_record"] == ir.name)

		assert row["nursing_charts_ok"] == 0
		assert row["overdue_charts"] == 3

	def test_discharge_summary_not_applicable_for_admitted(self, admin_session):
		"""Discharge summary check is None for patients still admitted."""
		practitioner = _make_practitioner("L2DS")
		ir = _make_ir(
			patient=_make_patient("L2DS"),
			practitioner=practitioner,
		)

		result = get_documentation_compliance(practitioner=practitioner)
		row = next(r for r in result if r["inpatient_record"] == ir.name)

		assert row["has_discharge_summary"] is None

	def test_compliance_score_all_passing(self, admin_session):
		"""100% score when all applicable checks pass."""
		row = {
			"has_admission_note": 1,
			"progress_note_gap": 0,
			"intake_complete": 1,
			"nursing_charts_ok": 1,
			"has_discharge_summary": None,
		}
		score = _compute_compliance_score(row)
		assert score == 100.0

	def test_compliance_score_partial(self, admin_session):
		"""50% when 2 of 4 checks pass."""
		row = {
			"has_admission_note": 1,
			"progress_note_gap": 3,
			"intake_complete": 0,
			"nursing_charts_ok": 1,
			"has_discharge_summary": None,
		}
		score = _compute_compliance_score(row)
		assert score == 50.0

	def test_report_execute_returns_chart(self, admin_session):
		"""Report execute returns a chart configuration."""
		from alcura_ipd_ext.alcura_ipd_ext.report.documentation_compliance.documentation_compliance import (
			execute,
		)

		practitioner = _make_practitioner("L2RE")
		_make_ir(
			patient=_make_patient("L2RE"),
			practitioner=practitioner,
		)

		result = execute({"practitioner": practitioner})
		assert len(result) == 5

		_, data, _, chart, summary = result
		assert len(data) >= 1
		assert chart is not None
		assert chart["type"] == "bar"
		assert len(summary) == 6
