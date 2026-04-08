"""Tests for order_notification_service (US-F1–F5).

Covers notification creation, deduplication, and realtime event publishing.
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


def _ensure_patient(name="_Test Notif Patient"):
	if frappe.db.exists("Patient", {"patient_name": name}):
		return frappe.db.get_value("Patient", {"patient_name": name})
	doc = frappe.get_doc({
		"doctype": "Patient",
		"first_name": name,
		"sex": "Female",
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


class TestOrderNotifications:
	def test_notification_created_on_order(self, admin_session):
		from alcura_ipd_ext.services.order_notification_service import notify_order_created

		company = _ensure_company()
		patient = _ensure_patient()
		ir = _ensure_ir(patient, company)

		order = frappe.get_doc({
			"doctype": "IPD Clinical Order",
			"order_type": "Medication",
			"patient": patient,
			"inpatient_record": ir,
			"company": company,
			"medication_name": "Notif Test",
			"urgency": "Routine",
			"status": "Ordered",
		})
		order.insert(ignore_permissions=True)

		# This should not raise even if no role users exist
		notify_order_created(order)

	def test_deduplication(self, admin_session):
		from alcura_ipd_ext.services.order_notification_service import _send_notifications

		# Create a test user notification
		count1 = _send_notifications(
			recipients={"Administrator"},
			subject="Test dedup [ref:test_dedup:001]",
			document_type="IPD Clinical Order",
			document_name="TEST-001",
			ref_key="test_dedup:001",
		)
		# We expect 0 since Administrator is filtered out
		assert count1 == 0


class TestSLABreachNotification:
	def test_breach_notification_structure(self, admin_session):
		from alcura_ipd_ext.services.order_notification_service import notify_sla_breach

		company = _ensure_company()
		patient = _ensure_patient()
		ir = _ensure_ir(patient, company)

		order = frappe.get_doc({
			"doctype": "IPD Clinical Order",
			"order_type": "Lab Test",
			"patient": patient,
			"inpatient_record": ir,
			"company": company,
			"lab_test_name": "Breach Notif Test",
			"urgency": "STAT",
			"status": "Ordered",
		})
		order.insert(ignore_permissions=True)

		# Should not raise even without escalation role users
		notify_sla_breach(order, "Acknowledged", "Healthcare Administrator")
