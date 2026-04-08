"""Tests for device observation feed service — ingestion, mapping, idempotency,
validation workflow, and alert logic (US-H3)."""

from __future__ import annotations

import frappe
import pytest
from frappe.utils import now_datetime


# ── Helpers ──────────────────────────────────────────────────────────


def _make_chart_template(name: str = "Device Test Vitals") -> "frappe.Document":
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


def _make_mapping(
	device_type: str = "TestDevice",
	template_name: str = "Device Test Vitals",
	requires_validation: bool = False,
) -> "frappe.Document":
	name = f"{device_type}-{template_name}"
	if frappe.db.exists("Device Observation Mapping", name):
		frappe.delete_doc("Device Observation Mapping", name, force=True)

	doc = frappe.get_doc({
		"doctype": "Device Observation Mapping",
		"source_device_type": device_type,
		"chart_template": template_name,
		"is_active": 1,
		"requires_manual_validation": 1 if requires_validation else 0,
		"mappings": [
			{
				"device_parameter": "temp",
				"chart_parameter": "Temperature",
				"unit_conversion_factor": 1.0,
				"unit_conversion_offset": 0.0,
			},
			{
				"device_parameter": "hr",
				"chart_parameter": "Pulse",
				"unit_conversion_factor": 1.0,
				"unit_conversion_offset": 0.0,
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
	if frappe.db.exists("Patient", {"patient_name": "_Test Device Patient"}):
		return frappe.get_doc("Patient", {"patient_name": "_Test Device Patient"})
	p = frappe.get_doc({
		"doctype": "Patient",
		"first_name": "_Test",
		"last_name": "Device Patient",
	})
	p.insert(ignore_permissions=True)
	return p


# ── Ingestion Tests ─────────────────────────────────────────────────


class TestIngestion:
	def test_basic_ingestion(self, admin_session):
		from alcura_ipd_ext.services.device_feed_service import ingest_observation

		tmpl = _make_chart_template()
		_make_mapping("BasicDevice", tmpl.name)
		ir = _make_ir()

		from alcura_ipd_ext.services.charting_service import start_bedside_chart
		start_bedside_chart(ir.name, tmpl.name)

		result = ingest_observation(
			source_device_type="BasicDevice",
			source_device_id="DEV-001",
			inpatient_record=ir.name,
			readings=[
				{"parameter": "temp", "value": 37.2},
				{"parameter": "hr", "value": 78},
			],
		)

		assert result["status"] == "Mapped"
		assert result["chart_entry"] is not None

		entry = frappe.get_doc("IPD Chart Entry", result["chart_entry"])
		assert entry.is_device_generated == 1
		assert entry.device_feed == result["feed_name"]

	def test_no_mapping_returns_error(self, admin_session):
		from alcura_ipd_ext.services.device_feed_service import ingest_observation

		result = ingest_observation(
			source_device_type="UnknownDevice",
			source_device_id="DEV-999",
			readings=[{"parameter": "temp", "value": 37.0}],
		)

		assert result["status"] == "Error"

	def test_out_of_range_detected(self, admin_session):
		from alcura_ipd_ext.services.device_feed_service import ingest_observation

		tmpl = _make_chart_template("OOR Device Vitals")
		_make_mapping("OORDevice", tmpl.name)
		ir = _make_ir()

		from alcura_ipd_ext.services.charting_service import start_bedside_chart
		start_bedside_chart(ir.name, tmpl.name)

		result = ingest_observation(
			source_device_type="OORDevice",
			source_device_id="DEV-002",
			inpatient_record=ir.name,
			readings=[
				{"parameter": "temp", "value": 40.5},
				{"parameter": "hr", "value": 78},
			],
		)

		assert "Temperature" in result["alerts"]


# ── Idempotency Tests ───────────────────────────────────────────────


class TestIdempotency:
	def test_duplicate_key_returns_existing(self, admin_session):
		from alcura_ipd_ext.services.device_feed_service import ingest_observation

		tmpl = _make_chart_template("Idem Device Vitals")
		_make_mapping("IdemDevice", tmpl.name)

		result1 = ingest_observation(
			source_device_type="IdemDevice",
			source_device_id="DEV-003",
			readings=[{"parameter": "temp", "value": 37.0}],
			idempotency_key="unique-key-123",
		)

		result2 = ingest_observation(
			source_device_type="IdemDevice",
			source_device_id="DEV-003",
			readings=[{"parameter": "temp", "value": 38.0}],
			idempotency_key="unique-key-123",
		)

		assert result2.get("duplicate") is True
		assert result2["feed_name"] == result1["feed_name"]


# ── Validation Workflow Tests ───────────────────────────────────────


class TestValidationWorkflow:
	def test_manual_validation_required(self, admin_session):
		from alcura_ipd_ext.services.device_feed_service import ingest_observation

		tmpl = _make_chart_template("Val Device Vitals")
		_make_mapping("ValDevice", tmpl.name, requires_validation=True)

		result = ingest_observation(
			source_device_type="ValDevice",
			source_device_id="DEV-004",
			readings=[{"parameter": "temp", "value": 37.0}],
		)

		assert result["status"] == "Received"
		assert result["chart_entry"] is None

	def test_validate_feed(self, admin_session):
		from alcura_ipd_ext.services.device_feed_service import (
			ingest_observation,
			validate_feed,
		)

		tmpl = _make_chart_template("ValAct Device Vitals")
		_make_mapping("ValActDevice", tmpl.name, requires_validation=True)
		ir = _make_ir()

		from alcura_ipd_ext.services.charting_service import start_bedside_chart
		start_bedside_chart(ir.name, tmpl.name)

		result = ingest_observation(
			source_device_type="ValActDevice",
			source_device_id="DEV-005",
			inpatient_record=ir.name,
			readings=[{"parameter": "temp", "value": 37.0}],
		)

		val_result = validate_feed(result["feed_name"], "validate")
		assert val_result["status"] == "Validated"

	def test_reject_feed(self, admin_session):
		from alcura_ipd_ext.services.device_feed_service import (
			ingest_observation,
			validate_feed,
		)

		tmpl = _make_chart_template("Rej Device Vitals")
		_make_mapping("RejDevice", tmpl.name, requires_validation=True)

		result = ingest_observation(
			source_device_type="RejDevice",
			source_device_id="DEV-006",
			readings=[{"parameter": "temp", "value": 37.0}],
		)

		val_result = validate_feed(result["feed_name"], "reject")
		assert val_result["status"] == "Rejected"


# ── Mapping Tests ───────────────────────────────────────────────────


class TestParameterMapping:
	def test_unit_conversion(self, admin_session):
		from alcura_ipd_ext.services.device_feed_service import map_readings

		tmpl = _make_chart_template("Conv Device Vitals")
		mapping = _make_mapping("ConvDevice", tmpl.name)
		mapping.mappings[0].unit_conversion_factor = 1.8
		mapping.mappings[0].unit_conversion_offset = 32.0
		mapping.save(ignore_permissions=True)

		result = map_readings(
			[{"parameter": "temp", "value": 37.0}],
			mapping,
		)

		assert len(result) == 1
		expected = 37.0 * 1.8 + 32.0
		assert result[0]["mapped_value"] == pytest.approx(expected, abs=0.01)

	def test_unmapped_parameter_passthrough(self, admin_session):
		from alcura_ipd_ext.services.device_feed_service import map_readings

		tmpl = _make_chart_template("Pass Device Vitals")
		mapping = _make_mapping("PassDevice", tmpl.name)

		result = map_readings(
			[{"parameter": "unknown_param", "value": 42}],
			mapping,
		)

		assert len(result) == 1
		assert result[0]["parameter_name"] == "unknown_param"
		assert result[0]["mapped_value"] is None


class TestMappingValidation:
	def test_rejects_empty_mappings(self, admin_session):
		tmpl = _make_chart_template("Empty Map Vitals")
		doc = frappe.get_doc({
			"doctype": "Device Observation Mapping",
			"source_device_type": "EmptyMapDevice",
			"chart_template": tmpl.name,
			"is_active": 1,
		})
		with pytest.raises(frappe.ValidationError, match="at least one"):
			doc.insert(ignore_permissions=True)

	def test_rejects_duplicate_device_params(self, admin_session):
		tmpl = _make_chart_template("Dup Map Vitals")
		doc = frappe.get_doc({
			"doctype": "Device Observation Mapping",
			"source_device_type": "DupMapDevice",
			"chart_template": tmpl.name,
			"is_active": 1,
			"mappings": [
				{"device_parameter": "temp", "chart_parameter": "Temperature"},
				{"device_parameter": "temp", "chart_parameter": "Pulse"},
			],
		})
		with pytest.raises(frappe.ValidationError, match="Duplicate"):
			doc.insert(ignore_permissions=True)
