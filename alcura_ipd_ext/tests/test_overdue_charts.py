"""Tests for overdue chart detection and notification generation (US-E4)."""

from __future__ import annotations

import frappe
import pytest
from frappe.utils import add_to_date, now_datetime


# ── Helpers ──────────────────────────────────────────────────────────


def _make_chart_template(name="Overdue Test Vitals"):
	if frappe.db.exists("IPD Chart Template", name):
		return frappe.get_doc("IPD Chart Template", name)

	doc = frappe.get_doc({
		"doctype": "IPD Chart Template",
		"template_name": name,
		"chart_type": "Vitals",
		"default_frequency_minutes": 30,
		"is_active": 1,
		"parameters": [
			{
				"parameter_name": "Temperature",
				"parameter_type": "Numeric",
				"uom": "°C",
				"is_mandatory": 1,
				"display_order": 10,
			},
		],
	})
	doc.insert(ignore_permissions=True)
	return doc


def _make_ir():
	patient = _ensure_patient()
	ir = frappe.get_doc({
		"doctype": "Inpatient Record",
		"patient": patient.name,
		"company": frappe.defaults.get_defaults().get("company", "_Test Company"),
		"status": "Admitted",
		"scheduled_date": frappe.utils.today(),
	})
	ir.insert(ignore_permissions=True)
	return ir


def _ensure_patient():
	if frappe.db.exists("Patient", {"patient_name": "_Test Overdue Patient"}):
		return frappe.get_doc("Patient", {"patient_name": "_Test Overdue Patient"})
	p = frappe.get_doc({
		"doctype": "Patient",
		"first_name": "_Test",
		"last_name": "Overdue Patient",
	})
	p.insert(ignore_permissions=True)
	return p


# ── Overdue Detection Tests ─────────────────────────────────────────


class TestOverdueDetection:
	def test_new_chart_not_overdue(self, admin_session):
		from alcura_ipd_ext.services.charting_service import get_overdue_charts, start_bedside_chart

		template = _make_chart_template("NotOverdue Vitals")
		ir = _make_ir()
		start_bedside_chart(ir.name, template.name)

		overdue = get_overdue_charts()
		names = [c["name"] for c in overdue]
		assert not any(ir.name in str(c.get("inpatient_record", "")) for c in overdue) or len(overdue) == 0

	def test_stale_chart_is_overdue(self, admin_session):
		from alcura_ipd_ext.services.charting_service import get_overdue_charts, start_bedside_chart

		template = _make_chart_template("StaleOverdue Vitals")
		ir = _make_ir()
		result = start_bedside_chart(ir.name, template.name)

		past_time = add_to_date(now_datetime(), minutes=-60)
		frappe.db.set_value(
			"IPD Bedside Chart", result["chart"],
			{"started_at": past_time, "last_entry_at": None},
			update_modified=False,
		)

		overdue = get_overdue_charts()
		chart_names = [c["name"] for c in overdue]
		assert result["chart"] in chart_names

	def test_overdue_with_grace_period(self, admin_session):
		from alcura_ipd_ext.services.charting_service import get_overdue_charts, start_bedside_chart

		template = _make_chart_template("Grace Vitals")
		ir = _make_ir()
		result = start_bedside_chart(ir.name, template.name)

		past_time = add_to_date(now_datetime(), minutes=-35)
		frappe.db.set_value(
			"IPD Bedside Chart", result["chart"],
			{"started_at": past_time, "last_entry_at": None},
			update_modified=False,
		)

		overdue_no_grace = get_overdue_charts(grace_minutes=0)
		overdue_with_grace = get_overdue_charts(grace_minutes=10)

		names_no_grace = [c["name"] for c in overdue_no_grace]
		names_with_grace = [c["name"] for c in overdue_with_grace]

		assert result["chart"] in names_no_grace
		assert result["chart"] not in names_with_grace

	def test_discontinued_chart_not_overdue(self, admin_session):
		from alcura_ipd_ext.services.charting_service import get_overdue_charts, start_bedside_chart

		template = _make_chart_template("DiscNotOverdue Vitals")
		ir = _make_ir()
		result = start_bedside_chart(ir.name, template.name)

		past_time = add_to_date(now_datetime(), minutes=-60)
		chart = frappe.get_doc("IPD Bedside Chart", result["chart"])
		chart.db_set("started_at", past_time)
		chart.status = "Discontinued"
		chart.save(ignore_permissions=True)

		overdue = get_overdue_charts()
		chart_names = [c["name"] for c in overdue]
		assert result["chart"] not in chart_names


# ── Virtual Property Tests ──────────────────────────────────────────


class TestBedsideChartProperties:
	def test_is_overdue_property(self, admin_session):
		from alcura_ipd_ext.services.charting_service import start_bedside_chart

		template = _make_chart_template("PropOverdue Vitals")
		ir = _make_ir()
		result = start_bedside_chart(ir.name, template.name)

		past_time = add_to_date(now_datetime(), minutes=-60)
		frappe.db.set_value(
			"IPD Bedside Chart", result["chart"],
			{"started_at": past_time, "last_entry_at": None},
			update_modified=False,
		)

		chart = frappe.get_doc("IPD Bedside Chart", result["chart"])
		assert chart.is_overdue
		assert chart.overdue_minutes > 0

	def test_not_overdue_when_paused(self, admin_session):
		from alcura_ipd_ext.services.charting_service import start_bedside_chart

		template = _make_chart_template("PausedOverdue Vitals")
		ir = _make_ir()
		result = start_bedside_chart(ir.name, template.name)

		past_time = add_to_date(now_datetime(), minutes=-60)
		chart = frappe.get_doc("IPD Bedside Chart", result["chart"])
		chart.db_set("started_at", past_time)
		chart.status = "Paused"
		chart.save(ignore_permissions=True)

		chart.reload()
		assert not chart.is_overdue
