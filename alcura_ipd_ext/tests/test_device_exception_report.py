"""Tests for US-N3: Device Observation Exception Report.

Covers: connectivity failure collection, missing observation detection,
unacknowledged abnormal detection, filter behaviour, and report output.
"""

from __future__ import annotations

import frappe
import pytest
from frappe.utils import add_to_date, now_datetime, today


# ── Helpers ──────────────────────────────────────────────────────────


def _get_or_create_company(name="Test Hospital N3", abbr="TN3"):
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


def _make_patient(suffix="N3"):
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


def _make_ward(suffix="A", company=None):
	company = company or _get_or_create_company()
	ward_code = f"DE{suffix}"
	name = f"{frappe.db.get_value('Company', company, 'abbr')}-{ward_code}"
	if frappe.db.exists("Hospital Ward", name):
		return frappe.get_doc("Hospital Ward", name)
	doc = frappe.get_doc({
		"doctype": "Hospital Ward",
		"ward_code": ward_code,
		"ward_name": f"Device Ward {suffix}",
		"company": company,
		"is_active": 1,
		"classification": "ICU",
	})
	doc.insert(ignore_permissions=True)
	return doc


def _make_ir(patient=None, company=None, ward=None):
	patient = patient or _make_patient()
	company = company or _get_or_create_company()
	doc = frappe.get_doc({
		"doctype": "Inpatient Record",
		"patient": patient,
		"company": company,
		"status": "Admitted",
		"scheduled_date": today(),
	})
	doc.insert(ignore_permissions=True)
	if ward:
		frappe.db.set_value(
			"Inpatient Record", doc.name,
			"custom_current_ward", ward,
			update_modified=False,
		)
	return doc


def _make_error_feed(patient=None, ir_name=None, device_type="Dozee"):
	feed = frappe.get_doc({
		"doctype": "Device Observation Feed",
		"source_device_type": device_type,
		"source_device_id": "DEV-001",
		"patient": patient,
		"inpatient_record": ir_name,
		"received_at": now_datetime(),
		"status": "Error",
		"error_message": "Connection timeout",
	})
	feed.insert(ignore_permissions=True)
	return feed


def _make_chart_template(name="N3 ICU Vitals"):
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
				"parameter_name": "HR",
				"parameter_type": "Numeric",
				"uom": "bpm",
				"is_mandatory": 1,
				"display_order": 10,
				"critical_low": 50,
				"critical_high": 130,
			},
		],
	})
	doc.insert(ignore_permissions=True)
	return doc


def _make_device_mapping(chart_template, device_type="Dozee"):
	autoname = f"{device_type}-{chart_template}"
	if frappe.db.exists("Device Observation Mapping", autoname):
		return frappe.get_doc("Device Observation Mapping", autoname)
	doc = frappe.get_doc({
		"doctype": "Device Observation Mapping",
		"source_device_type": device_type,
		"chart_template": chart_template,
		"is_active": 1,
		"mappings": [
			{
				"device_parameter": "heart_rate",
				"chart_parameter": "HR",
				"unit_conversion_factor": 1.0,
			},
		],
	})
	doc.insert(ignore_permissions=True)
	return doc


# ── Connectivity Failure Tests ───────────────────────────────────────


