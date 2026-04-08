"""Tests for clinical_order_service (US-F1, US-F2, US-F3).

Covers order creation (all types), status transitions, validation,
auto-population, PE integration, cancellation, hold/resume,
and IR aggregate count updates.
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


def _ensure_patient(name="_Test Order Patient"):
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


# ── Tests ────────────────────────────────────────────────────────────


class TestMedicationOrderCreation:
	def test_create_medication_order(self, admin_session):
		from alcura_ipd_ext.services.clinical_order_service import create_order

		company = _ensure_company()
		patient = _ensure_patient()
		ir = _ensure_ir(patient, company)

		order = create_order(
			order_type="Medication",
			patient=patient,
			inpatient_record=ir,
			company=company,
			medication_name="Paracetamol 500mg",
			dose="500",
			dose_uom="mg",
			route="Oral",
			frequency="TDS",
		)

		assert order.name
		assert order.status == "Ordered"
		assert order.order_type == "Medication"
		assert order.medication_name == "Paracetamol 500mg"
		assert order.ordered_at is not None
		assert order.ordered_by == "Administrator"

	def test_stat_order_sets_urgency(self, admin_session):
		from alcura_ipd_ext.services.clinical_order_service import create_order

		company = _ensure_company()
		patient = _ensure_patient()
		ir = _ensure_ir(patient, company)

		order = create_order(
			order_type="Medication",
			patient=patient,
			inpatient_record=ir,
			company=company,
			medication_name="Adrenaline 1mg",
			is_stat=1,
			urgency="Routine",
		)

		assert order.urgency == "STAT"

	def test_prn_requires_reason(self, admin_session):
		from alcura_ipd_ext.services.clinical_order_service import create_order

		company = _ensure_company()
		patient = _ensure_patient()
		ir = _ensure_ir(patient, company)

		with pytest.raises(frappe.ValidationError, match="PRN reason"):
			create_order(
				order_type="Medication",
				patient=patient,
				inpatient_record=ir,
				company=company,
				medication_name="Tramadol",
				is_prn=1,
				auto_place=False,
			)

	def test_medication_name_required(self, admin_session):
		from alcura_ipd_ext.services.clinical_order_service import create_order

		company = _ensure_company()
		patient = _ensure_patient()
		ir = _ensure_ir(patient, company)

		with pytest.raises(frappe.ValidationError, match="Medication Name"):
			create_order(
				order_type="Medication",
				patient=patient,
				inpatient_record=ir,
				company=company,
				auto_place=False,
			)


class TestLabOrderCreation:
	def test_create_lab_order(self, admin_session):
		from alcura_ipd_ext.services.clinical_order_service import create_order

		company = _ensure_company()
		patient = _ensure_patient()
		ir = _ensure_ir(patient, company)

		order = create_order(
			order_type="Lab Test",
			patient=patient,
			inpatient_record=ir,
			company=company,
			lab_test_name="Complete Blood Count",
			sample_type="Blood",
		)

		assert order.status == "Ordered"
		assert order.order_type == "Lab Test"
		assert order.lab_test_name == "Complete Blood Count"

	def test_lab_test_name_required(self, admin_session):
		from alcura_ipd_ext.services.clinical_order_service import create_order

		company = _ensure_company()
		patient = _ensure_patient()
		ir = _ensure_ir(patient, company)

		with pytest.raises(frappe.ValidationError, match="Lab Test Name"):
			create_order(
				order_type="Lab Test",
				patient=patient,
				inpatient_record=ir,
				company=company,
				auto_place=False,
			)


class TestProcedureOrderCreation:
	def test_create_procedure_order(self, admin_session):
		from alcura_ipd_ext.services.clinical_order_service import create_order

		company = _ensure_company()
		patient = _ensure_patient()
		ir = _ensure_ir(patient, company)

		order = create_order(
			order_type="Procedure",
			patient=patient,
			inpatient_record=ir,
			company=company,
			procedure_name="Central Line Insertion",
			body_site="Right Internal Jugular",
		)

		assert order.status == "Ordered"
		assert order.order_type == "Procedure"

	def test_create_radiology_order(self, admin_session):
		from alcura_ipd_ext.services.clinical_order_service import create_order

		company = _ensure_company()
		patient = _ensure_patient()
		ir = _ensure_ir(patient, company)

		order = create_order(
			order_type="Radiology",
			patient=patient,
			inpatient_record=ir,
			company=company,
			procedure_name="Chest X-Ray PA",
			urgency="Urgent",
		)

		assert order.order_type == "Radiology"
		assert order.urgency == "Urgent"


class TestStatusTransitions:
	def test_valid_transition_ordered_to_acknowledged(self, admin_session):
		from alcura_ipd_ext.services.clinical_order_service import (
			acknowledge_order,
			create_order,
		)

		company = _ensure_company()
		patient = _ensure_patient()
		ir = _ensure_ir(patient, company)

		order = create_order(
			order_type="Medication",
			patient=patient,
			inpatient_record=ir,
			company=company,
			medication_name="Amoxicillin",
		)

		acknowledge_order(order.name)
		order.reload()
		assert order.status == "Acknowledged"
		assert order.acknowledged_at is not None

	def test_valid_transition_to_completed(self, admin_session):
		from alcura_ipd_ext.services.clinical_order_service import (
			acknowledge_order,
			complete_order,
			create_order,
		)

		company = _ensure_company()
		patient = _ensure_patient()
		ir = _ensure_ir(patient, company)

		order = create_order(
			order_type="Lab Test",
			patient=patient,
			inpatient_record=ir,
			company=company,
			lab_test_name="RBS",
		)

		acknowledge_order(order.name)
		complete_order(order.name)
		order.reload()
		assert order.status == "Completed"
		assert order.completed_at is not None

	def test_invalid_transition_raises(self, admin_session):
		from alcura_ipd_ext.services.clinical_order_service import (
			complete_order,
			create_order,
		)

		company = _ensure_company()
		patient = _ensure_patient()
		ir = _ensure_ir(patient, company)

		order = create_order(
			order_type="Medication",
			patient=patient,
			inpatient_record=ir,
			company=company,
			medication_name="Metformin",
		)

		# Cannot go from Ordered directly to Completed (need Acknowledged first)
		# Actually our transition table allows Ordered -> In Progress but not Ordered -> Completed
		# The transition_to method validates this
		doc = frappe.get_doc("IPD Clinical Order", order.name)
		with pytest.raises(frappe.ValidationError, match="Invalid status transition"):
			doc.transition_to("Completed")

	def test_cannot_transition_from_completed(self, admin_session):
		from alcura_ipd_ext.services.clinical_order_service import (
			acknowledge_order,
			complete_order,
			create_order,
		)

		company = _ensure_company()
		patient = _ensure_patient()
		ir = _ensure_ir(patient, company)

		order = create_order(
			order_type="Medication",
			patient=patient,
			inpatient_record=ir,
			company=company,
			medication_name="Losartan",
		)

		acknowledge_order(order.name)
		complete_order(order.name)
		order.reload()

		with pytest.raises(frappe.ValidationError, match="Cannot change status"):
			order.transition_to("Ordered")

	def test_cancellation_requires_reason(self, admin_session):
		from alcura_ipd_ext.services.clinical_order_service import create_order

		company = _ensure_company()
		patient = _ensure_patient()
		ir = _ensure_ir(patient, company)

		order = create_order(
			order_type="Medication",
			patient=patient,
			inpatient_record=ir,
			company=company,
			medication_name="Diazepam",
		)

		order.reload()
		order.status = "Cancelled"
		with pytest.raises(frappe.ValidationError, match="Cancellation reason"):
			order.save()

	def test_cancel_with_reason(self, admin_session):
		from alcura_ipd_ext.services.clinical_order_service import (
			cancel_order,
			create_order,
		)

		company = _ensure_company()
		patient = _ensure_patient()
		ir = _ensure_ir(patient, company)

		order = create_order(
			order_type="Medication",
			patient=patient,
			inpatient_record=ir,
			company=company,
			medication_name="Aspirin",
		)

		cancel_order(order.name, "Patient allergy discovered")
		order.reload()
		assert order.status == "Cancelled"
		assert order.cancellation_reason == "Patient allergy discovered"

	def test_hold_and_resume(self, admin_session):
		from alcura_ipd_ext.services.clinical_order_service import (
			create_order,
			hold_order,
			resume_order,
		)

		company = _ensure_company()
		patient = _ensure_patient()
		ir = _ensure_ir(patient, company)

		order = create_order(
			order_type="Medication",
			patient=patient,
			inpatient_record=ir,
			company=company,
			medication_name="Omeprazole",
		)

		hold_order(order.name, "NPO for surgery")
		order.reload()
		assert order.status == "On Hold"

		resume_order(order.name)
		order.reload()
		assert order.status == "Ordered"


class TestIROrderCounts:
	def test_ir_counts_update_on_create(self, admin_session):
		from alcura_ipd_ext.services.clinical_order_service import create_order

		company = _ensure_company()
		patient = _ensure_patient("_Test Count Patient")
		ir = _ensure_ir(patient, company)

		create_order(
			order_type="Medication",
			patient=patient,
			inpatient_record=ir,
			company=company,
			medication_name="Test Med Count",
		)

		ir_doc = frappe.get_doc("Inpatient Record", ir)
		assert ir_doc.custom_active_medication_orders >= 1


class TestRejectOnDischargedIR:
	def test_order_rejected_for_discharged_ir(self, admin_session):
		from alcura_ipd_ext.services.clinical_order_service import create_order

		company = _ensure_company()
		patient = _ensure_patient("_Test Discharged Patient")
		ir = _ensure_ir(patient, company)
		frappe.db.set_value("Inpatient Record", ir, "status", "Discharged")

		with pytest.raises(frappe.ValidationError, match="Cannot place orders"):
			create_order(
				order_type="Medication",
				patient=patient,
				inpatient_record=ir,
				company=company,
				medication_name="Should Fail",
			)
