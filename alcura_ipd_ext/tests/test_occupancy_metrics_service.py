"""Tests for the occupancy metrics service and Bed Occupancy Dashboard report.

Covers: ward occupancy aggregation, room-type grouping, critical care
summary, average LOS, bed turnaround, filter behaviour, edge cases,
and the report execute() entry point.
"""

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import add_days, today

from alcura_ipd_ext.alcura_ipd_extensions.report.bed_occupancy_dashboard.bed_occupancy_dashboard import (
	execute as report_execute,
)
from alcura_ipd_ext.services.occupancy_metrics_service import (
	get_avg_los_by_ward,
	get_bed_turnaround_by_ward,
	get_critical_care_summary,
	get_overall_summary,
	get_room_type_occupancy_summary,
	get_ward_occupancy_summary,
)


# ---------------------------------------------------------------------------
# Factories
# ---------------------------------------------------------------------------


def _get_or_create_company(abbr="TOC", name="Test Occ Hospital Pvt Ltd"):
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


def _get_or_create_hsut(name="Test Occ Bed Type", inpatient_occupancy=1, **kw):
	if frappe.db.exists("Healthcare Service Unit Type", name):
		return name
	doc = frappe.get_doc({
		"doctype": "Healthcare Service Unit Type",
		"healthcare_service_unit_type": name,
		"inpatient_occupancy": inpatient_occupancy,
		**kw,
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
	ward_doc = ward or _get_or_create_ward("OCC01")
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
	room_doc = room or _get_or_create_room("OCC01")
	room_name = room_doc.name if hasattr(room_doc, "name") else room_doc
	doc = frappe.get_doc({
		"doctype": "Hospital Bed",
		"bed_number": bed_number,
		"hospital_room": room_name,
		**overrides,
	})
	doc.insert()
	return doc


def _setup_ward_with_beds(ward_code, room_number, bed_numbers, ward_overrides=None, room_overrides=None):
	ward = _get_or_create_ward(ward_code=ward_code, **(ward_overrides or {}))
	room = _get_or_create_room(room_number=room_number, ward=ward, **(room_overrides or {}))
	beds = [_make_bed(bed_number=bn, room=room) for bn in bed_numbers]
	return ward, room, beds


def _save_policy(**overrides):
	doc = frappe.get_doc("IPD Bed Policy")
	for key, val in overrides.items():
		doc.set(key, val)
	doc.save()
	frappe.clear_cache()
	return doc


def _make_ir(patient_name, ward, scheduled_date=None, **overrides):
	"""Create a minimal Inpatient Record with Admitted status for LOS tests."""
	patient = _get_or_create_patient(patient_name)
	ir = frappe.get_doc({
		"doctype": "Inpatient Record",
		"patient": patient,
		"company": overrides.pop("company", _get_or_create_company()),
		"scheduled_date": scheduled_date or today(),
		"status": "Admitted",
		"custom_current_ward": ward,
		**overrides,
	})
	ir.flags.ignore_validate = True
	ir.flags.ignore_mandatory = True
	ir.insert(ignore_permissions=True)
	return ir


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


def _make_housekeeping_task(bed_doc, ward, turnaround_minutes, **overrides):
	doc = frappe.get_doc({
		"doctype": "Bed Housekeeping Task",
		"hospital_bed": bed_doc.name if hasattr(bed_doc, "name") else bed_doc,
		"hospital_ward": ward.name if hasattr(ward, "name") else ward,
		"hospital_room": overrides.pop("hospital_room", bed_doc.hospital_room if hasattr(bed_doc, "hospital_room") else None),
		"company": overrides.pop("company", _get_or_create_company()),
		"status": "Completed",
		"trigger_event": overrides.pop("trigger_event", "Discharge"),
		"cleaning_type": overrides.pop("cleaning_type", "Standard"),
		"created_on": overrides.pop("created_on", frappe.utils.now_datetime()),
		"completed_on": overrides.pop("completed_on", frappe.utils.now_datetime()),
		"turnaround_minutes": turnaround_minutes,
		**overrides,
	})
	doc.flags.ignore_validate = True
	doc.flags.ignore_mandatory = True
	doc.insert(ignore_permissions=True)
	return doc


# ---------------------------------------------------------------------------
# Test class
# ---------------------------------------------------------------------------


class TestOccupancyMetricsService(IntegrationTestCase):
	def tearDown(self):
		frappe.db.rollback()
		frappe.clear_cache()

	# ── 1. Ward occupancy aggregation ────────────────────────────────

	def test_ward_occupancy_counts(self):
		"""Mixed bed statuses produce correct per-ward counts."""
		ward, room, beds = _setup_ward_with_beds("WO01", "WO01", ["A", "B", "C", "D"])
		frappe.db.set_value("Hospital Bed", beds[0].name, "occupancy_status", "Occupied")
		frappe.db.set_value("Hospital Bed", beds[1].name, "occupancy_status", "Reserved")
		frappe.db.set_value("Hospital Bed", beds[2].name, "maintenance_hold", 1)

		rows = get_ward_occupancy_summary({"ward": ward.name})
		self.assertEqual(len(rows), 1)
		row = rows[0]
		self.assertEqual(row["total_beds"], 4)
		self.assertEqual(row["occupied"], 1)
		self.assertEqual(row["reserved"], 1)
		self.assertEqual(row["blocked"], 1)
		self.assertEqual(row["vacant"], 1)

	def test_ward_occupancy_percentage(self):
		"""Occupancy % is computed correctly."""
		ward, _, beds = _setup_ward_with_beds("WO02", "WO02", ["A", "B", "C", "D", "E"])
		frappe.db.set_value("Hospital Bed", beds[0].name, "occupancy_status", "Occupied")
		frappe.db.set_value("Hospital Bed", beds[1].name, "occupancy_status", "Occupied")

		rows = get_ward_occupancy_summary({"ward": ward.name})
		self.assertEqual(rows[0]["occupancy_pct"], 40.0)

	def test_ward_filter_narrows_result(self):
		"""Only the filtered ward appears in results."""
		ward1, _, _ = _setup_ward_with_beds("WO03", "WO03", ["A"])
		ward2, _, _ = _setup_ward_with_beds("WO04", "WO04", ["B"])

		rows = get_ward_occupancy_summary({"ward": ward1.name})
		ward_names = {r["ward"] for r in rows}
		self.assertIn(ward1.name, ward_names)
		self.assertNotIn(ward2.name, ward_names)

	def test_empty_ward_returns_empty(self):
		"""Non-existent ward returns no rows."""
		rows = get_ward_occupancy_summary({"ward": "NONEXISTENT"})
		self.assertEqual(rows, [])

	# ── 2. Room type grouping ────────────────────────────────────────

	def test_room_type_grouping(self):
		"""Beds grouped by room type with correct counts."""
		hsut1 = _get_or_create_hsut("Occ ICU Type", inpatient_occupancy=1)
		hsut2 = _get_or_create_hsut("Occ General Type", inpatient_occupancy=1)

		ward = _get_or_create_ward(ward_code="RT01")
		room1 = _get_or_create_room("RT01", ward=ward, service_unit_type=hsut1)
		room2 = _get_or_create_room("RT02", ward=ward, service_unit_type=hsut2)
		b1 = _make_bed("R1", room=room1)
		b2 = _make_bed("R2", room=room2)
		frappe.db.set_value("Hospital Bed", b1.name, "occupancy_status", "Occupied")

		rows = get_room_type_occupancy_summary({"ward": ward.name})
		rt_map = {r["room_type"]: r for r in rows}
		self.assertEqual(rt_map[hsut1]["occupied"], 1)
		self.assertEqual(rt_map[hsut2]["occupied"], 0)

	# ── 3. Critical care summary ─────────────────────────────────────

	def test_critical_care_summary(self):
		"""Critical care summary only counts ICU wards."""
		_setup_ward_with_beds("CC01", "CC01", ["A", "B"], ward_overrides={"is_critical_care": 1})
		_setup_ward_with_beds("CC02", "CC02", ["C"], ward_overrides={"is_critical_care": 0})

		summary = get_critical_care_summary()
		self.assertGreaterEqual(summary["total"], 2)

	def test_critical_care_empty(self):
		"""No critical care beds returns zeros."""
		summary = get_critical_care_summary({"ward": "NONEXISTENT"})
		self.assertEqual(summary["total"], 0)
		self.assertEqual(summary["occupancy_pct"], 0.0)

	# ── 4. Average LOS ──────────────────────────────────────────────

	def test_avg_los_computation(self):
		"""Average LOS is correctly computed from scheduled_date to today."""
		ward, _, _ = _setup_ward_with_beds("LO01", "LO01", ["A"])
		five_days_ago = add_days(today(), -4)
		ten_days_ago = add_days(today(), -9)

		_make_ir("LOS Patient 1", ward.name, scheduled_date=five_days_ago)
		_make_ir("LOS Patient 2", ward.name, scheduled_date=ten_days_ago)

		los_map = get_avg_los_by_ward({"ward": ward.name})
		self.assertIn(ward.name, los_map)
		self.assertEqual(los_map[ward.name], 8.0)

	def test_avg_los_empty(self):
		"""No admitted patients returns empty map."""
		los_map = get_avg_los_by_ward({"ward": "NONEXISTENT"})
		self.assertEqual(los_map, {})

	# ── 5. Bed turnaround ───────────────────────────────────────────

	def test_bed_turnaround_avg(self):
		"""Average turnaround computed from completed tasks."""
		ward, _, beds = _setup_ward_with_beds("TA01", "TA01", ["A", "B"])
		_make_housekeeping_task(beds[0], ward, turnaround_minutes=30)
		_make_housekeeping_task(beds[1], ward, turnaround_minutes=60)

		tat_map = get_bed_turnaround_by_ward({"ward": ward.name})
		self.assertIn(ward.name, tat_map)
		self.assertEqual(tat_map[ward.name], 45.0)

	def test_bed_turnaround_empty(self):
		"""No completed tasks returns empty map."""
		tat_map = get_bed_turnaround_by_ward({"ward": "NONEXISTENT"})
		self.assertEqual(tat_map, {})

	# ── 6. Overall summary ──────────────────────────────────────────

	def test_overall_summary_counts(self):
		"""Overall summary produces correct totals."""
		ward, _, beds = _setup_ward_with_beds("OS01", "OS01", ["A", "B", "C"])
		frappe.db.set_value("Hospital Bed", beds[0].name, "occupancy_status", "Occupied")
		frappe.db.set_value("Hospital Bed", beds[1].name, "housekeeping_status", "Dirty")

		summary = get_overall_summary({"ward": ward.name})
		self.assertEqual(summary["total"], 3)
		self.assertEqual(summary["occupied"], 1)
		self.assertEqual(summary["blocked"], 1)
		self.assertEqual(summary["available"], 1)
		self.assertAlmostEqual(summary["occupancy_pct"], 33.3, places=1)

	# ── 7. Report execute() ─────────────────────────────────────────

	def test_report_execute_ward_view(self):
		"""Report returns columns, data, and summary for ward grouping."""
		_setup_ward_with_beds("RE01", "RE01", ["A"])
		columns, data, _, chart, summary = report_execute({"group_by": "Ward"})

		self.assertIsInstance(columns, list)
		self.assertTrue(len(columns) > 0)
		col_names = {c["fieldname"] for c in columns}
		self.assertIn("ward", col_names)
		self.assertIn("occupancy_pct", col_names)
		self.assertIsInstance(summary, list)

	def test_report_execute_room_type_view(self):
		"""Report returns room type columns when grouped by Room Type."""
		_setup_ward_with_beds("RE02", "RE02", ["A"])
		columns, data, _, chart, summary = report_execute({"group_by": "Room Type"})

		col_names = {c["fieldname"] for c in columns}
		self.assertIn("room_type", col_names)
		self.assertNotIn("ward", col_names)

	def test_report_chart_returned(self):
		"""Report produces a chart when data is available."""
		_setup_ward_with_beds("RE03", "RE03", ["A"])
		_, data, _, chart, _ = report_execute({})

		if data:
			self.assertIsNotNone(chart)
			self.assertEqual(chart["type"], "bar")

	def test_report_empty_data_no_chart(self):
		"""Report returns None chart when no data matches."""
		_, _, _, chart, _ = report_execute({"ward": "NONEXISTENT"})
		self.assertIsNone(chart)
