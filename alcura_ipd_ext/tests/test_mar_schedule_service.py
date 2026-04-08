"""Tests for mar_schedule_service (US-G2).

Covers MAR entry generation from medication order frequency,
daily generation, overdue marking, shift computation, and
ward MAR board summary.
"""

from __future__ import annotations

import frappe
import pytest
from frappe.utils import add_days, get_datetime, now_datetime, today


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


def _ensure_patient(name="_Test MAR Patient"):
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
		"scheduled_date": today(),
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
		"medication_name": "Amoxicillin 500mg",
		"dose": "500",
		"dose_uom": "mg",
		"route": "Oral",
		"frequency": "BD",
		"start_datetime": get_datetime(f"{today()} 08:00:00"),
		"duration_days": 1,
	}
	defaults.update(kwargs)
	return create_order(**defaults)


# ── Tests ────────────────────────────────────────────────────────────


class TestGenerateFromOrder:
	def test_generate_bd_schedule(self, admin_session):
		from alcura_ipd_ext.services.mar_schedule_service import generate_mar_entries_for_order

		company = _ensure_company()
		patient = _ensure_patient()
		ir = _ensure_ir(patient, company)
		order = _create_medication_order(patient, ir, company, frequency="BD", duration_days=1)

		entries = generate_mar_entries_for_order(order.name)
		# BD -> [08:00, 20:00], 1 day, start at 08:00 -> up to 2 entries
		assert len(entries) >= 1
		assert len(entries) <= 2

	def test_generate_tds_schedule(self, admin_session):
		from alcura_ipd_ext.services.mar_schedule_service import generate_mar_entries_for_order

		company = _ensure_company()
		patient = _ensure_patient("_Test TDS Patient")
		ir = _ensure_ir(patient, company)
		order = _create_medication_order(
			patient, ir, company,
			frequency="TDS",
			start_datetime=get_datetime(f"{today()} 00:00:00"),
			duration_days=1,
		)

		entries = generate_mar_entries_for_order(order.name)
		# TDS -> [06:00, 14:00, 22:00], should get up to 3 entries
		assert len(entries) == 3

	def test_stat_order_single_entry(self, admin_session):
		from alcura_ipd_ext.services.mar_schedule_service import generate_mar_entries_for_order

		company = _ensure_company()
		patient = _ensure_patient("_Test STAT MAR")
		ir = _ensure_ir(patient, company)
		order = _create_medication_order(
			patient, ir, company,
			frequency="STAT",
		)

		entries = generate_mar_entries_for_order(order.name)
		assert len(entries) == 1

	def test_prn_no_entries(self, admin_session):
		from alcura_ipd_ext.services.mar_schedule_service import generate_mar_entries_for_order

		company = _ensure_company()
		patient = _ensure_patient("_Test PRN MAR")
		ir = _ensure_ir(patient, company)
		order = _create_medication_order(
			patient, ir, company,
			frequency="PRN",
			is_prn=1,
		)

		entries = generate_mar_entries_for_order(order.name)
		assert len(entries) == 0

	def test_non_medication_no_entries(self, admin_session):
		from alcura_ipd_ext.services.mar_schedule_service import generate_mar_entries_for_order
		from alcura_ipd_ext.services.clinical_order_service import create_order

		company = _ensure_company()
		patient = _ensure_patient("_Test Lab MAR")
		ir = _ensure_ir(patient, company)
		order = create_order(
			order_type="Lab Test",
			patient=patient,
			inpatient_record=ir,
			company=company,
			lab_test_name="CBC",
		)

		entries = generate_mar_entries_for_order(order.name)
		assert len(entries) == 0

	def test_no_duplicate_entries(self, admin_session):
		from alcura_ipd_ext.services.mar_schedule_service import generate_mar_entries_for_order

		company = _ensure_company()
		patient = _ensure_patient("_Test Dedup MAR")
		ir = _ensure_ir(patient, company)
		order = _create_medication_order(
			patient, ir, company,
			frequency="OD",
			duration_days=1,
		)

		first = generate_mar_entries_for_order(order.name)
		second = generate_mar_entries_for_order(order.name)

		# Second call should not create duplicates
		assert len(second) == 0


class TestShiftComputation:
	def test_morning_shift(self, admin_session):
		from alcura_ipd_ext.services.mar_schedule_service import compute_shift

		assert compute_shift(get_datetime(f"{today()} 08:00:00")) == "Morning"
		assert compute_shift(get_datetime(f"{today()} 06:00:00")) == "Morning"
		assert compute_shift(get_datetime(f"{today()} 13:59:00")) == "Morning"

	def test_afternoon_shift(self, admin_session):
		from alcura_ipd_ext.services.mar_schedule_service import compute_shift

		assert compute_shift(get_datetime(f"{today()} 14:00:00")) == "Afternoon"
		assert compute_shift(get_datetime(f"{today()} 21:59:00")) == "Afternoon"

	def test_night_shift(self, admin_session):
		from alcura_ipd_ext.services.mar_schedule_service import compute_shift

		assert compute_shift(get_datetime(f"{today()} 22:00:00")) == "Night"
		assert compute_shift(get_datetime(f"{today()} 00:00:00")) == "Night"
		assert compute_shift(get_datetime(f"{today()} 05:59:00")) == "Night"


class TestMarkOverdue:
	def test_mark_overdue_entries(self, admin_session):
		from alcura_ipd_ext.services.mar_schedule_service import mark_overdue_scheduled_entries

		company = _ensure_company()
		patient = _ensure_patient("_Test Overdue MAR")
		ir = _ensure_ir(patient, company)
		order = _create_medication_order(patient, ir, company, frequency="OD")

		# Create a MAR entry with a past scheduled_time
		past_time = frappe.utils.add_to_date(now_datetime(), hours=-3)
		entry = frappe.get_doc({
			"doctype": "IPD MAR Entry",
			"patient": patient,
			"inpatient_record": ir,
			"medication_name": "Overdue Test Med",
			"dose": "100",
			"dose_uom": "mg",
			"scheduled_time": past_time,
			"administration_status": "Scheduled",
			"clinical_order": order.name,
		})
		entry.insert(ignore_permissions=True)

		count = mark_overdue_scheduled_entries()
		assert count >= 1

		entry.reload()
		assert entry.administration_status == "Missed"


class TestCancelPendingEntries:
	def test_cancel_pending_entries(self, admin_session):
		from alcura_ipd_ext.services.mar_schedule_service import (
			generate_mar_entries_for_order,
			cancel_pending_mar_entries,
		)

		company = _ensure_company()
		patient = _ensure_patient("_Test Cancel MAR")
		ir = _ensure_ir(patient, company)
		order = _create_medication_order(
			patient, ir, company,
			frequency="TDS",
			start_datetime=get_datetime(f"{today()} 00:00:00"),
			duration_days=1,
		)

		created = generate_mar_entries_for_order(order.name)
		assert len(created) > 0

		cancelled = cancel_pending_mar_entries(order.name)
		assert cancelled == len(created)


class TestWardMARBoard:
	def test_board_returns_structure(self, admin_session):
		from alcura_ipd_ext.services.mar_schedule_service import get_ward_mar_board

		result = get_ward_mar_board("NONEXISTENT_WARD")
		assert "patients" in result
		assert "status_counts" in result
		assert result["total"] == 0


class TestShiftSummary:
	def test_shift_summary_structure(self, admin_session):
		from alcura_ipd_ext.services.mar_schedule_service import get_shift_mar_summary

		result = get_shift_mar_summary("NONEXISTENT_WARD", today(), "Morning")
		assert "total" in result
		assert "status_counts" in result
		assert "patient_count" in result