class TestConnectivityFailures:

	def test_error_feed_collected(self, admin_session):
		from alcura_ipd_ext.services.device_exception_service import get_exceptions

		company = _get_or_create_company()
		patient = _make_patient("N3CF")
		ir = _make_ir(patient=patient, company=company)
		feed = _make_error_feed(patient=patient, ir_name=ir.name)

		rows = get_exceptions(
			from_date=today(),
			to_date=today(),
			exception_type="Connectivity Failure",
		)
		matching = [r for r in rows if r["source_name"] == feed.name]
		assert len(matching) == 1
		assert matching[0]["device_type"] == "Dozee"
		assert "timeout" in matching[0]["description"].lower()

	def test_device_type_filter(self, admin_session):
		from alcura_ipd_ext.services.device_exception_service import get_exceptions

		company = _get_or_create_company()
		patient = _make_patient("N3DT")
		ir = _make_ir(patient=patient, company=company)
		_make_error_feed(patient=patient, ir_name=ir.name, device_type="Dozee")
		_make_error_feed(patient=patient, ir_name=ir.name, device_type="Philips")

		rows = get_exceptions(
			from_date=today(),
			to_date=today(),
			exception_type="Connectivity Failure",
			device_type="Dozee",
		)
		for r in rows:
			assert r["device_type"] == "Dozee"

	def test_empty_date_range(self, admin_session):
		from alcura_ipd_ext.services.device_exception_service import get_exceptions

		rows = get_exceptions(
			from_date="2020-01-01",
			to_date="2020-01-01",
			exception_type="Connectivity Failure",
		)
		assert isinstance(rows, list)


# ── Missing Observation Tests ────────────────────────────────────────


class TestMissingObservations:

	def test_missing_slots_detected(self, admin_session):
		from alcura_ipd_ext.services.device_exception_service import get_exceptions

		company = _get_or_create_company()
		ward = _make_ward("MO", company)
		patient = _make_patient("N3MO")
		ir = _make_ir(patient=patient, company=company, ward=ward.name)

		template = _make_chart_template("N3 MO Vitals")
		_make_device_mapping(template.name, "Dozee")

		# Create a chart started 3 hours ago with 60-min frequency -> expect ~3 slots
		chart = frappe.get_doc({
			"doctype": "IPD Bedside Chart",
			"patient": patient,
			"inpatient_record": ir.name,
			"chart_template": template.name,
			"frequency_minutes": 60,
			"status": "Active",
			"started_at": add_to_date(now_datetime(), hours=-3),
			"source_profile": "ICU Monitor",
			"ward": ward.name,
		})
		chart.insert(ignore_permissions=True)

		rows = get_exceptions(
			from_date=today(),
			to_date=today(),
			exception_type="Missing Observation",
		)
		matching = [r for r in rows if r["source_name"] == chart.name]
		assert len(matching) >= 1
		assert matching[0]["exception_type"] == "Missing Observation"


# ── Unacknowledged Abnormal Tests ────────────────────────────────────


