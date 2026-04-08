"""Tests for lab_sample_service (US-G3).

Covers sample creation, collection, handoff, receipt,
recollection, critical result acknowledgment, and queue queries.
"""

from __future__ import annotations

import frappe
import pytest
from frappe.utils import today


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


def _ensure_patient(name="_Test Lab Sample Patient"):
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
		"scheduled_date": today(),
	})
	doc.insert(ignore_permissions=True)
	frappe.db.set_value("Inpatient Record", doc.name, "status", "Admitted")
	return doc.name


def _create_lab_order(patient, ir, company, **kwargs):
	from alcura_ipd_ext.services.clinical_order_service import create_order

	defaults = {
		"order_type": "Lab Test",
		"patient": patient,
		"inpatient_record": ir,
		"company": company,
		"lab_test_name": "Complete Blood Count",
		"sample_type": "Blood",
	}
	defaults.update(kwargs)
	return create_order(**defaults)


# ── Tests ────────────────────────────────────────────────────────────


class TestSampleCreation:
	def test_create_sample_from_order(self, admin_session):
		from alcura_ipd_ext.services.lab_sample_service import create_sample

		company = _ensure_company()
		patient = _ensure_patient()
		ir = _ensure_ir(patient, company)
		order = _create_lab_order(patient, ir, company)

		result = create_sample(order.name)
		assert result["name"]
		assert result["barcode"]

		sample = frappe.get_doc("IPD Lab Sample", result["name"])
		assert sample.status == "Pending"
		assert sample.collection_status == "Pending"
		assert sample.patient == patient
		assert sample.lab_test_name == "Complete Blood Count"

	def test_create_sample_fails_for_medication(self, admin_session):
		from alcura_ipd_ext.services.lab_sample_service import create_sample
		from alcura_ipd_ext.services.clinical_order_service import create_order

		company = _ensure_company()
		patient = _ensure_patient("_Test Med Sample")
		ir = _ensure_ir(patient, company)
		order = create_order(
			order_type="Medication",
			patient=patient,
			inpatient_record=ir,
			company=company,
			medication_name="Ibuprofen",
		)

		with pytest.raises(frappe.ValidationError):
			create_sample(order.name)

	def test_create_sample_fails_for_cancelled(self, admin_session):
		from alcura_ipd_ext.services.lab_sample_service import create_sample
		from alcura_ipd_ext.services.clinical_order_service import place_order, cancel_order

		company = _ensure_company()
		patient = _ensure_patient("_Test Cancel Sample")
		ir = _ensure_ir(patient, company)
		order = _create_lab_order(patient, ir, company)

		place_order(order.name)
		cancel_order(order.name, reason="Test")

		with pytest.raises(frappe.ValidationError):
			create_sample(order.name)


class TestSampleCollection:
	def test_record_collection(self, admin_session):
		from alcura_ipd_ext.services.lab_sample_service import create_sample, record_collection

		company = _ensure_company()
		patient = _ensure_patient("_Test Collect Patient")
		ir = _ensure_ir(patient, company)
		order = _create_lab_order(patient, ir, company)

		sample_result = create_sample(order.name)
		result = record_collection(
			sample_result["name"],
			collection_site="Left Antecubital",
			notes="Smooth collection",
		)

		assert result["status"] == "Collected"
		sample = frappe.get_doc("IPD Lab Sample", sample_result["name"])
		assert sample.collection_status == "Collected"
		assert sample.collected_by
		assert sample.collected_at
		assert sample.collection_site == "Left Antecubital"


class TestSampleHandoff:
	def test_record_handoff(self, admin_session):
		from alcura_ipd_ext.services.lab_sample_service import (
			create_sample,
			record_collection,
			record_handoff,
		)

		company = _ensure_company()
		patient = _ensure_patient("_Test Handoff Patient")
		ir = _ensure_ir(patient, company)
		order = _create_lab_order(patient, ir, company)

		sample_result = create_sample(order.name)
		record_collection(sample_result["name"])
		result = record_handoff(sample_result["name"], transport_mode="Pneumatic Tube")

		assert result["status"] == "In Transit"
		sample = frappe.get_doc("IPD Lab Sample", sample_result["name"])
		assert sample.transport_mode == "Pneumatic Tube"


class TestSampleReceipt:
	def test_record_receipt_acceptable(self, admin_session):
		from alcura_ipd_ext.services.lab_sample_service import (
			create_sample,
			record_collection,
			record_handoff,
			record_receipt,
		)

		company = _ensure_company()
		patient = _ensure_patient("_Test Receipt OK")
		ir = _ensure_ir(patient, company)
		order = _create_lab_order(patient, ir, company)

		sample_result = create_sample(order.name)
		record_collection(sample_result["name"])
		record_handoff(sample_result["name"])
		result = record_receipt(sample_result["name"], sample_condition="Acceptable")

		assert result["status"] == "Received"
		assert result["needs_recollection"] is False

	def test_record_receipt_hemolyzed_triggers_recollection(self, admin_session):
		from alcura_ipd_ext.services.lab_sample_service import (
			create_sample,
			record_collection,
			record_handoff,
			record_receipt,
		)

		company = _ensure_company()
		patient = _ensure_patient("_Test Hemolyzed")
		ir = _ensure_ir(patient, company)
		order = _create_lab_order(patient, ir, company)

		sample_result = create_sample(order.name)
		record_collection(sample_result["name"])
		record_handoff(sample_result["name"])
		result = record_receipt(sample_result["name"], sample_condition="Hemolyzed")

		assert result["needs_recollection"] is True

		# Original should be Rejected with Recollection Needed
		original = frappe.get_doc("IPD Lab Sample", sample_result["name"])
		assert original.status == "Rejected"
		assert original.collection_status == "Recollection Needed"

		# A new sample should exist linked to the original
		new_samples = frappe.get_all(
			"IPD Lab Sample",
			filters={"parent_sample": sample_result["name"]},
			pluck="name",
		)
		assert len(new_samples) == 1

		new_sample = frappe.get_doc("IPD Lab Sample", new_samples[0])
		assert new_sample.status == "Pending"
		assert new_sample.parent_sample == sample_result["name"]


