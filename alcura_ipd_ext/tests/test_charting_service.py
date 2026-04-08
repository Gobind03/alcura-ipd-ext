"""Tests for the charting service — chart creation, entry recording, correction flow,
template validation, and overdue detection (US-E4)."""

from __future__ import annotations

import frappe
import pytest
from frappe.utils import add_to_date, now_datetime


# ── Helpers ──────────────────────────────────────────────────────────


def _make_chart_template(
	name: str = "Test Vitals",
	chart_type: str = "Vitals",
	freq: int = 240,
	params: list[dict] | None = None,
) -> "frappe.Document":
	if frappe.db.exists("IPD Chart Template", name):
		return frappe.get_doc("IPD Chart Template", name)

	doc = frappe.get_doc({
		"doctype": "IPD Chart Template",
		"template_name": name,
		"chart_type": chart_type,
		"default_frequency_minutes": freq,
		"is_active": 1,
		"parameters": params or [
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
	"""Create a minimal Inpatient Record for testing."""
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
	if frappe.db.exists("Patient", {"patient_name": "_Test Chart Patient"}):
		return frappe.get_doc("Patient", {"patient_name": "_Test Chart Patient"})
	p = frappe.get_doc({
		"doctype": "Patient",
		"first_name": "_Test",
		"last_name": "Chart Patient",
	})
	p.insert(ignore_permissions=True)
	return p


# ── Template Validation Tests ────────────────────────────────────────


class TestChartTemplateValidation:
	def test_template_requires_parameters(self, admin_session):
		doc = frappe.get_doc({
			"doctype": "IPD Chart Template",
			"template_name": "Empty Template",
			"chart_type": "Vitals",
			"default_frequency_minutes": 60,
			"is_active": 1,
		})
		with pytest.raises(frappe.ValidationError):
			doc.insert(ignore_permissions=True)

	def test_template_rejects_duplicate_params(self, admin_session):
		doc = frappe.get_doc({
			"doctype": "IPD Chart Template",
			"template_name": "Dup Params",
			"chart_type": "Vitals",
			"default_frequency_minutes": 60,
			"is_active": 1,
			"parameters": [
				{"parameter_name": "Pulse", "parameter_type": "Numeric", "uom": "bpm", "display_order": 10},
				{"parameter_name": "Pulse", "parameter_type": "Numeric", "uom": "bpm", "display_order": 20},
			],
		})
		with pytest.raises(frappe.ValidationError, match="Duplicate"):
			doc.insert(ignore_permissions=True)

	def test_select_param_requires_options(self, admin_session):
		doc = frappe.get_doc({
			"doctype": "IPD Chart Template",
			"template_name": "Select No Opts",
			"chart_type": "Pain",
			"default_frequency_minutes": 60,
			"is_active": 1,
			"parameters": [
				{"parameter_name": "Type", "parameter_type": "Select", "display_order": 10},
			],
		})
		with pytest.raises(frappe.ValidationError, match="no options"):
			doc.insert(ignore_permissions=True)

	def test_valid_template_creation(self, admin_session):
		template = _make_chart_template("Valid Template")
		assert template.name == "Valid Template"
		assert len(template.parameters) == 2


# ── Chart Lifecycle Tests ────────────────────────────────────────────


class TestBedsideChartLifecycle:
	def test_start_chart(self, admin_session):
		from alcura_ipd_ext.services.charting_service import start_bedside_chart

		template = _make_chart_template("Lifecycle Vitals")
		ir = _make_ir()

		result = start_bedside_chart(ir.name, template.name)
		assert result["status"] == "Active"
		assert result["chart_type"] == "Vitals"

	def test_duplicate_chart_blocked(self, admin_session):
		from alcura_ipd_ext.services.charting_service import start_bedside_chart

		template = _make_chart_template("Dup Chart Vitals")
		ir = _make_ir()

		start_bedside_chart(ir.name, template.name)

		with pytest.raises(frappe.ValidationError, match="active chart already exists"):
			start_bedside_chart(ir.name, template.name)

	def test_chart_status_transitions(self, admin_session):
		from alcura_ipd_ext.services.charting_service import start_bedside_chart

		template = _make_chart_template("Transition Vitals")
		ir = _make_ir()

		result = start_bedside_chart(ir.name, template.name)
		chart = frappe.get_doc("IPD Bedside Chart", result["chart"])

		chart.status = "Paused"
		chart.save(ignore_permissions=True)
		assert chart.status == "Paused"

		chart.status = "Active"
		chart.save(ignore_permissions=True)
		assert chart.status == "Active"

		chart.status = "Discontinued"
		chart.save(ignore_permissions=True)
		assert chart.status == "Discontinued"
		assert chart.discontinued_at is not None
		assert chart.discontinued_by is not None


# ── Chart Entry Tests ────────────────────────────────────────────────


class TestChartEntryRecording:
	def test_record_entry(self, admin_session):
		from alcura_ipd_ext.services.charting_service import (
			record_chart_entry,
			start_bedside_chart,
		)

		template = _make_chart_template("Entry Vitals")
		ir = _make_ir()
		chart_result = start_bedside_chart(ir.name, template.name)

		entry_result = record_chart_entry(
			bedside_chart=chart_result["chart"],
			observations=[
				{"parameter_name": "Temperature", "numeric_value": 37.2, "uom": "°C"},
				{"parameter_name": "Pulse", "numeric_value": 78, "uom": "bpm"},
			],
		)

		assert entry_result["chart_type"] == "Vitals"
		assert not entry_result["has_critical"]

		chart = frappe.get_doc("IPD Bedside Chart", chart_result["chart"])
		assert chart.total_entries == 1
		assert chart.last_entry_at is not None

	def test_critical_observation_detection(self, admin_session):
		from alcura_ipd_ext.services.charting_service import (
			record_chart_entry,
			start_bedside_chart,
		)

		template = _make_chart_template("Critical Vitals")
		ir = _make_ir()
		chart_result = start_bedside_chart(ir.name, template.name)

		entry_result = record_chart_entry(
			bedside_chart=chart_result["chart"],
			observations=[
				{"parameter_name": "Temperature", "numeric_value": 40.5, "uom": "°C"},
				{"parameter_name": "Pulse", "numeric_value": 78, "uom": "bpm"},
			],
		)

		assert entry_result["has_critical"]

		entry = frappe.get_doc("IPD Chart Entry", entry_result["entry"])
		critical_obs = [o for o in entry.observations if o.is_critical]
		assert len(critical_obs) == 1
		assert critical_obs[0].parameter_name == "Temperature"

	def test_entry_blocked_for_discontinued_chart(self, admin_session):
		from alcura_ipd_ext.services.charting_service import start_bedside_chart

		template = _make_chart_template("Disc Entry Vitals")
		ir = _make_ir()
		chart_result = start_bedside_chart(ir.name, template.name)

		chart = frappe.get_doc("IPD Bedside Chart", chart_result["chart"])
		chart.status = "Discontinued"
		chart.save(ignore_permissions=True)

		entry = frappe.get_doc({
			"doctype": "IPD Chart Entry",
			"bedside_chart": chart.name,
			"entry_datetime": now_datetime(),
			"observations": [
				{"parameter_name": "Temperature", "numeric_value": 37.0, "uom": "°C"},
			],
		})
		with pytest.raises(frappe.ValidationError, match="Discontinued"):
			entry.insert(ignore_permissions=True)


# ── Correction Flow Tests ────────────────────────────────────────────


class TestCorrectionFlow:
	def test_create_correction(self, admin_session):
		from alcura_ipd_ext.services.charting_service import (
			create_correction_entry,
			record_chart_entry,
			start_bedside_chart,
		)

		template = _make_chart_template("Correction Vitals")
		ir = _make_ir()
		chart_result = start_bedside_chart(ir.name, template.name)

		entry_result = record_chart_entry(
			bedside_chart=chart_result["chart"],
			observations=[
				{"parameter_name": "Temperature", "numeric_value": 37.2, "uom": "°C"},
				{"parameter_name": "Pulse", "numeric_value": 78, "uom": "bpm"},
			],
		)

		correction = create_correction_entry(
			entry_result["entry"], "Wrong temperature reading"
		)

		original = frappe.get_doc("IPD Chart Entry", entry_result["entry"])
		assert original.status == "Corrected"

		new_entry = frappe.get_doc("IPD Chart Entry", correction["name"])
		assert new_entry.is_correction
		assert new_entry.corrects_entry == entry_result["entry"]

	def test_double_correction_blocked(self, admin_session):
		from alcura_ipd_ext.services.charting_service import (
			create_correction_entry,
			record_chart_entry,
			start_bedside_chart,
		)

		template = _make_chart_template("DblCorr Vitals")
		ir = _make_ir()
		chart_result = start_bedside_chart(ir.name, template.name)

		entry_result = record_chart_entry(
			bedside_chart=chart_result["chart"],
			observations=[
				{"parameter_name": "Temperature", "numeric_value": 37.2, "uom": "°C"},
				{"parameter_name": "Pulse", "numeric_value": 78, "uom": "bpm"},
			],
		)

		create_correction_entry(entry_result["entry"], "First correction")

		with pytest.raises(frappe.ValidationError, match="already been corrected"):
			create_correction_entry(entry_result["entry"], "Second correction")

	def test_correction_requires_reason(self, admin_session):
		from alcura_ipd_ext.services.charting_service import (
			record_chart_entry,
			start_bedside_chart,
		)

		template = _make_chart_template("NoReason Vitals")
		ir = _make_ir()
		chart_result = start_bedside_chart(ir.name, template.name)

		entry_result = record_chart_entry(
			bedside_chart=chart_result["chart"],
			observations=[
				{"parameter_name": "Temperature", "numeric_value": 37.2, "uom": "°C"},
				{"parameter_name": "Pulse", "numeric_value": 78, "uom": "bpm"},
			],
		)

		entry = frappe.get_doc({
			"doctype": "IPD Chart Entry",
			"bedside_chart": chart_result["chart"],
			"entry_datetime": now_datetime(),
			"is_correction": 1,
			"corrects_entry": entry_result["entry"],
			"correction_reason": "",
			"observations": [
				{"parameter_name": "Temperature", "numeric_value": 37.0, "uom": "°C"},
			],
		})
		with pytest.raises(frappe.ValidationError, match="correction reason"):
			entry.insert(ignore_permissions=True)
