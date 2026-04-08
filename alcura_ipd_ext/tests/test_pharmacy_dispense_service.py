"""Tests for pharmacy_dispense_service (US-G1).

Covers dispense creation, partial dispense, stock verification,
substitution request/approve/reject, return, and dispense status aggregation.
"""

from __future__ import annotations

import frappe
import pytest


# ── Helpers ──────────────────────────────────────────────────────────


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


def _ensure_patient(name="_Test Dispense Patient"):
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


def _create_medication_order(patient, ir, company, **kwargs):
	from alcura_ipd_ext.services.clinical_order_service import create_order

	defaults = {
		"order_type": "Medication",
		"patient": patient,
		"inpatient_record": ir,
		"company": company,
		"medication_name": "Paracetamol 500mg",
		"dose": "500",
		"dose_uom": "mg",
		"route": "Oral",
		"frequency": "BD",
	}
	defaults.update(kwargs)
	return create_order(**defaults)


# ── Tests ────────────────────────────────────────────────────────────


class TestStockVerification:
	def test_verify_stock_no_bin(self, admin_session):
		from alcura_ipd_ext.services.pharmacy_dispense_service import verify_stock

		result = verify_stock("NONEXISTENT_ITEM_12345")
		assert result["available_qty"] == 0
		assert result["warehouses"] == []

	def test_verify_stock_requires_item_code(self, admin_session):
		from alcura_ipd_ext.services.pharmacy_dispense_service import verify_stock

		with pytest.raises(frappe.ValidationError):
			verify_stock("")


class TestDispenseMedication:
	def test_dispense_full(self, admin_session):
		from alcura_ipd_ext.services.pharmacy_dispense_service import dispense_medication

		company = _ensure_company()
		patient = _ensure_patient()
		ir = _ensure_ir(patient, company)
		order = _create_medication_order(patient, ir, company)

		# Place and acknowledge the order
		from alcura_ipd_ext.services.clinical_order_service import place_order, acknowledge_order

		place_order(order.name)
		acknowledge_order(order.name)

		result = dispense_medication(
			order_name=order.name,
			dispensed_qty=10,
			dispense_type="Full",
		)

		assert result["name"]
		dispense = frappe.get_doc("IPD Dispense Entry", result["name"])
		assert dispense.dispensed_qty == 10
		assert dispense.dispense_type == "Full"
		assert dispense.status == "Dispensed"
		assert dispense.clinical_order == order.name

	def test_dispense_partial(self, admin_session):
		from alcura_ipd_ext.services.pharmacy_dispense_service import (
			dispense_medication,
			update_order_dispense_status,
		)

		company = _ensure_company()
		patient = _ensure_patient("_Test Partial Dispense")
		ir = _ensure_ir(patient, company)
		order = _create_medication_order(patient, ir, company, ordered_qty=20)

		from alcura_ipd_ext.services.clinical_order_service import place_order, acknowledge_order

		place_order(order.name)
		acknowledge_order(order.name)

		# First partial dispense
		dispense_medication(order_name=order.name, dispensed_qty=5, dispense_type="Partial")
		order_doc = frappe.get_doc("IPD Clinical Order", order.name)
		assert order_doc.dispense_status == "Partially Dispensed"
		assert order_doc.total_dispensed_qty == 5

		# Second partial dispense — should become fully dispensed
		dispense_medication(order_name=order.name, dispensed_qty=15, dispense_type="Partial")
		order_doc.reload()
		assert order_doc.dispense_status == "Fully Dispensed"
		assert order_doc.total_dispensed_qty == 20

	def test_dispense_fails_for_cancelled_order(self, admin_session):
		from alcura_ipd_ext.services.pharmacy_dispense_service import dispense_medication

		company = _ensure_company()
		patient = _ensure_patient("_Test Cancel Dispense")
		ir = _ensure_ir(patient, company)
		order = _create_medication_order(patient, ir, company)

		from alcura_ipd_ext.services.clinical_order_service import place_order, cancel_order

		place_order(order.name)
		cancel_order(order.name, reason="Test cancellation")

		with pytest.raises(frappe.ValidationError):
			dispense_medication(order_name=order.name, dispensed_qty=1)

	def test_dispense_fails_for_non_medication(self, admin_session):
		from alcura_ipd_ext.services.pharmacy_dispense_service import dispense_medication
		from alcura_ipd_ext.services.clinical_order_service import create_order

		company = _ensure_company()
		patient = _ensure_patient("_Test Lab Dispense")
		ir = _ensure_ir(patient, company)

		order = create_order(
			order_type="Lab Test",
			patient=patient,
			inpatient_record=ir,
			company=company,
			lab_test_name="CBC",
		)

		with pytest.raises(frappe.ValidationError):
			dispense_medication(order_name=order.name, dispensed_qty=1)


