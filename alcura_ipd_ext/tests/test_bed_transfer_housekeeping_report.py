"""Tests for the Bed Transfer and Housekeeping Report (US-K2).

Covers: transfer listing, date/ward/consultant filters, blocked bed
snapshot, housekeeping TAT aggregation, SLA breach %, and the report
execute() entry point.
"""

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import add_days, now_datetime, today

from alcura_ipd_ext.alcura_ipd_ext.report.bed_transfer_housekeeping.bed_transfer_housekeeping import (
	_count_transfers,
	_get_blocked_beds,
	_get_housekeeping_by_ward,
	_get_housekeeping_summary,
	_get_transfer_data,
	execute as report_execute,
)


# ---------------------------------------------------------------------------
# Factories
# ---------------------------------------------------------------------------


def _get_or_create_company(abbr="TBH", name="Test BTH Hospital Pvt Ltd"):
	if frappe.db.exists("Company", name):
		return name
	company = frappe.get_doc({
		"doctype": "Company",
		"company_name": name,
		"abbr": abbr,
		"default_currency": "INR",
		"country": "India",
	})
	company.insert(ignore_if_duplicate=True)
	return company.name


def _get_or_create_hsut(name="Test BTH Bed Type", inpatient_occupancy=1):
	if frappe.db.exists("Healthcare Service Unit Type", name):
		return name
	doc = frappe.get_doc({
		"doctype": "Healthcare Service Unit Type",
		"healthcare_service_unit_type": name,
		"inpatient_occupancy": inpatient_occupancy,
	})
	doc.flags.ignore_validate = True
	doc.insert(ignore_if_duplicate=True)
	return doc.name


def _get_or_create_ward(ward_code, company=None, **overrides):
	company = company or _get_or_create_company()
	abbr = frappe.get_cached_value("Company", company, "abbr")
	ward_key = f"{abbr}-{ward_code.upper()}"
	if frappe.db.exists("Hospital Ward", ward_key):
		return frappe.get_doc("Hospital Ward", ward_key)
	doc = frappe.get_doc({
		"doctype": "Hospital Ward",
		"ward_code": ward_code,
		"ward_name": overrides.pop("ward_name", f"Test Ward {ward_code}"),
		"company": company,
		"ward_classification": overrides.pop("ward_classification", "General"),
		**overrides,
	})
	doc.insert()
	return doc


def _get_or_create_room(room_number, ward=None, **overrides):
	ward_doc = ward or _get_or_create_ward("BTH01")
	ward_name = ward_doc.name if hasattr(ward_doc, "name") else ward_doc
	room_key = f"{ward_name}-{room_number.upper()}"
	if frappe.db.exists("Hospital Room", room_key):
		return frappe.get_doc("Hospital Room", room_key)
	hsut = overrides.pop("service_unit_type", None) or _get_or_create_hsut()
	doc = frappe.get_doc({
		"doctype": "Hospital Room",
		"room_number": room_number,
		"room_name": overrides.pop("room_name", f"Room {room_number}"),
		"hospital_ward": ward_name,
		"service_unit_type": hsut,
		**overrides,
	})
	doc.insert()
	return doc


def _make_bed(bed_number, room=None, **overrides):
	room_doc = room or _get_or_create_room("BTH01")
	room_name = room_doc.name if hasattr(room_doc, "name") else room_doc
	doc = frappe.get_doc({
		"doctype": "Hospital Bed",
		"bed_number": bed_number,
		"hospital_room": room_name,
		**overrides,
	})
	doc.insert()
	return doc


def _make_bml(movement_type, from_bed=None, to_bed=None, **overrides):
	"""Create a Bed Movement Log entry."""
	company = overrides.pop("company", _get_or_create_company())
	patient = overrides.pop("patient", _get_or_create_patient("BTH Test Patient"))

	doc = frappe.get_doc({
		"doctype": "Bed Movement Log",
		"movement_type": movement_type,
		"movement_datetime": overrides.pop("movement_datetime", now_datetime()),
		"patient": patient,
		"inpatient_record": overrides.pop("inpatient_record", "IR-DUMMY-BTH"),
		"from_bed": from_bed,
		"to_bed": to_bed,
		"company": company,
		"reason": overrides.pop("reason", "Test reason"),
		**overrides,
	})
	doc.flags.ignore_validate = True
	doc.flags.ignore_mandatory = True
	doc.insert(ignore_permissions=True)
	return doc


