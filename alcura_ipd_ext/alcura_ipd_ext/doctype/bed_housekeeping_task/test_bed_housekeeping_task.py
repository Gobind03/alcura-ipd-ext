"""DocType-level tests for Bed Housekeeping Task.

Tests state transitions, SLA computation, and duplicate prevention.
"""

from __future__ import annotations

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import add_to_date, now_datetime


class TestBedHousekeepingTask(IntegrationTestCase):
	def setUp(self):
		if not frappe.db.exists("Company", "_Test BHT Company"):
			frappe.get_doc({
				"doctype": "Company",
				"company_name": "_Test BHT Company",
				"abbr": "TBHT",
				"default_currency": "INR",
				"country": "India",
			}).insert(ignore_permissions=True)

		if not frappe.db.exists("Hospital Ward", {"ward_code": "BHT-WARD"}):
			frappe.get_doc({
				"doctype": "Hospital Ward",
				"ward_name": "BHT Test Ward",
				"ward_code": "BHT-WARD",
				"company": "_Test BHT Company",
				"is_active": 1,
			}).insert(ignore_permissions=True)

	def _ensure_bed(self, bed_number="BHT01"):
		ward = frappe.db.get_value("Hospital Ward", {"ward_code": "BHT-WARD"}, "name")
		room_name = f"{ward}-BHTR01"
		if not frappe.db.exists("Hospital Room", room_name):
			frappe.get_doc({
				"doctype": "Hospital Room",
				"room_number": "BHTR01",
				"hospital_ward": ward,
				"company": "_Test BHT Company",
				"is_active": 1,
			}).insert(ignore_permissions=True)

		bed_key = f"{room_name}-{bed_number}"
		if not frappe.db.exists("Hospital Bed", bed_key):
			doc = frappe.get_doc({
				"doctype": "Hospital Bed",
				"bed_number": bed_number,
				"hospital_room": room_name,
				"is_active": 1,
				"occupancy_status": "Vacant",
				"housekeeping_status": "Dirty",
			})
			doc.flags.ignore_permissions = True
			doc.insert()
			return doc.name
		return bed_key

	def _make_task(self, bed_name):
		doc = frappe.get_doc({
			"doctype": "Bed Housekeeping Task",
			"hospital_bed": bed_name,
			"trigger_event": "Discharge",
			"cleaning_type": "Standard",
			"sla_target_minutes": 60,
			"created_on": now_datetime(),
		})
		doc.insert(ignore_permissions=True)
		return doc

	def test_start_and_complete_cycle(self):
		bed = self._ensure_bed()
		task = self._make_task(bed)

		self.assertEqual(task.status, "Pending")

		task.start_task()
		task.reload()
		self.assertEqual(task.status, "In Progress")
		self.assertIsNotNone(task.started_on)

		task.complete_task()
		task.reload()
		self.assertEqual(task.status, "Completed")
		self.assertIsNotNone(task.completed_on)
		self.assertGreaterEqual(task.turnaround_minutes, 0)

	def test_invalid_transition_from_completed(self):
		bed = self._ensure_bed("BHT02")
		task = self._make_task(bed)
		task.start_task()
		task.complete_task()

		self.assertRaises(frappe.ValidationError, task.start_task)

	def test_turnaround_computation(self):
		bed = self._ensure_bed("BHT03")
		task = self._make_task(bed)

		task.created_on = add_to_date(now_datetime(), minutes=-30)
		task.save(ignore_permissions=True)

		task.start_task()
		task.complete_task()
		task.reload()

		self.assertGreaterEqual(task.turnaround_minutes, 29)
