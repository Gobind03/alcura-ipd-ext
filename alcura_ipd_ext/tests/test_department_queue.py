"""Tests for department queue data endpoints (US-F4).

Covers queue filtering, SLA color band enrichment, and empty queue handling.
"""

from __future__ import annotations

import frappe
import pytest


def _ensure_company(name="_Test Company"):
	if not frappe.db.exists("Company", name):
		doc = frappe.get_doc({
			"doctype": "Company",
			"company_name": name,
			"abbr": "TC",
			"default_currency": "INR",
			"country": "India",
		})
		doc.insert(ignore_permissions=True)
	return name


def _ensure_patient(name="_Test Queue Patient"):
	if frappe.db.exists("Patient", {"patient_name": name}):
		return frappe.db.get_value("Patient", {"patient_name": name})
	doc = frappe.get_doc({
		"doctype": "Patient",
		"first_name": name,
		"sex": "Male",
	})
	doc.insert(ignore_permissions=True)
	return doc.name


def _ensure_ir(patient, company):
	existing = frappe.db.get_value(
		"Inpatient Record",
		{"patient": patient, "status": "Admitted"},
	)
	if existing:
		return existing
	doc = frappe.get_doc({
		"doctype": "Inpatient Record",
		"patient": patient,
		"company": company,
		"status": "Admitted",
		"scheduled_date": frappe.utils.today(),
	})
	doc.insert(ignore_permissions=True)
	frappe.db.set_value("Inpatient Record", doc.name, "status", "Admitted")
	return doc.name


class TestPharmacyQueue:
	def test_pharmacy_queue_returns_medication_orders(self, admin_session):
		from alcura_ipd_ext.api.department_queue import get_pharmacy_queue
		from alcura_ipd_ext.services.clinical_order_service import create_order

		company = _ensure_company()
		patient = _ensure_patient()
		ir = _ensure_ir(patient, company)

		create_order(
			order_type="Medication",
			patient=patient,
			inpatient_record=ir,
			company=company,
			medication_name="Queue Test Med",
		)

		result = get_pharmacy_queue()
		assert isinstance(result, list)
		med_orders = [o for o in result if o.get("medication_name") == "Queue Test Med"]
		assert len(med_orders) >= 1

	def test_pharmacy_queue_has_sla_color(self, admin_session):
		from alcura_ipd_ext.api.department_queue import get_pharmacy_queue

		result = get_pharmacy_queue()
		for order in result:
			assert "sla_color" in order
			assert "elapsed_minutes" in order

	def test_empty_pharmacy_queue(self, admin_session):
		from alcura_ipd_ext.api.department_queue import get_pharmacy_queue

		result = get_pharmacy_queue(ward="NONEXISTENT_WARD")
		assert result == []


class TestLabQueue:
	def test_lab_queue_returns_lab_orders(self, admin_session):
		from alcura_ipd_ext.api.department_queue import get_lab_queue
		from alcura_ipd_ext.services.clinical_order_service import create_order

		company = _ensure_company()
		patient = _ensure_patient()
		ir = _ensure_ir(patient, company)

		create_order(
			order_type="Lab Test",
			patient=patient,
			inpatient_record=ir,
			company=company,
			lab_test_name="Queue Test CBC",
		)

		result = get_lab_queue()
		assert isinstance(result, list)
		lab_orders = [o for o in result if o.get("lab_test_name") == "Queue Test CBC"]
		assert len(lab_orders) >= 1


class TestNurseStationQueue:
	def test_nurse_queue_returns_all_types(self, admin_session):
		from alcura_ipd_ext.api.department_queue import get_nurse_station_queue
		from alcura_ipd_ext.services.clinical_order_service import create_order

		company = _ensure_company()
		patient = _ensure_patient()
		ir = _ensure_ir(patient, company)

		create_order(
			order_type="Medication",
			patient=patient,
			inpatient_record=ir,
			company=company,
			medication_name="Nurse Queue Med",
		)
		create_order(
			order_type="Lab Test",
			patient=patient,
			inpatient_record=ir,
			company=company,
			lab_test_name="Nurse Queue Lab",
		)

		result = get_nurse_station_queue()
		assert isinstance(result, list)
		# Both types should appear
		types = {o.get("order_type") for o in result}
		assert "Medication" in types
		assert "Lab Test" in types


class TestSLAColorBands:
	def test_sla_color_grey_when_no_target(self, admin_session):
		from alcura_ipd_ext.api.department_queue import _enrich_with_sla

		orders = [{"ordered_at": frappe.utils.now_datetime()}]
		enriched = _enrich_with_sla(orders)
		assert enriched[0]["sla_color"] == "grey"

	def test_sla_color_red_when_breached(self, admin_session):
		from alcura_ipd_ext.api.department_queue import _enrich_with_sla
		from frappe.utils import add_to_date, now_datetime

		orders = [{
			"ordered_at": add_to_date(now_datetime(), minutes=-60),
			"current_sla_target_at": add_to_date(now_datetime(), minutes=-10),
			"is_sla_breached": 1,
		}]
		enriched = _enrich_with_sla(orders)
		assert enriched[0]["sla_color"] == "red"
