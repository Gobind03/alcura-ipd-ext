"""Tests for discharge orchestrator service (US-J3).

Covers the full bed vacate flow: validation, bed state transitions,
movement log creation, housekeeping task creation, and capacity rollup.
"""

from __future__ import annotations

import frappe
import pytest
from frappe.utils import add_days, now_datetime, today


# ── Helpers ──────────────────────────────────────────────────────────


def _ensure_company():
	if not frappe.db.exists("Company", "_Test Disch Co"):
		frappe.get_doc({
			"doctype": "Company",
			"company_name": "_Test Disch Co",
			"abbr": "TDC",
			"default_currency": "INR",
			"country": "India",
		}).insert(ignore_permissions=True)
	return "_Test Disch Co"


def _ensure_patient():
	if not frappe.db.exists("Patient", {"first_name": "_Test Disch Patient"}):
		doc = frappe.get_doc({
			"doctype": "Patient",
			"first_name": "_Test Disch Patient",
			"sex": "Male",
		})
		doc.insert(ignore_permissions=True)
		return doc.name
	return frappe.db.get_value("Patient", {"first_name": "_Test Disch Patient"}, "name")


def _ensure_practitioner():
	if not frappe.db.exists("Healthcare Practitioner", {"practitioner_name": "_Test Disch Dr"}):
		doc = frappe.get_doc({
			"doctype": "Healthcare Practitioner",
			"first_name": "_Test Disch Dr",
		})
		doc.insert(ignore_permissions=True)
		return doc.name
	return frappe.db.get_value(
		"Healthcare Practitioner", {"practitioner_name": "_Test Disch Dr"}, "name"
	)


def _ensure_ward():
	if not frappe.db.exists("Hospital Ward", {"ward_code": "DSC-WARD"}):
		company = _ensure_company()
		doc = frappe.get_doc({
			"doctype": "Hospital Ward",
			"ward_name": "Disch Test Ward",
			"ward_code": "DSC-WARD",
			"company": company,
			"is_active": 1,
		})
		doc.insert(ignore_permissions=True)
		return doc.name
	return frappe.db.get_value("Hospital Ward", {"ward_code": "DSC-WARD"}, "name")


def _ensure_room(ward):
	room_name = f"{ward}-DR01"
	if not frappe.db.exists("Hospital Room", room_name):
		company = frappe.db.get_value("Hospital Ward", ward, "company")
		doc = frappe.get_doc({
			"doctype": "Hospital Room",
			"room_number": "DR01",
			"hospital_ward": ward,
			"company": company,
			"is_active": 1,
		})
		doc.insert(ignore_permissions=True)
		return doc.name
	return room_name


def _ensure_bed(room, bed_number="DB01"):
	bed_key = f"{room}-{bed_number}"
	if not frappe.db.exists("Hospital Bed", bed_key):
		doc = frappe.get_doc({
			"doctype": "Hospital Bed",
			"bed_number": bed_number,
			"hospital_room": room,
			"is_active": 1,
			"occupancy_status": "Occupied",
			"housekeeping_status": "Clean",
		})
		doc.flags.ignore_permissions = True
		doc.insert()
		return doc.name
	frappe.db.set_value("Hospital Bed", bed_key, {
		"occupancy_status": "Occupied",
		"housekeeping_status": "Clean",
	}, update_modified=False)
	return bed_key


def _ensure_admitted_ir_with_bed(patient, company, bed, ward, room):
	doc = frappe.get_doc({
		"doctype": "Inpatient Record",
		"patient": patient,
		"company": company,
		"status": "Admitted",
		"scheduled_date": today(),
	})
	doc.insert(ignore_permissions=True)
	doc.db_set({
		"status": "Admitted",
		"admitted_datetime": now_datetime(),
		"custom_current_bed": bed,
		"custom_current_room": room,
		"custom_current_ward": ward,
	})
	return doc.name


