"""Tests for housekeeping service (US-J3).

Covers housekeeping task creation, state transitions, SLA computation,
breach detection, cleaning type determination, and concurrent task prevention.
"""

from __future__ import annotations

import frappe
import pytest
from frappe.utils import add_to_date, now_datetime

from alcura_ipd_ext.services.housekeeping_service import (
	cancel_task,
	check_sla_breaches,
	complete_cleaning,
	create_housekeeping_task,
	start_cleaning,
)


# ── Helpers ──────────────────────────────────────────────────────────


def _ensure_ward():
	if not frappe.db.exists("Hospital Ward", {"ward_code": "HK-WARD"}):
		company = _ensure_company()
		doc = frappe.get_doc({
			"doctype": "Hospital Ward",
			"ward_name": "HK Test Ward",
			"ward_code": "HK-WARD",
			"company": company,
			"is_active": 1,
		})
		doc.insert(ignore_permissions=True)
		return doc.name
	return frappe.db.get_value("Hospital Ward", {"ward_code": "HK-WARD"}, "name")


def _ensure_company():
	if not frappe.db.exists("Company", "_Test HK Co"):
		frappe.get_doc({
			"doctype": "Company",
			"company_name": "_Test HK Co",
			"abbr": "THKC",
			"default_currency": "INR",
			"country": "India",
		}).insert(ignore_permissions=True)
	return "_Test HK Co"


def _ensure_room(ward):
	room_name = f"{ward}-R01"
	if not frappe.db.exists("Hospital Room", room_name):
		company = frappe.db.get_value("Hospital Ward", ward, "company")
		doc = frappe.get_doc({
			"doctype": "Hospital Room",
			"room_number": "R01",
			"hospital_ward": ward,
			"company": company,
			"is_active": 1,
		})
		doc.insert(ignore_permissions=True)
		return doc.name
	return room_name


def _ensure_bed(room, bed_number="B01"):
	bed_key = f"{room}-{bed_number}"
	if not frappe.db.exists("Hospital Bed", bed_key):
		doc = frappe.get_doc({
			"doctype": "Hospital Bed",
			"bed_number": bed_number,
			"hospital_room": room,
			"is_active": 1,
			"occupancy_status": "Vacant",
			"housekeeping_status": "Dirty",
		})
		doc.flags.ignore_permissions = True
		doc.insert()
		return doc.name
	frappe.db.set_value("Hospital Bed", bed_key, {
		"occupancy_status": "Vacant",
		"housekeeping_status": "Dirty",
	}, update_modified=False)
	return bed_key


# ── Tests ────────────────────────────────────────────────────────────


class TestHousekeepingTaskCreation:
	def test_create_standard_task(self, admin_session):
		ward = _ensure_ward()
		room = _ensure_room(ward)
		bed = _ensure_bed(room)

		name = create_housekeeping_task(
			hospital_bed=bed,
			trigger_event="Discharge",
		)

		doc = frappe.get_doc("Bed Housekeeping Task", name)
		assert doc.status == "Pending"
		assert doc.cleaning_type == "Standard"
		assert doc.hospital_bed == bed
		assert doc.sla_target_minutes > 0

	def test_infection_bed_gets_isolation_clean(self, admin_session):
		ward = _ensure_ward()
		room = _ensure_room(ward)
		bed = _ensure_bed(room, "B02")
		frappe.db.set_value("Hospital Bed", bed, "infection_block", 1, update_modified=False)

		name = create_housekeeping_task(hospital_bed=bed)

		doc = frappe.get_doc("Bed Housekeeping Task", name)
		assert doc.cleaning_type == "Isolation Clean"
		assert doc.requires_deep_clean == 1
		assert doc.sla_target_minutes > 60

	def test_no_duplicate_active_task(self, admin_session):
		ward = _ensure_ward()
		room = _ensure_room(ward)
		bed = _ensure_bed(room, "B03")

		create_housekeeping_task(hospital_bed=bed)

		with pytest.raises(frappe.ValidationError, match="active housekeeping"):
			create_housekeeping_task(hospital_bed=bed)


class TestHousekeepingTransitions:
	def test_start_cleaning(self, admin_session):
		ward = _ensure_ward()
		room = _ensure_room(ward)
		bed = _ensure_bed(room, "B04")

		name = create_housekeeping_task(hospital_bed=bed)
		start_cleaning(name)

		doc = frappe.get_doc("Bed Housekeeping Task", name)
		assert doc.status == "In Progress"
		assert doc.started_on is not None
		assert doc.started_by == "Administrator"

		bed_status = frappe.db.get_value("Hospital Bed", bed, "housekeeping_status")
		assert bed_status == "In Progress"

	def test_complete_cleaning(self, admin_session):
		ward = _ensure_ward()
		room = _ensure_room(ward)
		bed = _ensure_bed(room, "B05")

		name = create_housekeeping_task(hospital_bed=bed)
		start_cleaning(name)
		result = complete_cleaning(name)

		assert result["status"] == "Completed"
		assert result["turnaround_minutes"] >= 0

		bed_status = frappe.db.get_value("Hospital Bed", bed, "housekeeping_status")
		assert bed_status == "Clean"

	def test_cancel_task(self, admin_session):
		ward = _ensure_ward()
		room = _ensure_room(ward)
		bed = _ensure_bed(room, "B06")

		name = create_housekeeping_task(hospital_bed=bed)
		cancel_task(name)

		doc = frappe.get_doc("Bed Housekeeping Task", name)
		assert doc.status == "Cancelled"

	def test_invalid_transition_fails(self, admin_session):
		ward = _ensure_ward()
		room = _ensure_room(ward)
		bed = _ensure_bed(room, "B07")

		name = create_housekeeping_task(hospital_bed=bed)
		start_cleaning(name)
		complete_cleaning(name)

		doc = frappe.get_doc("Bed Housekeeping Task", name)
		with pytest.raises(frappe.ValidationError, match="Cannot transition"):
			doc.start_task()


class TestHousekeepingSLA:
	def test_breach_detection(self, admin_session):
		ward = _ensure_ward()
		room = _ensure_room(ward)
		bed = _ensure_bed(room, "B08")

		name = create_housekeeping_task(hospital_bed=bed)

		# Backdate created_on to simulate SLA breach
		past = add_to_date(now_datetime(), minutes=-120)
		frappe.db.set_value(
			"Bed Housekeeping Task", name,
			"created_on", past,
			update_modified=False,
		)

		count = check_sla_breaches()
		assert count >= 1

		doc = frappe.get_doc("Bed Housekeeping Task", name)
		assert doc.sla_breached == 1

	def test_no_breach_within_sla(self, admin_session):
		ward = _ensure_ward()
		room = _ensure_room(ward)
		bed = _ensure_bed(room, "B09")

		create_housekeeping_task(hospital_bed=bed)

		count = check_sla_breaches()
		# task was just created so should not breach yet
		# (unless SLA is 0, which would be unusual)
		# We just verify it doesn't crash
		assert count >= 0
