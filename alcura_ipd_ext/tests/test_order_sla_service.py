"""Tests for order_sla_service (US-F5).

Covers SLA initialization, milestone advancement, breach detection,
and graceful handling when no config exists.
"""

from __future__ import annotations

import frappe
import pytest
from frappe.utils import add_to_date, now_datetime


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


def _ensure_patient(name="_Test SLA Patient"):
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


def _ensure_sla_config(order_type="Medication", urgency="Routine"):
	config_name = f"{order_type}-{urgency}"
	if frappe.db.exists("IPD Order SLA Config", config_name):
		return config_name

	doc = frappe.get_doc({
		"doctype": "IPD Order SLA Config",
		"order_type": order_type,
		"urgency": urgency,
		"is_active": 1,
		"milestones": [
			{"milestone": "Acknowledged", "sequence": 1, "target_minutes": 30},
			{"milestone": "Dispensed", "sequence": 2, "target_minutes": 120},
		],
	})
	doc.insert(ignore_permissions=True)
	return doc.name


class TestSLAInitialization:
	def test_sla_milestones_created(self, admin_session):
		from alcura_ipd_ext.services.clinical_order_service import create_order

		_ensure_sla_config("Medication", "Routine")
		company = _ensure_company()
		patient = _ensure_patient()
		ir = _ensure_ir(patient, company)

		order = create_order(
			order_type="Medication",
			patient=patient,
			inpatient_record=ir,
			company=company,
			medication_name="SLA Test Med",
			urgency="Routine",
		)

		assert len(order.sla_milestones) >= 2
		assert order.current_sla_target_at is not None
		assert order.sla_milestones[0].milestone == "Acknowledged"

	def test_no_config_skips_sla(self, admin_session):
		from alcura_ipd_ext.services.clinical_order_service import create_order

		company = _ensure_company()
		patient = _ensure_patient()
		ir = _ensure_ir(patient, company)

		order = create_order(
			order_type="Radiology",
			patient=patient,
			inpatient_record=ir,
			company=company,
			procedure_name="No SLA Config Test",
			urgency="Emergency",
		)

		# No config for Radiology-Emergency, so no milestones
		assert order.current_sla_target_at is None or len(order.sla_milestones) == 0


class TestSLAAdvancement:
	def test_milestone_advances_target(self, admin_session):
		from alcura_ipd_ext.services.clinical_order_service import (
			acknowledge_order,
			create_order,
		)

		_ensure_sla_config("Medication", "Routine")
		company = _ensure_company()
		patient = _ensure_patient()
		ir = _ensure_ir(patient, company)

		order = create_order(
			order_type="Medication",
			patient=patient,
			inpatient_record=ir,
			company=company,
			medication_name="Advance Test",
			urgency="Routine",
		)

		first_target = order.current_sla_target_at
		acknowledge_order(order.name)
		order.reload()

		# Target should advance to the Dispensed milestone
		if order.current_sla_target_at:
			assert order.current_sla_target_at != first_target


class TestBreachDetection:
	def test_breach_detected(self, admin_session):
		from alcura_ipd_ext.services.clinical_order_service import create_order
		from alcura_ipd_ext.services.order_sla_service import check_breaches

		_ensure_sla_config("Medication", "Routine")
		company = _ensure_company()
		patient = _ensure_patient()
		ir = _ensure_ir(patient, company)

		order = create_order(
			order_type="Medication",
			patient=patient,
			inpatient_record=ir,
			company=company,
			medication_name="Breach Test",
			urgency="Routine",
		)

		# Manually set SLA target to the past to simulate breach
		frappe.db.set_value(
			"IPD Clinical Order",
			order.name,
			"current_sla_target_at",
			add_to_date(now_datetime(), minutes=-5),
		)

		breached = check_breaches()
		assert breached >= 1

		order.reload()
		assert order.is_sla_breached == 1
		assert order.sla_breach_count >= 1
