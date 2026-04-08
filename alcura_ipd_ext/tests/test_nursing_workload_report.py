"""Tests for US-N1: Nursing Workload by Ward report and service.

Covers: ward-level census, acuity aggregation, overdue chart/MAR/protocol
counting, workload score computation, filter behaviour, and report output
(columns, chart, summary).
"""

from __future__ import annotations

import frappe
import pytest
from frappe.utils import add_to_date, now_datetime


# ── Helpers ──────────────────────────────────────────────────────────


def _get_or_create_company(name="Test Hospital N1", abbr="TN1"):
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


def _make_ward(suffix="A", company=None):
	company = company or _get_or_create_company()
	ward_code = f"NW{suffix}"
	name = f"{frappe.db.get_value('Company', company, 'abbr')}-{ward_code}"
	if frappe.db.exists("Hospital Ward", name):
		return frappe.get_doc("Hospital Ward", name)

	doc = frappe.get_doc({
		"doctype": "Hospital Ward",
		"ward_code": ward_code,
		"ward_name": f"Test Ward {suffix}",
		"company": company,
		"is_active": 1,
		"classification": "General",
	})
	doc.insert(ignore_permissions=True)
	return doc


def _make_patient(suffix="N1"):
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


def _make_ir(patient=None, company=None, ward=None):
	patient = patient or _make_patient()
	company = company or _get_or_create_company()
	doc = frappe.get_doc({
		"doctype": "Inpatient Record",
		"patient": patient,
		"company": company,
		"status": "Admitted",
		"scheduled_date": frappe.utils.today(),
	})
	doc.insert(ignore_permissions=True)

	if ward:
		frappe.db.set_value(
			"Inpatient Record", doc.name,
			"custom_current_ward", ward,
			update_modified=False,
		)

	return doc


def _make_chart_template(name="NW Test Vitals"):
	if frappe.db.exists("IPD Chart Template", name):
		return frappe.get_doc("IPD Chart Template", name)
	doc = frappe.get_doc({
		"doctype": "IPD Chart Template",
		"template_name": name,
		"chart_type": "Vitals",
		"default_frequency_minutes": 60,
		"is_active": 1,
		"parameters": [
			{
				"parameter_name": "Temperature",
				"parameter_type": "Numeric",
				"uom": "C",
				"is_mandatory": 1,
				"display_order": 10,
			},
		],
	})
	doc.insert(ignore_permissions=True)
	return doc


# ── Service Tests ────────────────────────────────────────────────────


