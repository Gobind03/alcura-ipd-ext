"""Tests for observation trend service — trend queries, schedule generation,
missed observation detection, and dashboard summary (US-H2)."""

from __future__ import annotations

import frappe
import pytest
from frappe.utils import add_to_date, now_datetime


# ── Helpers ──────────────────────────────────────────────────────────


def _make_chart_template(
	name: str = "Trend Test Vitals",
	freq: int = 60,
) -> "frappe.Document":
	if frappe.db.exists("IPD Chart Template", name):
		return frappe.get_doc("IPD Chart Template", name)

	doc = frappe.get_doc({
		"doctype": "IPD Chart Template",
		"template_name": name,
		"chart_type": "Vitals",
		"default_frequency_minutes": freq,
		"is_active": 1,
		"parameters": [
			{
				"parameter_name": "Temperature",
				"parameter_type": "Numeric",
				"uom": "°C",
				"is_mandatory": 1,
				"display_order": 10,
				"min_value": 35.0,
				"max_value": 42.0,
				"critical_low": 35.5,
				"critical_high": 39.5,
			},
			{
				"parameter_name": "Pulse",
				"parameter_type": "Numeric",
				"uom": "bpm",
				"is_mandatory": 1,
				"display_order": 20,
				"min_value": 30,
				"max_value": 200,
				"critical_low": 50,
				"critical_high": 130,
			},
		],
	})
	doc.insert(ignore_permissions=True)
	return doc


def _make_ir() -> "frappe.Document":
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


def _ensure_patient() -> "frappe.Document":
	if frappe.db.exists("Patient", {"patient_name": "_Test Trend Patient"}):
		return frappe.get_doc("Patient", {"patient_name": "_Test Trend Patient"})
	p = frappe.get_doc({
		"doctype": "Patient",
		"first_name": "_Test",
		"last_name": "Trend Patient",
	})
	p.insert(ignore_permissions=True)
	return p


def _start_chart_and_record(
	template_name: str = "Trend Vitals",
	freq: int = 60,
	entry_count: int = 3,
) -> tuple:
	"""Create template, IR, chart, and record entries at regular intervals."""
	from alcura_ipd_ext.services.charting_service import (
		record_chart_entry,
		start_bedside_chart,
	)

	tmpl = _make_chart_template(template_name, freq)
	ir = _make_ir()
	now = now_datetime()
	start_time = add_to_date(now, hours=-entry_count)

	result = start_bedside_chart(ir.name, tmpl.name, freq)
	frappe.db.set_value(
		"IPD Bedside Chart", result["chart"], "started_at", start_time,
		update_modified=False,
	)

	entries = []
	for i in range(entry_count):
		entry_time = add_to_date(start_time, minutes=freq * i)
		entry = record_chart_entry(
			bedside_chart=result["chart"],
			observations=[
				{"parameter_name": "Temperature", "numeric_value": 37.0 + i * 0.2},
				{"parameter_name": "Pulse", "numeric_value": 72 + i * 2},
			],
			entry_datetime=str(entry_time),
		)
		entries.append(entry)

	return result["chart"], ir.name, entries


# ── Trend Query Tests ───────────────────────────────────────────────


class TestParameterTrend:
	def test_returns_time_series(self, admin_session):
		from alcura_ipd_ext.services.observation_trend_service import get_parameter_trend

		chart_name, _, entries = _start_chart_and_record("Trend TS Vitals", 60, 3)

		trend = get_parameter_trend(chart_name, "Temperature")
		assert len(trend) == 3
		assert all("datetime" in t and "value" in t for t in trend)
		assert trend[0]["value"] == 37.0
		assert trend[2]["value"] == pytest.approx(37.4, abs=0.01)

	def test_respects_date_range(self, admin_session):
		from alcura_ipd_ext.services.observation_trend_service import get_parameter_trend

		chart_name, _, _ = _start_chart_and_record("Trend Range Vitals", 60, 5)

		now = now_datetime()
		from_dt = str(add_to_date(now, hours=-2))
		trend = get_parameter_trend(chart_name, "Temperature", from_datetime=from_dt)
		assert len(trend) <= 3

	def test_respects_limit(self, admin_session):
		from alcura_ipd_ext.services.observation_trend_service import get_parameter_trend

		chart_name, _, _ = _start_chart_and_record("Trend Limit Vitals", 60, 5)
		trend = get_parameter_trend(chart_name, "Temperature", limit=2)
		assert len(trend) == 2


class TestMultiParameterTrend:
	def test_returns_keyed_data(self, admin_session):
		from alcura_ipd_ext.services.observation_trend_service import get_multi_parameter_trend

		chart_name, _, _ = _start_chart_and_record("Multi Trend Vitals", 60, 3)

		result = get_multi_parameter_trend(
			chart_name, ["Temperature", "Pulse"]
		)
		assert "Temperature" in result
		assert "Pulse" in result
		assert len(result["Temperature"]) == 3
		assert len(result["Pulse"]) == 3


# ── Schedule Tests ──────────────────────────────────────────────────


class TestObservationSchedule:
	def test_generates_expected_slots(self, admin_session):
		from alcura_ipd_ext.services.observation_trend_service import get_observation_schedule

		chart_name, _, _ = _start_chart_and_record("Sched Vitals", 60, 3)

		schedule = get_observation_schedule(chart_name)
		assert len(schedule) > 0
		assert all("expected_at" in s for s in schedule)
		recorded = [s for s in schedule if s["actual_at"]]
		assert len(recorded) >= 3

	def test_identifies_missed_slots(self, admin_session):
		from alcura_ipd_ext.services.charting_service import start_bedside_chart
		from alcura_ipd_ext.services.observation_trend_service import (
			compute_missed_observations,
		)

		tmpl = _make_chart_template("Missed Vitals", 60)
		ir = _make_ir()
		start_time = add_to_date(now_datetime(), hours=-4)

		result = start_bedside_chart(ir.name, tmpl.name, 60)
		frappe.db.set_value(
			"IPD Bedside Chart", result["chart"], "started_at", start_time,
			update_modified=False,
		)

		missed = compute_missed_observations(result["chart"])
		assert missed["missed_count"] > 0
		assert missed["total_expected"] > missed["total_recorded"]


# ── Severity Classification Tests ──────────────────────────────────


class TestOverdueSeverity:
	def test_warning_severity(self, admin_session):
		from alcura_ipd_ext.services.observation_trend_service import classify_overdue_severity

		assert classify_overdue_severity(30, 60) == "Warning"

	def test_escalation_severity(self, admin_session):
		from alcura_ipd_ext.services.observation_trend_service import classify_overdue_severity

		assert classify_overdue_severity(120, 60) == "Escalation"

	def test_critical_severity(self, admin_session):
		from alcura_ipd_ext.services.observation_trend_service import classify_overdue_severity

		assert classify_overdue_severity(200, 60) == "Critical"

	def test_not_overdue(self, admin_session):
		from alcura_ipd_ext.services.observation_trend_service import classify_overdue_severity

		assert classify_overdue_severity(0, 60) is None


# ── Dashboard Summary Tests ─────────────────────────────────────────


class TestDashboardSummary:
	def test_returns_chart_summaries(self, admin_session):
		from alcura_ipd_ext.services.observation_trend_service import get_dashboard_summary

		_start_chart_and_record("Dash Vitals", 60, 2)
		summary = get_dashboard_summary()
		assert len(summary) > 0
		assert all("next_due_at" in s for s in summary)