class TestUnacknowledgedAbnormals:

	def test_critical_device_entry_without_followup(self, admin_session):
		from alcura_ipd_ext.services.device_exception_service import get_exceptions

		company = _get_or_create_company()
		ward = _make_ward("UA", company)
		patient = _make_patient("N3UA")
		ir = _make_ir(patient=patient, company=company, ward=ward.name)

		template = _make_chart_template("N3 UA Vitals")
		_make_device_mapping(template.name, "Dozee")

		chart = frappe.get_doc({
			"doctype": "IPD Bedside Chart",
			"patient": patient,
			"inpatient_record": ir.name,
			"chart_template": template.name,
			"frequency_minutes": 60,
			"status": "Active",
			"started_at": add_to_date(now_datetime(), hours=-2),
			"ward": ward.name,
		})
		chart.insert(ignore_permissions=True)

		# Create a device-generated entry with a critical observation
		entry = frappe.get_doc({
			"doctype": "IPD Chart Entry",
			"bedside_chart": chart.name,
			"entry_datetime": add_to_date(now_datetime(), hours=-1),
			"is_device_generated": 1,
			"observations": [
				{
					"parameter_name": "HR",
					"numeric_value": 150,  # above critical_high=130
					"uom": "bpm",
				},
			],
		})
		entry.insert(ignore_permissions=True)

		# Mark observation as critical manually (normally done by controller)
		frappe.db.set_value(
			"IPD Chart Observation",
			{"parent": entry.name, "parameter_name": "HR"},
			"is_critical",
			1,
			update_modified=False,
		)

		rows = get_exceptions(
			from_date=today(),
			to_date=today(),
			exception_type="Unacknowledged Abnormal",
		)
		matching = [r for r in rows if r["source_name"] == entry.name]
		assert len(matching) >= 1
		assert "HR" in matching[0]["parameter"]

	def test_acknowledged_critical_excluded(self, admin_session):
		from alcura_ipd_ext.services.device_exception_service import get_exceptions

		company = _get_or_create_company()
		ward = _make_ward("AE", company)
		patient = _make_patient("N3AE")
		ir = _make_ir(patient=patient, company=company, ward=ward.name)

		template = _make_chart_template("N3 AE Vitals")

		chart = frappe.get_doc({
			"doctype": "IPD Bedside Chart",
			"patient": patient,
			"inpatient_record": ir.name,
			"chart_template": template.name,
			"frequency_minutes": 60,
			"status": "Active",
			"started_at": add_to_date(now_datetime(), hours=-2),
			"ward": ward.name,
		})
		chart.insert(ignore_permissions=True)

		critical_time = add_to_date(now_datetime(), hours=-1)

		device_entry = frappe.get_doc({
			"doctype": "IPD Chart Entry",
			"bedside_chart": chart.name,
			"entry_datetime": critical_time,
			"is_device_generated": 1,
			"observations": [
				{"parameter_name": "HR", "numeric_value": 150, "uom": "bpm"},
			],
		})
		device_entry.insert(ignore_permissions=True)
		frappe.db.set_value(
			"IPD Chart Observation",
			{"parent": device_entry.name, "parameter_name": "HR"},
			"is_critical", 1, update_modified=False,
		)

		# Create a follow-up manual entry within ack window
		followup = frappe.get_doc({
			"doctype": "IPD Chart Entry",
			"bedside_chart": chart.name,
			"entry_datetime": add_to_date(critical_time, minutes=10),
			"is_device_generated": 0,
			"observations": [
				{"parameter_name": "HR", "numeric_value": 85, "uom": "bpm"},
			],
		})
		followup.insert(ignore_permissions=True)

		rows = get_exceptions(
			from_date=today(),
			to_date=today(),
			exception_type="Unacknowledged Abnormal",
		)
		matching = [r for r in rows if r["source_name"] == device_entry.name]
		assert len(matching) == 0


# ── Exception Summary Tests ─────────────────────────────────────────


class TestExceptionSummary:

	def test_summary_counts(self, admin_session):
		from alcura_ipd_ext.services.device_exception_service import get_exception_summary

		rows = [
			{"exception_type": "Connectivity Failure"},
			{"exception_type": "Connectivity Failure"},
			{"exception_type": "Missing Observation"},
		]
		summary = get_exception_summary(rows)
		assert summary["Connectivity Failure"] == 2
		assert summary["Missing Observation"] == 1


# ── Report Output Tests ──────────────────────────────────────────────


class TestDeviceObservationExceptionReport:

	def test_report_returns_five_tuple(self, admin_session):
		from alcura_ipd_ext.alcura_ipd_extensions.report.device_observation_exception.device_observation_exception import (
			execute,
		)

		result = execute({"from_date": "2020-01-01", "to_date": "2020-01-01"})
		assert len(result) == 5

	def test_report_columns(self, admin_session):
		from alcura_ipd_ext.alcura_ipd_extensions.report.device_observation_exception.device_observation_exception import (
			_get_columns,
		)

		col_names = [c["fieldname"] for c in _get_columns()]
		assert "exception_type" in col_names
		assert "device_type" in col_names
		assert "chart" in col_names
		assert "parameter" in col_names

	def test_report_chart_generated(self, admin_session):
		from alcura_ipd_ext.alcura_ipd_extensions.report.device_observation_exception.device_observation_exception import (
			execute,
		)

		company = _get_or_create_company()
		patient = _make_patient("N3CH")
		ir = _make_ir(patient=patient, company=company)
		_make_error_feed(patient=patient, ir_name=ir.name)

		result = execute({"from_date": today(), "to_date": today()})
		_, data, _, chart, summary = result

		assert len(data) >= 1
		assert chart is not None
		assert chart["type"] == "bar"
		assert len(summary) >= 1