class TestRecollection:
	def test_request_recollection(self, admin_session):
		from alcura_ipd_ext.services.lab_sample_service import (
			create_sample,
			record_collection,
			request_recollection,
		)

		company = _ensure_company()
		patient = _ensure_patient("_Test Recollect")
		ir = _ensure_ir(patient, company)
		order = _create_lab_order(patient, ir, company)

		sample_result = create_sample(order.name)
		record_collection(sample_result["name"])

		# Transition to Received first since Collected can only go to In Transit or Received
		sample = frappe.get_doc("IPD Lab Sample", sample_result["name"])
		sample.transition_to("Received")
		sample.save(ignore_permissions=True)

		result = request_recollection(sample_result["name"], "Clotted sample")
		assert result["new_sample"]
		assert result["original_sample"] == sample_result["name"]


class TestCriticalResult:
	def test_acknowledge_critical_result(self, admin_session):
		from alcura_ipd_ext.services.lab_sample_service import (
			create_sample,
			acknowledge_critical_result,
		)

		company = _ensure_company()
		patient = _ensure_patient("_Test Critical")
		ir = _ensure_ir(patient, company)
		order = _create_lab_order(patient, ir, company)

		sample_result = create_sample(order.name)

		# Mark as critical
		frappe.db.set_value("IPD Lab Sample", sample_result["name"], "is_critical_result", 1)

		result = acknowledge_critical_result(sample_result["name"])
		assert result["acknowledged_by"]

		sample = frappe.get_doc("IPD Lab Sample", sample_result["name"])
		assert sample.critical_result_acknowledged_by
		assert sample.critical_result_acknowledged_at

	def test_acknowledge_non_critical_fails(self, admin_session):
		from alcura_ipd_ext.services.lab_sample_service import (
			create_sample,
			acknowledge_critical_result,
		)

		company = _ensure_company()
		patient = _ensure_patient("_Test Non Critical")
		ir = _ensure_ir(patient, company)
		order = _create_lab_order(patient, ir, company)

		sample_result = create_sample(order.name)

		with pytest.raises(frappe.ValidationError):
			acknowledge_critical_result(sample_result["name"])


class TestSampleTransitions:
	def test_valid_transitions(self, admin_session):
		from alcura_ipd_ext.services.lab_sample_service import create_sample

		company = _ensure_company()
		patient = _ensure_patient("_Test Transitions")
		ir = _ensure_ir(patient, company)
		order = _create_lab_order(patient, ir, company)

		sample_result = create_sample(order.name)
		sample = frappe.get_doc("IPD Lab Sample", sample_result["name"])

		sample.transition_to("Collected")
		assert sample.status == "Collected"

		sample.transition_to("In Transit")
		assert sample.status == "In Transit"

		sample.transition_to("Received")
		assert sample.status == "Received"

		sample.transition_to("Processing")
		assert sample.status == "Processing"

		sample.transition_to("Completed")
		assert sample.status == "Completed"

	def test_invalid_transition_raises(self, admin_session):
		from alcura_ipd_ext.services.lab_sample_service import create_sample

		company = _ensure_company()
		patient = _ensure_patient("_Test Bad Transition")
		ir = _ensure_ir(patient, company)
		order = _create_lab_order(patient, ir, company)

		sample_result = create_sample(order.name)
		sample = frappe.get_doc("IPD Lab Sample", sample_result["name"])

		with pytest.raises(frappe.ValidationError):
			sample.transition_to("Completed")  # Pending -> Completed is invalid

	def test_cannot_transition_from_terminal(self, admin_session):
		from alcura_ipd_ext.services.lab_sample_service import create_sample

		company = _ensure_company()
		patient = _ensure_patient("_Test Terminal")
		ir = _ensure_ir(patient, company)
		order = _create_lab_order(patient, ir, company)

		sample_result = create_sample(order.name)
		sample = frappe.get_doc("IPD Lab Sample", sample_result["name"])
		sample.transition_to("Rejected")
		assert sample.status == "Rejected"

		with pytest.raises(frappe.ValidationError):
			sample.transition_to("Pending")


class TestCollectionQueue:
	def test_collection_queue_returns_pending(self, admin_session):
		from alcura_ipd_ext.services.lab_sample_service import create_sample, get_collection_queue

		company = _ensure_company()
		patient = _ensure_patient("_Test Queue Patient")
		ir = _ensure_ir(patient, company)
		order = _create_lab_order(patient, ir, company)

		create_sample(order.name)
		queue = get_collection_queue()

		assert len(queue) >= 1
		sample_names = [s["name"] for s in queue]
		assert any(True for q in queue if q["clinical_order"] == order.name)


class TestSampleLifecycle:
	def test_full_lifecycle(self, admin_session):
		from alcura_ipd_ext.services.lab_sample_service import get_sample_lifecycle, create_sample

		company = _ensure_company()
		patient = _ensure_patient("_Test Lifecycle")
		ir = _ensure_ir(patient, company)
		order = _create_lab_order(patient, ir, company)

		create_sample(order.name)
		lifecycle = get_sample_lifecycle(order.name)

		assert len(lifecycle) >= 1
		assert lifecycle[0]["status"] == "Pending"