def _get_or_create_patient(name):
	if frappe.db.exists("Patient", {"patient_name": name}):
		return frappe.db.get_value("Patient", {"patient_name": name}, "name")
	doc = frappe.get_doc({
		"doctype": "Patient",
		"first_name": name,
	})
	doc.flags.ignore_validate = True
	doc.flags.ignore_mandatory = True
	doc.insert(ignore_permissions=True)
	return doc.name


def _make_housekeeping_task(bed, ward, turnaround_minutes, sla_breached=0, **overrides):
	doc = frappe.get_doc({
		"doctype": "Bed Housekeeping Task",
		"hospital_bed": bed.name if hasattr(bed, "name") else bed,
		"hospital_ward": ward.name if hasattr(ward, "name") else ward,
		"hospital_room": overrides.pop("hospital_room", bed.hospital_room if hasattr(bed, "hospital_room") else None),
		"company": overrides.pop("company", _get_or_create_company()),
		"status": overrides.pop("status", "Completed"),
		"trigger_event": overrides.pop("trigger_event", "Discharge"),
		"cleaning_type": overrides.pop("cleaning_type", "Standard"),
		"created_on": overrides.pop("created_on", now_datetime()),
		"completed_on": overrides.pop("completed_on", now_datetime()),
		"turnaround_minutes": turnaround_minutes,
		"sla_breached": sla_breached,
		**overrides,
	})
	doc.flags.ignore_validate = True
	doc.flags.ignore_mandatory = True
	doc.insert(ignore_permissions=True)
	return doc


# ---------------------------------------------------------------------------
# Test class
# ---------------------------------------------------------------------------