class TestNursingWorkloadService:

	def test_empty_wards_returns_empty(self, admin_session):
		from alcura_ipd_ext.services.nursing_workload_service import get_ward_workload

		result = get_ward_workload(company="Nonexistent Company 12345")
		assert result == []

	def test_census_counted_per_ward(self, admin_session):
		from alcura_ipd_ext.services.nursing_workload_service import get_ward_workload

		company = _get_or_create_company()
		ward_a = _make_ward("CA", company)
		ward_b = _make_ward("CB", company)

		_make_ir(patient=_make_patient("N1CA1"), company=company, ward=ward_a.name)
		_make_ir(patient=_make_patient("N1CA2"), company=company, ward=ward_a.name)
		_make_ir(patient=_make_patient("N1CB1"), company=company, ward=ward_b.name)

		rows = get_ward_workload(company=company)
		census_map = {r["ward"]: r["patient_census"] for r in rows}

		assert census_map.get(ward_a.name) == 2
		assert census_map.get(ward_b.name) == 1

	def test_high_acuity_counted(self, admin_session):
		from alcura_ipd_ext.services.nursing_workload_service import get_ward_workload

		company = _get_or_create_company()
		ward = _make_ward("HA", company)

		ir_high = _make_ir(patient=_make_patient("N1HA1"), company=company, ward=ward.name)
		frappe.db.set_value(
			"Inpatient Record", ir_high.name,
			"custom_fall_risk_level", "High",
			update_modified=False,
		)

		ir_low = _make_ir(patient=_make_patient("N1HA2"), company=company, ward=ward.name)
		frappe.db.set_value(
			"Inpatient Record", ir_low.name,
			"custom_fall_risk_level", "Low",
			update_modified=False,
		)

		rows = get_ward_workload(company=company, ward=ward.name)
		assert len(rows) == 1
		assert rows[0]["high_acuity_count"] == 1

	def test_overdue_mar_counted(self, admin_session):
		from alcura_ipd_ext.services.nursing_workload_service import get_ward_workload

		company = _get_or_create_company()
		ward = _make_ward("MA", company)
		patient = _make_patient("N1MA1")
		ir = _make_ir(patient=patient, company=company, ward=ward.name)

		frappe.get_doc({
			"doctype": "IPD MAR Entry",
			"patient": patient,
			"inpatient_record": ir.name,
			"medication_name": "Test Med",
			"dose": "500mg",
			"route": "Oral",
			"scheduled_time": add_to_date(now_datetime(), hours=-2),
			"administration_status": "Missed",
			"ward": ward.name,
		}).insert(ignore_permissions=True)

		rows = get_ward_workload(company=company, ward=ward.name)
		assert len(rows) == 1
		assert rows[0]["overdue_mar_count"] == 1

	def test_workload_score_computation(self, admin_session):
		from alcura_ipd_ext.services.nursing_workload_service import get_ward_workload

		company = _get_or_create_company()
		ward = _make_ward("SC", company)

		ir = _make_ir(patient=_make_patient("N1SC1"), company=company, ward=ward.name)
		frappe.db.set_value(
			"Inpatient Record", ir.name,
			"custom_fall_risk_level", "High",
			update_modified=False,
		)

		rows = get_ward_workload(company=company, ward=ward.name)
		assert len(rows) == 1
		# census=1 * 1 + high_acuity=1 * 2 = 3
		assert rows[0]["workload_score"] >= 3

	def test_ward_filter(self, admin_session):
		from alcura_ipd_ext.services.nursing_workload_service import get_ward_workload

		company = _get_or_create_company()
		ward_a = _make_ward("FA", company)
		ward_b = _make_ward("FB", company)

		_make_ir(patient=_make_patient("N1FA1"), company=company, ward=ward_a.name)
		_make_ir(patient=_make_patient("N1FB1"), company=company, ward=ward_b.name)

		rows = get_ward_workload(company=company, ward=ward_a.name)
		assert len(rows) == 1
		assert rows[0]["ward"] == ward_a.name

	def test_totals(self, admin_session):
		from alcura_ipd_ext.services.nursing_workload_service import (
			get_ward_workload,
			get_workload_totals,
		)

		company = _get_or_create_company()
		ward = _make_ward("TT", company)
		_make_ir(patient=_make_patient("N1TT1"), company=company, ward=ward.name)
		_make_ir(patient=_make_patient("N1TT2"), company=company, ward=ward.name)

		rows = get_ward_workload(company=company, ward=ward.name)
		totals = get_workload_totals(rows)

		assert totals["patient_census"] == 2
		assert "highest_workload_ward" in totals


# ── Report Output Tests ──────────────────────────────────────────────


class TestNursingWorkloadReport:

	def test_report_returns_five_tuple(self, admin_session):
		from alcura_ipd_ext.alcura_ipd_extensions.report.nursing_workload_by_ward.nursing_workload_by_ward import (
			execute,
		)

		result = execute({"company": "Nonexistent Company 12345"})
		assert len(result) == 5

		columns, data, _, chart, summary = result
		assert isinstance(columns, list)
		assert data == []
		assert chart is None
		assert summary == []

	def test_report_columns(self, admin_session):
		from alcura_ipd_ext.alcura_ipd_extensions.report.nursing_workload_by_ward.nursing_workload_by_ward import (
			_get_columns,
		)

		col_names = [c["fieldname"] for c in _get_columns()]
		assert "ward" in col_names
		assert "patient_census" in col_names
		assert "workload_score" in col_names
		assert "overdue_charts" in col_names
		assert "overdue_mar_count" in col_names

	def test_report_chart_generated(self, admin_session):
		from alcura_ipd_ext.alcura_ipd_extensions.report.nursing_workload_by_ward.nursing_workload_by_ward import (
			execute,
		)

		company = _get_or_create_company()
		ward = _make_ward("RC", company)
		_make_ir(patient=_make_patient("N1RC1"), company=company, ward=ward.name)

		result = execute({"company": company})
		_, data, _, chart, summary = result

		assert len(data) >= 1
		assert chart is not None
		assert chart["type"] == "bar"
		assert len(summary) >= 1
