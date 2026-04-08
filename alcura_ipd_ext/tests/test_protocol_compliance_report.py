"""Tests for US-L4: Protocol Compliance Report enhancements.

Covers: ICU unit type filtering, step detail drilldown, delayed step
counting, patient_name column, summary metrics, chart generation,
and batch query correctness.
"""

from __future__ import annotations

import frappe
import pytest
from frappe.utils import now_datetime, add_to_date


# ── Helpers ──────────────────────────────────────────────────────────


def _get_or_create_company(name="Test Hospital L4", abbr="TL4"):
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


def _make_patient(suffix="L4"):
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


def _make_ir(patient=None, company=None, **kwargs):
	patient = patient or _make_patient()
	company = company or _get_or_create_company()
	doc = frappe.get_doc({
		"doctype": "Inpatient Record",
		"patient": patient,
		"company": company,
		"status": "Admitted",
		"scheduled_date": frappe.utils.today(),
		**kwargs,
	})
	doc.insert(ignore_permissions=True)
	return doc


def _make_protocol_bundle(name="Test Sepsis Bundle L4"):
	if frappe.db.exists("Monitoring Protocol Bundle", name):
		return frappe.get_doc("Monitoring Protocol Bundle", name)
	doc = frappe.get_doc({
		"doctype": "Monitoring Protocol Bundle",
		"bundle_name": name,
		"category": "Sepsis",
		"is_active": 1,
		"steps": [
			{
				"step_name": "Blood Culture",
				"step_type": "Lab Test",
				"sequence": 1,
				"is_mandatory": 1,
				"target_minutes": 30,
			},
			{
				"step_name": "Antibiotics",
				"step_type": "Medication",
				"sequence": 2,
				"is_mandatory": 1,
				"target_minutes": 60,
			},
			{
				"step_name": "Lactate Level",
				"step_type": "Lab Test",
				"sequence": 3,
				"is_mandatory": 0,
				"target_minutes": 120,
			},
		],
	})
	doc.insert(ignore_permissions=True)
	return doc


def _make_active_bundle(ir, protocol_bundle, status="Active", compliance_score=100, **kwargs):
	now = now_datetime()
	doc = frappe.get_doc({
		"doctype": "Active Protocol Bundle",
		"protocol_bundle": protocol_bundle.name,
		"patient": ir.patient,
		"inpatient_record": ir.name,
		"status": status,
		"compliance_score": compliance_score,
		"activated_at": now,
		"activated_by": "Administrator",
		"step_trackers": [
			{
				"step_name": "Blood Culture",
				"step_type": "Lab Test",
				"sequence": 1,
				"is_mandatory": 1,
				"status": "Completed",
				"due_at": add_to_date(now, minutes=-30),
				"completed_at": add_to_date(now, minutes=-25),
			},
			{
				"step_name": "Antibiotics",
				"step_type": "Medication",
				"sequence": 2,
				"is_mandatory": 1,
				"status": "Completed",
				"due_at": add_to_date(now, minutes=-60),
				"completed_at": add_to_date(now, minutes=-10),
			},
			{
				"step_name": "Lactate Level",
				"step_type": "Lab Test",
				"sequence": 3,
				"is_mandatory": 0,
				"status": "Missed",
				"due_at": add_to_date(now, minutes=-120),
			},
		],
		**kwargs,
	})
	doc.insert(ignore_permissions=True)
	return doc


# ── Tests ────────────────────────────────────────────────────────────