class TestSubstitution:
	def test_request_substitution(self, admin_session):
		from alcura_ipd_ext.services.pharmacy_dispense_service import request_substitution

		company = _ensure_company()
		patient = _ensure_patient("_Test Subst Patient")
		ir = _ensure_ir(patient, company)
		order = _create_medication_order(patient, ir, company)

		from alcura_ipd_ext.services.clinical_order_service import place_order, acknowledge_order

		place_order(order.name)
		acknowledge_order(order.name)

		result = request_substitution(order.name, "ITEM-ALT", "Out of stock")
		assert result["substitution_status"] == "Requested"

		order_doc = frappe.get_doc("IPD Clinical Order", order.name)
		assert order_doc.substitution_status == "Requested"
		assert order_doc.status == "On Hold"

	def test_approve_substitution(self, admin_session):
		from alcura_ipd_ext.services.pharmacy_dispense_service import (
			request_substitution,
			approve_substitution,
		)

		company = _ensure_company()
		patient = _ensure_patient("_Test Approve Subst")
		ir = _ensure_ir(patient, company)
		order = _create_medication_order(patient, ir, company)

		from alcura_ipd_ext.services.clinical_order_service import place_order, acknowledge_order

		place_order(order.name)
		acknowledge_order(order.name)

		request_substitution(order.name, "ITEM-ALT", "Out of stock")
		result = approve_substitution(order.name)
		assert result["substitution_status"] == "Approved"

	def test_reject_substitution(self, admin_session):
		from alcura_ipd_ext.services.pharmacy_dispense_service import (
			request_substitution,
			reject_substitution,
		)

		company = _ensure_company()
		patient = _ensure_patient("_Test Reject Subst")
		ir = _ensure_ir(patient, company)
		order = _create_medication_order(patient, ir, company)

		from alcura_ipd_ext.services.clinical_order_service import place_order, acknowledge_order

		place_order(order.name)
		acknowledge_order(order.name)

		request_substitution(order.name, "ITEM-ALT", "Out of stock")
		result = reject_substitution(order.name, "Not equivalent")
		assert result["substitution_status"] == "Rejected"


class TestReturnDispense:
	def test_return_dispense(self, admin_session):
		from alcura_ipd_ext.services.pharmacy_dispense_service import (
			dispense_medication,
			return_dispense,
		)

		company = _ensure_company()
		patient = _ensure_patient("_Test Return Patient")
		ir = _ensure_ir(patient, company)
		order = _create_medication_order(patient, ir, company)

		from alcura_ipd_ext.services.clinical_order_service import place_order, acknowledge_order

		place_order(order.name)
		acknowledge_order(order.name)

		result = dispense_medication(order_name=order.name, dispensed_qty=10)
		return_result = return_dispense(result["name"], "Patient discharged")
		assert return_result["status"] == "Returned"

		# Dispense status should revert to Pending
		order_doc = frappe.get_doc("IPD Clinical Order", order.name)
		assert order_doc.dispense_status == "Pending"
		assert order_doc.total_dispensed_qty == 0

	def test_double_return_fails(self, admin_session):
		from alcura_ipd_ext.services.pharmacy_dispense_service import (
			dispense_medication,
			return_dispense,
		)

		company = _ensure_company()
		patient = _ensure_patient("_Test Double Return")
		ir = _ensure_ir(patient, company)
		order = _create_medication_order(patient, ir, company)

		from alcura_ipd_ext.services.clinical_order_service import place_order, acknowledge_order

		place_order(order.name)
		acknowledge_order(order.name)

		result = dispense_medication(order_name=order.name, dispensed_qty=5)
		return_dispense(result["name"], "Reason 1")

		with pytest.raises(frappe.ValidationError):
			return_dispense(result["name"], "Reason 2")


class TestDispenseHistory:
	def test_get_dispense_history(self, admin_session):
		from alcura_ipd_ext.services.pharmacy_dispense_service import (
			dispense_medication,
			get_dispense_history,
		)

		company = _ensure_company()
		patient = _ensure_patient("_Test History Patient")
		ir = _ensure_ir(patient, company)
		order = _create_medication_order(patient, ir, company)

		from alcura_ipd_ext.services.clinical_order_service import place_order, acknowledge_order

		place_order(order.name)
		acknowledge_order(order.name)

		dispense_medication(order_name=order.name, dispensed_qty=5, dispense_type="Partial")
		dispense_medication(order_name=order.name, dispensed_qty=3, dispense_type="Partial")

		history = get_dispense_history(order.name)
		assert len(history) == 2
