"""Tests for I/O entry management and fluid balance computation (US-E4)."""

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
	if frappe.db.exists("Patient", {"patient_name": "_Test IO Patient"}):
		return frappe.get_doc("Patient", {"patient_name": "_Test IO Patient"})
	p = frappe.get_doc({
		"doctype": "Patient",
		"first_name": "_Test",
		"last_name": "IO Patient",
	})
	p.insert(ignore_permissions=True)
	return p


def _make_io_entry(ir, io_type, category, volume, fluid_name=""):
	doc = frappe.get_doc({
		"doctype": "IPD IO Entry",
		"patient": ir.patient,
		"inpatient_record": ir.name,
		"entry_datetime": now_datetime(),
		"io_type": io_type,
		"fluid_category": category,
		"fluid_name": fluid_name,
		"volume_ml": volume,
	})
	doc.insert(ignore_permissions=True)
	return doc


# ── Validation Tests ────────────────────────────────────────────────


class TestIOEntryValidation:
	def test_volume_must_be_positive(self, admin_session):
		ir = _make_ir()
		doc = frappe.get_doc({
			"doctype": "IPD IO Entry",
			"patient": ir.patient,
			"inpatient_record": ir.name,
			"entry_datetime": now_datetime(),
			"io_type": "Intake",
			"fluid_category": "IV Fluid",
			"volume_ml": 0,
		})
		with pytest.raises(frappe.ValidationError, match="greater than 0"):
			doc.insert(ignore_permissions=True)

	def test_valid_io_entry_creation(self, admin_session):
		ir = _make_ir()
		entry = _make_io_entry(ir, "Intake", "IV Fluid", 500, "NS 0.9%")
		assert entry.status == "Active"
		assert entry.volume_ml == 500

	def test_correction_requires_reason(self, admin_session):
		ir = _make_ir()
		original = _make_io_entry(ir, "Output", "Urine", 300)

		correction = frappe.get_doc({
			"doctype": "IPD IO Entry",
			"patient": ir.patient,
			"inpatient_record": ir.name,
			"entry_datetime": now_datetime(),
			"io_type": "Output",
			"fluid_category": "Urine",
			"volume_ml": 250,
			"is_correction": 1,
			"corrects_entry": original.name,
			"correction_reason": "",
		})
		with pytest.raises(frappe.ValidationError, match="correction reason"):
			correction.insert(ignore_permissions=True)


# ── Correction Tests ────────────────────────────────────────────────


class TestIOCorrection:
	def test_correction_marks_original(self, admin_session):
		from alcura_ipd_ext.services.io_service import create_io_correction

		ir = _make_ir()
		original = _make_io_entry(ir, "Intake", "Oral", 200)

		result = create_io_correction(original.name, "Volume was wrong")

		original.reload()
		assert original.status == "Corrected"

		new_entry = frappe.get_doc("IPD IO Entry", result["name"])
		assert new_entry.is_correction
		assert new_entry.corrects_entry == original.name


# ── Fluid Balance Tests ─────────────────────────────────────────────


class TestFluidBalance:
	def test_daily_balance(self, admin_session):
		from alcura_ipd_ext.services.io_service import get_fluid_balance

		ir = _make_ir()
		_make_io_entry(ir, "Intake", "IV Fluid", 500)
		_make_io_entry(ir, "Intake", "Oral", 200)
		_make_io_entry(ir, "Output", "Urine", 400)

		result = get_fluid_balance(ir.name)

		assert result["total_intake"] == 700
		assert result["total_output"] == 400
		assert result["balance"] == 300
		assert result["entry_count"] == 3
		assert result["intake_breakdown"]["IV Fluid"] == 500
		assert result["intake_breakdown"]["Oral"] == 200
		assert result["output_breakdown"]["Urine"] == 400

	def test_corrected_entries_excluded(self, admin_session):
		from alcura_ipd_ext.services.io_service import (
			create_io_correction,
			get_fluid_balance,
		)

		ir = _make_ir()
		original = _make_io_entry(ir, "Intake", "IV Fluid", 500)
		_make_io_entry(ir, "Output", "Urine", 300)

		create_io_correction(original.name, "Wrong volume")

		result = get_fluid_balance(ir.name)
		assert result["total_intake"] == 0
		assert result["total_output"] == 300

	def test_hourly_balance(self, admin_session):
		from alcura_ipd_ext.services.io_service import get_hourly_balance

		ir = _make_ir()
		_make_io_entry(ir, "Intake", "IV Fluid", 500)

		result = get_hourly_balance(ir.name)
		assert len(result) == 24

		total_intake = sum(r["intake"] for r in result)
		assert total_intake == 500

	def test_shift_balance(self, admin_session):
		from alcura_ipd_ext.services.io_service import get_shift_balance

		ir = _make_ir()
		_make_io_entry(ir, "Intake", "IV Fluid", 500)

		result = get_shift_balance(ir.name)
		assert len(result) == 3
		total = sum(r["intake"] for r in result)
		assert total == 500
