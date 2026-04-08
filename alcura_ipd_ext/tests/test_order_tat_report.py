"""Tests for US-L3: Order TAT Report and SLA Breach Report.

Covers: TAT calculation, summary metrics, department breakdown,
SLA target comparison, chart generation, and breach report enhancements.
"""

from __future__ import annotations

import frappe
import pytest
from frappe.utils import now_datetime, add_to_date


# ── Helpers ──────────────────────────────────────────────────────────


def _get_or_create_company(name="Test Hospital L3", abbr="TL3"):
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


def _make_practitioner(suffix="L3"):
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


def _make_patient(suffix="L3"):
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


def _make_ir(patient=None, company=None):
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
	return doc


def _make_clinical_order(
	ir_name,
	patient=None,
	company=None,
	order_type="Lab Test",
	urgency="Routine",
	status="Completed",
	ordered_at=None,
	acknowledged_at=None,
	completed_at=None,
	is_sla_breached=0,
	target_department=None,
	**kwargs,
):
	patient = patient or _make_patient()
	company = company or _get_or_create_company()
	now = now_datetime()
	doc = frappe.get_doc({
		"doctype": "IPD Clinical Order",
		"inpatient_record": ir_name,
		"patient": patient,
		"company": company,
		"order_type": order_type,
		"urgency": urgency,
		"status": status,
		"ordered_at": ordered_at or add_to_date(now, hours=-2),
		"acknowledged_at": acknowledged_at,
		"completed_at": completed_at,
		"is_sla_breached": is_sla_breached,
		"target_department": target_department,
		**kwargs,
	})
	doc.insert(ignore_permissions=True)
	return doc


# ── TAT Report Tests ────────────────────────────────────────────────


class TestOrderTATReport:

	def test_tat_calculated_for_completed_orders(self, admin_session):
		"""TAT is calculated when both ordered_at and completed_at are set."""
		from alcura_ipd_ext.alcura_ipd_extensions.report.order_tat_report.order_tat_report import (
			execute,
		)

		patient = _make_patient("L3TC")
		ir = _make_ir(patient=patient)
		now = now_datetime()
		ordered = add_to_date(now, hours=-1)

		_make_clinical_order(
			ir.name,
			patient=patient,
			ordered_at=ordered,
			acknowledged_at=add_to_date(ordered, minutes=10),
			completed_at=now,
			status="Completed",
		)

		result = execute({
			"from_date": frappe.utils.today(),
			"to_date": frappe.utils.today(),
		})
		columns, data, _, _, _ = result

		matching = [r for r in data if r["patient_name"] and ir.patient in str(r.get("name", ""))]
		assert len(data) >= 1

		for row in data:
			if row.get("tat_minutes") is not None:
				assert row["tat_minutes"] > 0
				break

	def test_report_returns_summary_metrics(self, admin_session):
		"""Report returns summary with total, avg TAT, median TAT, etc."""
		from alcura_ipd_ext.alcura_ipd_extensions.report.order_tat_report.order_tat_report import (
			execute,
		)

		patient = _make_patient("L3SM")
		ir = _make_ir(patient=patient)
		now = now_datetime()

		_make_clinical_order(
			ir.name,
			patient=patient,
			ordered_at=add_to_date(now, hours=-1),
			completed_at=now,
			status="Completed",
		)

		result = execute({
			"from_date": frappe.utils.today(),
			"to_date": frappe.utils.today(),
		})
		assert len(result) == 5

		_, _, _, _, summary = result
		assert len(summary) >= 1

		labels = {s["label"] for s in summary}
		assert "Total Orders" in labels

	def test_department_column_present(self, admin_session):
		"""Report includes target_department column."""
		from alcura_ipd_ext.alcura_ipd_extensions.report.order_tat_report.order_tat_report import (
			_get_columns,
		)

		col_names = [c["fieldname"] for c in _get_columns()]
		assert "target_department" in col_names

	def test_sla_target_column_present(self, admin_session):
		"""Report includes sla_target_minutes column."""
		from alcura_ipd_ext.alcura_ipd_extensions.report.order_tat_report.order_tat_report import (
			_get_columns,
		)

		col_names = [c["fieldname"] for c in _get_columns()]
		assert "sla_target_minutes" in col_names

	def test_chart_generated(self, admin_session):
		"""Report returns a chart when data exists."""
		from alcura_ipd_ext.alcura_ipd_extensions.report.order_tat_report.order_tat_report import (
			execute,
		)

		patient = _make_patient("L3CG")
		ir = _make_ir(patient=patient)
		now = now_datetime()

		_make_clinical_order(
			ir.name,
			patient=patient,
			ordered_at=add_to_date(now, hours=-1),
			completed_at=now,
		)

		result = execute({
			"from_date": frappe.utils.today(),
			"to_date": frappe.utils.today(),
		})
		_, _, _, chart, _ = result
		assert chart is not None
		assert chart["type"] == "bar"

	def test_empty_report(self, admin_session):
		"""Empty data returns no chart and no summary."""
		from alcura_ipd_ext.alcura_ipd_extensions.report.order_tat_report.order_tat_report import (
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


# ── SLA Breach Report Tests ─────────────────────────────────────────


class TestSLABreachReport:

	def test_breach_report_includes_department(self, admin_session):
		"""Breach report includes target_department column."""
		from alcura_ipd_ext.alcura_ipd_extensions.report.sla_breach_report.sla_breach_report import (
			_get_columns,
		)

		col_names = [c["fieldname"] for c in _get_columns()]
		assert "target_department" in col_names

	def test_breach_report_returns_summary(self, admin_session):
		"""Breach report returns summary metrics."""
		from alcura_ipd_ext.alcura_ipd_extensions.report.sla_breach_report.sla_breach_report import (
			execute,
		)

		patient = _make_patient("L3BS")
		ir = _make_ir(patient=patient)
		now = now_datetime()

		order = _make_clinical_order(
			ir.name,
			patient=patient,
			ordered_at=add_to_date(now, hours=-2),
			completed_at=now,
			is_sla_breached=1,
			sla_breach_count=1,
		)

		result = execute({
			"from_date": frappe.utils.today(),
			"to_date": frappe.utils.today(),
		})
		assert len(result) == 5
		_, data, _, chart, summary = result
		assert len(data) >= 1
		assert len(summary) >= 1

	def test_breach_report_chart(self, admin_session):
		"""Breach report includes a bar chart by order type."""
		from alcura_ipd_ext.alcura_ipd_extensions.report.sla_breach_report.sla_breach_report import (
			execute,
		)

		patient = _make_patient("L3BC")
		ir = _make_ir(patient=patient)
		now = now_datetime()

		_make_clinical_order(
			ir.name,
			patient=patient,
			ordered_at=add_to_date(now, hours=-1),
			is_sla_breached=1,
			sla_breach_count=1,
		)

		result = execute({
			"from_date": frappe.utils.today(),
			"to_date": frappe.utils.today(),
		})
		_, _, _, chart, _ = result
		assert chart is not None
		assert chart["type"] == "bar"