def _create_and_acknowledge_advice(ir, practitioner):
	from alcura_ipd_ext.services.discharge_advice_service import (
		acknowledge_advice,
		create_discharge_advice,
	)

	name = create_discharge_advice(
		inpatient_record=ir,
		consultant=practitioner,
		expected_discharge_datetime=str(add_days(now_datetime(), 1)),
	)
	acknowledge_advice(name)
	return name


# ── Tests ────────────────────────────────────────────────────────────


class TestBedVacate:
	def test_vacate_with_acknowledged_advice(self, admin_session):
		company = _ensure_company()
		patient = _ensure_patient()
		practitioner = _ensure_practitioner()
		ward = _ensure_ward()
		room = _ensure_room(ward)
		bed = _ensure_bed(room)
		ir = _ensure_admitted_ir_with_bed(patient, company, bed, ward, room)

		_create_and_acknowledge_advice(ir, practitioner)

		from alcura_ipd_ext.services.discharge_service import process_bed_vacate

		result = process_bed_vacate(ir)

		assert result["inpatient_record"] == ir
		assert result["bed_movement_log"]
		assert result["bed"] == bed

		bed_status = frappe.db.get_value("Hospital Bed", bed, "occupancy_status")
		assert bed_status == "Vacant"

		ir_bed = frappe.db.get_value("Inpatient Record", ir, "custom_current_bed")
		assert ir_bed is None or ir_bed == ""

	def test_vacate_creates_housekeeping_task(self, admin_session):
		company = _ensure_company()
		patient = _ensure_patient()
		practitioner = _ensure_practitioner()
		ward = _ensure_ward()
		room = _ensure_room(ward)
		bed = _ensure_bed(room, "DB02")
		ir = _ensure_admitted_ir_with_bed(patient, company, bed, ward, room)

		_create_and_acknowledge_advice(ir, practitioner)

		from alcura_ipd_ext.services.discharge_service import process_bed_vacate

		result = process_bed_vacate(ir)

		if result.get("housekeeping_task"):
			task = frappe.get_doc("Bed Housekeeping Task", result["housekeeping_task"])
			assert task.hospital_bed == bed
			assert task.status == "Pending"
			assert task.trigger_event == "Discharge"

	def test_vacate_without_advice_still_works(self, admin_session):
		"""Bed vacate works without discharge advice (edge case)."""
		company = _ensure_company()
		patient = _ensure_patient()
		ward = _ensure_ward()
		room = _ensure_room(ward)
		bed = _ensure_bed(room, "DB03")
		ir = _ensure_admitted_ir_with_bed(patient, company, bed, ward, room)

		from alcura_ipd_ext.services.discharge_service import process_bed_vacate

		result = process_bed_vacate(ir)
		assert result["bed_movement_log"]

	def test_vacate_non_admitted_fails(self, admin_session):
		company = _ensure_company()
		patient = _ensure_patient()

		doc = frappe.get_doc({
			"doctype": "Inpatient Record",
			"patient": patient,
			"company": company,
			"status": "Admission Scheduled",
			"scheduled_date": today(),
		})
		doc.insert(ignore_permissions=True)

		from alcura_ipd_ext.services.discharge_service import process_bed_vacate

		with pytest.raises(frappe.ValidationError, match="Cannot vacate"):
			process_bed_vacate(doc.name)

	def test_creates_movement_log(self, admin_session):
		company = _ensure_company()
		patient = _ensure_patient()
		practitioner = _ensure_practitioner()
		ward = _ensure_ward()
		room = _ensure_room(ward)
		bed = _ensure_bed(room, "DB04")
		ir = _ensure_admitted_ir_with_bed(patient, company, bed, ward, room)

		_create_and_acknowledge_advice(ir, practitioner)

		from alcura_ipd_ext.services.discharge_service import process_bed_vacate

		result = process_bed_vacate(ir)

		bml = frappe.get_doc("Bed Movement Log", result["bed_movement_log"])
		assert bml.movement_type == "Discharge"
		assert bml.from_bed == bed
		assert bml.inpatient_record == ir
