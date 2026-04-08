"""Tests for nursing discharge checklist service (US-J2).

Covers checklist creation, item completion, skip/NA handling,
mandatory item enforcement, signoff, and verification.
"""

from __future__ import annotations

import frappe
import pytest
from frappe.utils import now_datetime, today

from alcura_ipd_ext.services.nursing_discharge_service import (
	create_nursing_checklist,
)


# ── Helpers ──────────────────────────────────────────────────────────


def _ensure_company():
	if not frappe.db.exists("Company", "_Test NDC Company"):
		frappe.get_doc({
			"doctype": "Company",
			"company_name": "_Test NDC Company",
			"abbr": "TNDC",
			"default_currency": "INR",
			"country": "India",
		}).insert(ignore_permissions=True)
	return "_Test NDC Company"


def _ensure_patient():
	if not frappe.db.exists("Patient", {"first_name": "_Test NDC Patient"}):
		doc = frappe.get_doc({
			"doctype": "Patient",
			"first_name": "_Test NDC Patient",
			"sex": "Female",
		})
		doc.insert(ignore_permissions=True)
		return doc.name
	return frappe.db.get_value("Patient", {"first_name": "_Test NDC Patient"}, "name")


def _ensure_ir(patient, company):
	doc = frappe.get_doc({
		"doctype": "Inpatient Record",
		"patient": patient,
		"company": company,
		"status": "Admitted",
		"scheduled_date": today(),
	})
	doc.insert(ignore_permissions=True)
	doc.db_set("status", "Admitted")
	doc.db_set("admitted_datetime", now_datetime())
	return doc.name


# ── Tests ────────────────────────────────────────────────────────────


class TestNursingChecklistCreation:
	def test_create_with_standard_items(self, admin_session):
		company = _ensure_company()
		patient = _ensure_patient()
		ir = _ensure_ir(patient, company)

		name = create_nursing_checklist(inpatient_record=ir)

		doc = frappe.get_doc("Nursing Discharge Checklist", name)
		assert doc.status == "Pending"
		assert doc.patient == patient
		assert len(doc.items) == 15
		assert doc.total_items == 15
		assert doc.completed_items == 0

		mandatory_items = [r for r in doc.items if r.is_mandatory]
		assert len(mandatory_items) == 9

	def test_reject_duplicate_checklist(self, admin_session):
		company = _ensure_company()
		patient = _ensure_patient()
		ir = _ensure_ir(patient, company)

		create_nursing_checklist(inpatient_record=ir)

		with pytest.raises(Exception, match="already exists"):
			create_nursing_checklist(inpatient_record=ir)

	def test_ir_link_set(self, admin_session):
		company = _ensure_company()
		patient = _ensure_patient()
		ir = _ensure_ir(patient, company)

		name = create_nursing_checklist(inpatient_record=ir)

		ir_link = frappe.db.get_value(
			"Inpatient Record", ir, "custom_nursing_discharge_checklist"
		)
		assert ir_link == name


class TestNursingChecklistItemCompletion:
	def test_complete_item(self, admin_session):
		company = _ensure_company()
		patient = _ensure_patient()
		ir = _ensure_ir(patient, company)
		name = create_nursing_checklist(inpatient_record=ir)

		doc = frappe.get_doc("Nursing Discharge Checklist", name)
		doc.complete_item(item_idx=1)

		doc.reload()
		assert doc.items[0].item_status == "Done"
		assert doc.items[0].completed_by == "Administrator"
		assert doc.items[0].completed_on is not None
		assert doc.status == "In Progress"
		assert doc.completed_items == 1

	def test_mark_not_applicable(self, admin_session):
		company = _ensure_company()
		patient = _ensure_patient()
		ir = _ensure_ir(patient, company)
		name = create_nursing_checklist(inpatient_record=ir)

		doc = frappe.get_doc("Nursing Discharge Checklist", name)
		doc.mark_not_applicable(item_idx=2)

		doc.reload()
		assert doc.items[1].item_status == "Not Applicable"

	def test_skip_with_reason(self, admin_session):
		company = _ensure_company()
		patient = _ensure_patient()
		ir = _ensure_ir(patient, company)
		name = create_nursing_checklist(inpatient_record=ir)

		doc = frappe.get_doc("Nursing Discharge Checklist", name)
		doc.skip_item(item_idx=2, reason="Catheter was not used")

		doc.reload()
		assert doc.items[1].item_status == "Skipped"
		assert doc.items[1].skip_reason == "Catheter was not used"

	def test_skip_without_reason_fails(self, admin_session):
		company = _ensure_company()
		patient = _ensure_patient()
		ir = _ensure_ir(patient, company)
		name = create_nursing_checklist(inpatient_record=ir)

		doc = frappe.get_doc("Nursing Discharge Checklist", name)
		with pytest.raises(Exception, match="[Rr]eason"):
			doc.skip_item(item_idx=2, reason="")


class TestNursingChecklistSignoff:
	def test_signoff_blocked_with_pending_mandatory(self, admin_session):
		company = _ensure_company()
		patient = _ensure_patient()
		ir = _ensure_ir(patient, company)
		name = create_nursing_checklist(inpatient_record=ir)

		doc = frappe.get_doc("Nursing Discharge Checklist", name)
		with pytest.raises(Exception, match="[Mm]andatory"):
			doc.sign_off()

	def test_signoff_succeeds_when_all_mandatory_done(self, admin_session):
		company = _ensure_company()
		patient = _ensure_patient()
		ir = _ensure_ir(patient, company)
		name = create_nursing_checklist(inpatient_record=ir)

		doc = frappe.get_doc("Nursing Discharge Checklist", name)
		for row in doc.items:
			if row.is_mandatory:
				row.item_status = "Done"
				row.completed_by = "Administrator"
				row.completed_on = now_datetime()
			else:
				row.item_status = "Not Applicable"
				row.completed_by = "Administrator"
				row.completed_on = now_datetime()
		doc.save(ignore_permissions=True)

		doc.sign_off(handover_notes="All clear")

		doc.reload()
		assert doc.status == "Completed"
		assert doc.completed_by == "Administrator"
		assert doc.completed_on is not None
		assert doc.handover_notes == "All clear"

	def test_verify_requires_completed(self, admin_session):
		company = _ensure_company()
		patient = _ensure_patient()
		ir = _ensure_ir(patient, company)
		name = create_nursing_checklist(inpatient_record=ir)

		doc = frappe.get_doc("Nursing Discharge Checklist", name)
		with pytest.raises(frappe.ValidationError):
			doc.verify()