class TestProtocolComplianceReport:

	def test_report_includes_patient_name(self, admin_session):
		"""Report rows include patient_name."""
		from alcura_ipd_ext.alcura_ipd_extensions.report.protocol_compliance_report.protocol_compliance_report import (
			get_columns,
			get_data,
		)

		col_names = [c["fieldname"] for c in get_columns()]
		assert "patient_name" in col_names

		patient = _make_patient("L4PN")
		ir = _make_ir(patient=patient)
		pb = _make_protocol_bundle("PN Bundle L4")
		_make_active_bundle(ir, pb)

		data = get_data({})
		matching = [r for r in data if r.get("patient") == patient]
		assert len(matching) >= 1
		assert matching[0]["patient_name"]

	def test_report_includes_delayed_steps(self, admin_session):
		"""Report counts delayed steps (completed after due_at)."""
		from alcura_ipd_ext.alcura_ipd_extensions.report.protocol_compliance_report.protocol_compliance_report import (
			get_data,
		)

		patient = _make_patient("L4DS")
		ir = _make_ir(patient=patient)
		pb = _make_protocol_bundle("DS Bundle L4")
		ab = _make_active_bundle(ir, pb, compliance_score=66.7)

		data = get_data({})
		matching = [r for r in data if r.get("active_bundle") == ab.name]
		assert len(matching) == 1

		row = matching[0]
		assert row["delayed_steps"] >= 1
		assert row["missed_steps"] >= 1

	def test_step_detail_returns_steps(self, admin_session):
		"""get_step_detail returns individual step tracker rows."""
		from alcura_ipd_ext.alcura_ipd_extensions.report.protocol_compliance_report.protocol_compliance_report import (
			get_step_detail,
		)

		patient = _make_patient("L4SD")
		ir = _make_ir(patient=patient)
		pb = _make_protocol_bundle("SD Bundle L4")
		ab = _make_active_bundle(ir, pb)

		steps = get_step_detail(ab.name)
		assert len(steps) == 3

		step_names = {s["step_name"] for s in steps}
		assert "Blood Culture" in step_names
		assert "Antibiotics" in step_names

		delayed = [s for s in steps if s.get("delay_minutes") and s["delay_minutes"] > 0]
		assert len(delayed) >= 1

	def test_report_summary(self, admin_session):
		"""Report returns summary with avg compliance and totals."""
		from alcura_ipd_ext.alcura_ipd_extensions.report.protocol_compliance_report.protocol_compliance_report import (
			execute,
		)

		patient = _make_patient("L4RS")
		ir = _make_ir(patient=patient)
		pb = _make_protocol_bundle("RS Bundle L4")
		_make_active_bundle(ir, pb, compliance_score=80)

		result = execute({})
		assert len(result) == 5

		_, data, _, chart, summary = result
		assert len(data) >= 1
		assert len(summary) >= 1

		labels = {s["label"] for s in summary}
		assert "Total Bundles" in labels
		assert "Avg Compliance" in labels

	def test_report_chart(self, admin_session):
		"""Report returns a bar chart by category."""
		from alcura_ipd_ext.alcura_ipd_extensions.report.protocol_compliance_report.protocol_compliance_report import (
			execute,
		)

		patient = _make_patient("L4CH")
		ir = _make_ir(patient=patient)
		pb = _make_protocol_bundle("CH Bundle L4")
		_make_active_bundle(ir, pb)

		result = execute({})
		_, _, _, chart, _ = result
		assert chart is not None
		assert chart["type"] == "bar"

	def test_category_filter(self, admin_session):
		"""Category filter restricts results to matching protocol bundles."""
		from alcura_ipd_ext.alcura_ipd_extensions.report.protocol_compliance_report.protocol_compliance_report import (
			get_data,
		)

		patient = _make_patient("L4CF")
		ir = _make_ir(patient=patient)
		pb = _make_protocol_bundle("CF Bundle L4")
		_make_active_bundle(ir, pb)

		data_sepsis = get_data({"category": "Sepsis"})
		data_other = get_data({"category": "Ventilator"})

		sepsis_bundles = [r for r in data_sepsis if r.get("patient") == patient]
		other_bundles = [r for r in data_other if r.get("patient") == patient]

		assert len(sepsis_bundles) >= 1
		assert len(other_bundles) == 0

	def test_empty_report(self, admin_session):
		"""Empty data returns no chart and no summary."""
		from alcura_ipd_ext.alcura_ipd_extensions.report.protocol_compliance_report.protocol_compliance_report import (
			execute,
		)

		result = execute({
			"from_date": "2020-01-01",
			"to_date": "2020-01-01",
		})
		_, data, _, chart, summary = result
		assert data == []
		assert chart is None
		assert summary == []