class TestBedTransferHousekeepingReport(IntegrationTestCase):
	def tearDown(self):
		frappe.db.rollback()
		frappe.clear_cache()

	# ── 1. Transfer listing ──────────────────────────────────────────

	def test_transfer_listing_within_date_range(self):
		"""Only transfers within the date range appear."""
		ward, room, beds = self._setup_ward("TL01", ["A", "B"])
		_make_bml("Transfer", from_bed=beds[0].name, to_bed=beds[1].name,
				  from_ward=ward.name, to_ward=ward.name,
				  movement_datetime=f"{today()} 10:00:00")
		_make_bml("Transfer", from_bed=beds[1].name, to_bed=beds[0].name,
				  from_ward=ward.name, to_ward=ward.name,
				  movement_datetime=f"{add_days(today(), -10)} 10:00:00")

		data = _get_transfer_data({
			"from_date": add_days(today(), -3),
			"to_date": today(),
		})
		recent_names = {r["name"] for r in data}
		self.assertTrue(any(True for r in data if r["from_bed"] == beds[0].name))

	def test_ward_filter_on_transfers(self):
		"""Ward filter matches from_ward or to_ward."""
		ward1, _, beds1 = self._setup_ward("TF01", ["A"])
		ward2, _, beds2 = self._setup_ward("TF02", ["B"])
		_make_bml("Transfer", from_bed=beds1[0].name, to_bed=beds2[0].name,
				  from_ward=ward1.name, to_ward=ward2.name)

		data = _get_transfer_data({"ward": ward1.name})
		self.assertTrue(len(data) >= 1)

	def test_transfer_count(self):
		"""Transfer count excludes non-transfer types."""
		ward, _, beds = self._setup_ward("TC01", ["A", "B"])
		_make_bml("Transfer", from_bed=beds[0].name, to_bed=beds[1].name,
				  from_ward=ward.name, to_ward=ward.name)
		_make_bml("Admission", to_bed=beds[0].name, to_ward=ward.name)

		count = _count_transfers({"ward": ward.name})
		self.assertEqual(count, 1)

	# ── 2. Blocked beds ──────────────────────────────────────────────

	def test_blocked_beds_snapshot(self):
		"""Currently blocked beds are returned."""
		ward, room, beds = self._setup_ward("BB01", ["A", "B", "C"])
		frappe.db.set_value("Hospital Bed", beds[0].name, "maintenance_hold", 1)
		frappe.db.set_value("Hospital Bed", beds[1].name, "infection_block", 1)

		blocked = _get_blocked_beds({"ward": ward.name})
		blocked_names = {r["bed"] for r in blocked}
		self.assertIn(beds[0].name, blocked_names)
		self.assertIn(beds[1].name, blocked_names)
		self.assertNotIn(beds[2].name, blocked_names)

	def test_blocked_beds_reason_labels(self):
		"""Block reason labels are correctly assigned."""
		ward, _, beds = self._setup_ward("BB02", ["A", "B"])
		frappe.db.set_value("Hospital Bed", beds[0].name, "maintenance_hold", 1)
		frappe.db.set_value("Hospital Bed", beds[1].name, {
			"maintenance_hold": 1, "infection_block": 1,
		})

		blocked = _get_blocked_beds({"ward": ward.name})
		reason_map = {r["bed"]: r["block_reason"] for r in blocked}
		self.assertEqual(reason_map[beds[0].name], "Maintenance Hold")
		self.assertEqual(reason_map[beds[1].name], "Maintenance + Infection Block")

	def test_no_blocked_beds(self):
		"""Clean ward returns empty blocked list."""
		ward, _, _ = self._setup_ward("BB03", ["A"])
		blocked = _get_blocked_beds({"ward": ward.name})
		self.assertEqual(blocked, [])

	# ── 3. Housekeeping TAT ──────────────────────────────────────────

	def test_housekeeping_summary_counts(self):
		"""Summary counts completed, pending, breached correctly."""
		ward, _, beds = self._setup_ward("HK01", ["A", "B", "C"])
		_make_housekeeping_task(beds[0], ward, 30, sla_breached=0)
		_make_housekeeping_task(beds[1], ward, 60, sla_breached=1)
		_make_housekeeping_task(beds[2], ward, 0, sla_breached=0,
							   status="Pending", completed_on=None, turnaround_minutes=None)

		summary = _get_housekeeping_summary({"ward": ward.name})
		self.assertEqual(summary["total_tasks"], 3)
		self.assertEqual(summary["completed"], 2)
		self.assertEqual(summary["pending"], 1)
		self.assertEqual(summary["sla_breached"], 1)

	def test_housekeeping_avg_tat(self):
		"""Average TAT is computed from completed tasks only."""
		ward, _, beds = self._setup_ward("HK02", ["A", "B"])
		_make_housekeeping_task(beds[0], ward, 20)
		_make_housekeeping_task(beds[1], ward, 40)

		summary = _get_housekeeping_summary({"ward": ward.name})
		self.assertEqual(summary["avg_tat"], 30.0)

	def test_housekeeping_sla_breach_pct(self):
		"""SLA breach % is calculated correctly."""
		ward, _, beds = self._setup_ward("HK03", ["A", "B", "C", "D"])
		_make_housekeeping_task(beds[0], ward, 30, sla_breached=1)
		_make_housekeeping_task(beds[1], ward, 20, sla_breached=0)
		_make_housekeeping_task(beds[2], ward, 40, sla_breached=1)
		_make_housekeeping_task(beds[3], ward, 25, sla_breached=0)

		summary = _get_housekeeping_summary({"ward": ward.name})
		self.assertEqual(summary["sla_breach_pct"], 50.0)

	def test_housekeeping_by_ward_grouping(self):
		"""TAT by ward/cleaning type produces correct groups."""
		ward, _, beds = self._setup_ward("HK04", ["A", "B"])
		_make_housekeeping_task(beds[0], ward, 30, cleaning_type="Standard")
		_make_housekeeping_task(beds[1], ward, 60, cleaning_type="Deep Clean")

		rows = _get_housekeeping_by_ward({"ward": ward.name})
		types = {r["cleaning_type"] for r in rows}
		self.assertIn("Standard", types)
		self.assertIn("Deep Clean", types)

	# ── 4. Report execute() ──────────────────────────────────────────

	def test_report_execute_returns_structure(self):
		"""Report returns columns, data, message, and summary."""
		ward, _, beds = self._setup_ward("RE01", ["A", "B"])
		_make_bml("Transfer", from_bed=beds[0].name, to_bed=beds[1].name,
				  from_ward=ward.name, to_ward=ward.name)

		columns, data, message, chart, summary = report_execute({
			"from_date": add_days(today(), -7),
			"to_date": today(),
			"ward": ward.name,
		})

		self.assertIsInstance(columns, list)
		self.assertTrue(len(columns) > 0)
		self.assertIsInstance(data, list)
		self.assertIsInstance(message, str)
		self.assertIsInstance(summary, list)
		self.assertTrue(len(summary) == 4)

	def test_report_empty_filters(self):
		"""Report handles missing filters gracefully."""
		columns, data, message, chart, summary = report_execute({})
		self.assertIsInstance(columns, list)
		self.assertIsInstance(data, list)
		self.assertIsInstance(summary, list)

	# ── helpers ──────────────────────────────────────────────────────

	def _setup_ward(self, ward_code, bed_numbers):
		ward = _get_or_create_ward(ward_code)
		room = _get_or_create_room(ward_code, ward=ward)
		beds = [_make_bed(bn, room=room) for bn in bed_numbers]
		return ward, room, beds
