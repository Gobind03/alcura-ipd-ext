"""Tests for MAR entry management and status validations (US-E4)."""

from __future__ import annotations

import frappe
import pytest
from frappe.utils import now_datetime


# ── Helpers ──────────────────────────────────────────────────────────


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
	if frappe.db.exists("Patient", {"patient_name": "_Test MAR Patient"}):
		return frappe.get_doc("Patient", {"patient_name": "_Test MAR Patient"})
	p = frappe.get_doc({
		"doctype": "Patient",
		"first_name": "_Test",
		"last_name": "MAR Patient",
	})
	p.insert(ignore_permissions=True)
	return p


def _make_mar_entry(ir, **kwargs):
	defaults = {
		"doctype": "IPD MAR Entry",
		"patient": ir.patient,
		"inpatient_record": ir.name,
		"medication_name": "Paracetamol 500mg",
		"dose": "500mg",
		"route": "Oral",
		"scheduled_time": now_datetime(),
		"administration_status": "Scheduled",
	}
	defaults.update(kwargs)
	doc = frappe.get_doc(defaults)
	doc.insert(ignore_permissions=True)
	return doc


# ── Validation Tests ────────────────────────────────────────────────


class TestMARValidation:
	def test_held_requires_reason(self, admin_session):
		ir = _make_ir()
		doc = frappe.get_doc({
			"doctype": "IPD MAR Entry",
			"patient": ir.patient,
			"inpatient_record": ir.name,
			"medication_name": "Test Med",
			"dose": "100mg",
			"scheduled_time": now_datetime(),
			"administration_status": "Held",
			"hold_reason": "",
		})
		with pytest.raises(frappe.ValidationError, match="Hold reason"):
			doc.insert(ignore_permissions=True)

	def test_refused_requires_reason(self, admin_session):
		ir = _make_ir()
		doc = frappe.get_doc({
			"doctype": "IPD MAR Entry",
			"patient": ir.patient,
			"inpatient_record": ir.name,
			"medication_name": "Test Med",
			"dose": "100mg",
			"scheduled_time": now_datetime(),
			"administration_status": "Refused",
			"refusal_reason": "",
		})
		with pytest.raises(frappe.ValidationError, match="Refusal reason"):
			doc.insert(ignore_permissions=True)

	def test_given_auto_sets_timestamp(self, admin_session):
		ir = _make_ir()
		entry = _make_mar_entry(ir, administration_status="Given")
		assert entry.administered_at is not None
		assert entry.administered_by is not None

	def test_valid_scheduled_entry(self, admin_session):
		ir = _make_ir()
		entry = _make_mar_entry(ir)
		assert entry.status == "Active"
		assert entry.administration_status == "Scheduled"


# ── Correction Tests ────────────────────────────────────────────────


class TestMARCorrection:
	def test_correction_marks_original(self, admin_session):
		from alcura_ipd_ext.services.mar_service import create_mar_correction

		ir = _make_ir()
		original = _make_mar_entry(ir)

		result = create_mar_correction(original.name, "Wrong dose recorded")

		original.reload()
		assert original.status == "Corrected"

		new_entry = frappe.get_doc("IPD MAR Entry", result["name"])
		assert new_entry.is_correction
		assert new_entry.corrects_entry == original.name

	def test_double_correction_blocked(self, admin_session):
		from alcura_ipd_ext.services.mar_service import create_mar_correction

		ir = _make_ir()
		original = _make_mar_entry(ir)

		create_mar_correction(original.name, "First correction")

		with pytest.raises(frappe.ValidationError, match="already been corrected"):
			create_mar_correction(original.name, "Second correction")


# ── Summary Tests ────────────────────────────────────────────────────


class TestMARSummary:
	def test_summary_counts(self, admin_session):
		from alcura_ipd_ext.services.mar_service import get_mar_summary

		ir = _make_ir()
		_make_mar_entry(ir, administration_status="Given")
		_make_mar_entry(ir, administration_status="Scheduled")
		_make_mar_entry(
			ir,
			administration_status="Held",
			hold_reason="NPO for procedure",
		)

		result = get_mar_summary(ir.name)
		assert result["total"] == 3
		assert result["status_counts"]["Given"] == 1
		assert result["status_counts"]["Scheduled"] == 1
		assert result["status_counts"]["Held"] == 1
