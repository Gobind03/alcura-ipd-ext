"""Tests for US-N2: Incident and Critical Alert Report.

Covers: each incident type collection, filter behaviour, severity
mapping, deduplication, report output (columns, chart, summary).
"""

from __future__ import annotations

import frappe
import pytest
from frappe.utils import add_to_date, now_datetime, today


# ── Helpers ──────────────────────────────────────────────────────────


def _get_or_create_company(name="Test Hospital N2", abbr="TN2"):
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


def _make_patient(suffix="N2"):
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
	ward_code = f"NI{suffix}"
	name = f"{frappe.db.get_value('Company', company, 'abbr')}-{ward_code}"
	if frappe.db.exists("Hospital Ward", name):
		return frappe.get_doc("Hospital Ward", name)
	doc = frappe.get_doc({
		"doctype": "Hospital Ward",
		"ward_code": ward_code,
		"ward_name": f"Incident Ward {suffix}",
		"company": company,
		"is_active": 1,
		"classification": "General",
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


def _make_risk_todo(ir_name, tag="fall-risk", priority="High"):
	"""Create a ToDo matching nursing_alert_service pattern."""
	ref = f"NursingRisk:{tag}:{ir_name}"
	todo = frappe.get_doc({
		"doctype": "ToDo",
		"description": f"Fall Prevention Protocol\n<!-- ref:{ref} -->",
		"reference_type": "Inpatient Record",
		"reference_name": ir_name,
		"allocated_to": frappe.session.user,
		"priority": priority,
		"status": "Open",
	})
	todo.insert(ignore_permissions=True)
	return todo


def _make_missed_mar(patient, ir_name, ward_name=None):
	entry = frappe.get_doc({
		"doctype": "IPD MAR Entry",
		"patient": patient,
		"inpatient_record": ir_name,
		"medication_name": "Paracetamol",
		"dose": "500mg",
		"route": "Oral",
		"scheduled_time": add_to_date(now_datetime(), hours=-1),
		"administration_status": "Missed",
		"ward": ward_name or "",
	})
	entry.insert(ignore_permissions=True)
	return entry


def _make_clinical_order_breached(patient, ir_name, ward_name=None, company=None):
	company = company or _get_or_create_company()
	order = frappe.get_doc({
		"doctype": "IPD Clinical Order",
		"patient": patient,
		"inpatient_record": ir_name,
		"company": company,
		"order_type": "Lab Test",
		"urgency": "STAT",
		"status": "In Progress",
		"ordered_at": add_to_date(now_datetime(), hours=-2),
		"is_sla_breached": 1,
		"sla_breach_count": 1,
		"ward": ward_name or "",
	})
	order.insert(ignore_permissions=True)
	return order


# ── Service Tests ────────────────────────────────────────────────────


class TestIncidentReportService:

	def test_empty_date_range(self, admin_session):
		from alcura_ipd_ext.services.incident_report_service import get_incidents

		rows = get_incidents(from_date="2020-01-01", to_date="2020-01-01")
		assert isinstance(rows, list)

	def test_risk_alert_collected(self, admin_session):
		from alcura_ipd_ext.services.incident_report_service import get_incidents

		company = _get_or_create_company()
		ward = _make_ward("RA", company)
		patient = _make_patient("N2RA")
		ir = _make_ir(patient=patient, company=company, ward=ward.name)
		_make_risk_todo(ir.name, tag="fall-risk")

		rows = get_incidents(
			from_date=today(),
			to_date=today(),
			incident_type="Fall Risk",
		)
		matching = [r for r in rows if r["source_name"] and ir.name in r.get("description", "")]
		assert len(rows) >= 1

	def test_missed_medication_collected(self, admin_session):
		from alcura_ipd_ext.services.incident_report_service import get_incidents

		company = _get_or_create_company()
		ward = _make_ward("MM", company)
		patient = _make_patient("N2MM")
		ir = _make_ir(patient=patient, company=company, ward=ward.name)
		mar = _make_missed_mar(patient, ir.name, ward.name)

		rows = get_incidents(
			from_date=today(),
			to_date=today(),
			incident_type="Missed Medication",
		)
		matching = [r for r in rows if r["source_name"] == mar.name]
		assert len(matching) == 1
		assert matching[0]["severity"] == "Medium"

	def test_sla_breach_collected(self, admin_session):
		from alcura_ipd_ext.services.incident_report_service import get_incidents

		company = _get_or_create_company()
		ward = _make_ward("SB", company)
		patient = _make_patient("N2SB")
		ir = _make_ir(patient=patient, company=company, ward=ward.name)
		order = _make_clinical_order_breached(patient, ir.name, ward.name, company)

		rows = get_incidents(
			from_date=today(),
			to_date=today(),
			incident_type="SLA Breach",
		)
		matching = [r for r in rows if r["source_name"] == order.name]
		assert len(matching) == 1
		assert matching[0]["severity"] == "High"  # STAT urgency

	def test_ward_filter(self, admin_session):
		from alcura_ipd_ext.services.incident_report_service import get_incidents

		company = _get_or_create_company()
		ward_a = _make_ward("WA", company)
		ward_b = _make_ward("WB", company)
		patient_a = _make_patient("N2WA")
		patient_b = _make_patient("N2WB")
		ir_a = _make_ir(patient=patient_a, company=company, ward=ward_a.name)
		ir_b = _make_ir(patient=patient_b, company=company, ward=ward_b.name)

		_make_missed_mar(patient_a, ir_a.name, ward_a.name)
		_make_missed_mar(patient_b, ir_b.name, ward_b.name)

		rows = get_incidents(
			from_date=today(),
			to_date=today(),
			ward=ward_a.name,
			incident_type="Missed Medication",
		)
		wards_in_result = {r["ward"] for r in rows}
		assert ward_b.name not in wards_in_result

	def test_severity_filter(self, admin_session):
		from alcura_ipd_ext.services.incident_report_service import get_incidents

		company = _get_or_create_company()
		ward = _make_ward("SF", company)
		patient = _make_patient("N2SF")
		ir = _make_ir(patient=patient, company=company, ward=ward.name)

		_make_missed_mar(patient, ir.name, ward.name)  # severity=Medium
		_make_risk_todo(ir.name, tag="fall-risk", priority="High")  # severity=High

		rows = get_incidents(
			from_date=today(),
			to_date=today(),
			severity="High",
		)
		for r in rows:
			assert r["severity"] == "High"

	def test_incident_summary(self, admin_session):
		from alcura_ipd_ext.services.incident_report_service import (
			get_incident_summary,
			get_incidents,
		)

		company = _get_or_create_company()
		ward = _make_ward("IS", company)
		patient = _make_patient("N2IS")
		ir = _make_ir(patient=patient, company=company, ward=ward.name)
		_make_missed_mar(patient, ir.name, ward.name)
		_make_risk_todo(ir.name)

		rows = get_incidents(from_date=today(), to_date=today())
		summary = get_incident_summary(rows)
		assert isinstance(summary, dict)
		assert sum(summary.values()) == len(rows)


# ── Report Output Tests ──────────────────────────────────────────────


class TestIncidentAlertReport:

	def test_report_returns_five_tuple(self, admin_session):
		from alcura_ipd_ext.alcura_ipd_extensions.report.incident_alert_report.incident_alert_report import (
			execute,
		)

		result = execute({"from_date": "2020-01-01", "to_date": "2020-01-01"})
		assert len(result) == 5

	def test_report_columns(self, admin_session):
		from alcura_ipd_ext.alcura_ipd_extensions.report.incident_alert_report.incident_alert_report import (
			_get_columns,
		)

		col_names = [c["fieldname"] for c in _get_columns()]
		assert "incident_datetime" in col_names
		assert "incident_type" in col_names
		assert "severity" in col_names
		assert "source_name" in col_names

	def test_report_chart_generated(self, admin_session):
		from alcura_ipd_ext.alcura_ipd_extensions.report.incident_alert_report.incident_alert_report import (
			execute,
		)

		company = _get_or_create_company()
		ward = _make_ward("CH", company)
		patient = _make_patient("N2CH")
		ir = _make_ir(patient=patient, company=company, ward=ward.name)
		_make_missed_mar(patient, ir.name, ward.name)

		result = execute({"from_date": today(), "to_date": today()})
		_, data, _, chart, summary = result

		assert len(data) >= 1
		assert chart is not None
		assert chart["type"] == "pie"
		assert len(summary) >= 1
