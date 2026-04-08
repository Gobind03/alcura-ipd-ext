"""Tests for the ADT Census Service and Report (US-K3).

Covers: opening census, admissions, transfers in/out, discharges, deaths,
closing census formula, same-day edge cases, multi-ward, ward filter,
empty day, and report execute() entry point.
"""

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import add_days, today

from alcura_ipd_ext.alcura_ipd_extensions.report.adt_census.adt_census import (
	execute as report_execute,
)
from alcura_ipd_ext.services.adt_census_service import (
	get_adt_census,
	get_adt_totals,
)


# ---------------------------------------------------------------------------
# Factories
# ---------------------------------------------------------------------------


def _get_or_create_company(abbr="TAD", name="Test ADT Hospital Pvt Ltd"):
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


def _get_or_create_hsut(name="Test ADT Bed Type", inpatient_occupancy=1):
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
	ward_doc = ward or _get_or_create_ward("ADT01")
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
	room_doc = room or _get_or_create_room("ADT01")
	room_name = room_doc.name if hasattr(room_doc, "name") else room_doc
	doc = frappe.get_doc({
		"doctype": "Hospital Bed",
		"bed_number": bed_number,
		"hospital_room": room_name,
		**overrides,
	})
	doc.insert()
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


def _make_ir(patient_name, company=None, **overrides):
	"""Create a minimal Inpatient Record."""
	patient = _get_or_create_patient(patient_name)
	company = company or _get_or_create_company()
	ir = frappe.get_doc({
		"doctype": "Inpatient Record",
		"patient": patient,
		"company": company,
		"scheduled_date": overrides.pop("scheduled_date", today()),
		"status": overrides.pop("status", "Admitted"),
		**overrides,
	})
	ir.flags.ignore_validate = True
	ir.flags.ignore_mandatory = True
	ir.insert(ignore_permissions=True)
	return ir


def _make_bml(movement_type, ir, from_bed=None, to_bed=None, **overrides):
	"""Create a Bed Movement Log entry linked to an IR."""
	doc = frappe.get_doc({
		"doctype": "Bed Movement Log",
		"movement_type": movement_type,
		"movement_datetime": overrides.pop("movement_datetime", f"{today()} 10:00:00"),
		"patient": ir.patient,
		"patient_name": overrides.pop("patient_name", ir.patient_name if hasattr(ir, "patient_name") else ""),
		"inpatient_record": ir.name,
		"from_bed": from_bed,
		"to_bed": to_bed,
		"company": ir.company,
		**overrides,
	})
	doc.flags.ignore_validate = True
	doc.flags.ignore_mandatory = True
	doc.insert(ignore_permissions=True)
	return doc


def _setup_ward(ward_code, bed_numbers):
	ward = _get_or_create_ward(ward_code)
	room = _get_or_create_room(ward_code, ward=ward)
	beds = [_make_bed(bn, room=room) for bn in bed_numbers]
	return ward, room, beds


# ---------------------------------------------------------------------------
# Test class
# ---------------------------------------------------------------------------


class TestAdtCensusService(IntegrationTestCase):
	def tearDown(self):
		frappe.db.rollback()
		frappe.clear_cache()

	# ── 1. Basic admissions count ────────────────────────────────────

	def test_admission_counted(self):
		"""Admission BML on census date is counted."""
		ward, _, beds = _setup_ward("AD01", ["A"])
		ir = _make_ir("ADT Patient 1")
		_make_bml("Admission", ir, to_bed=beds[0].name,
				  to_ward=ward.name,
				  movement_datetime=f"{today()} 09:00:00")

		rows = get_adt_census({"date": today(), "ward": ward.name})
		self.assertEqual(len(rows), 1)
		self.assertEqual(rows[0]["admissions"], 1)

	# ── 2. Discharge counted ────────────────────────────────────────

	def test_discharge_counted(self):
		"""Discharge BML on census date is counted."""
		ward, _, beds = _setup_ward("DC01", ["A"])
		ir = _make_ir("ADT Patient 2")

		yesterday = add_days(today(), -1)
		_make_bml("Admission", ir, to_bed=beds[0].name,
				  to_ward=ward.name,
				  movement_datetime=f"{yesterday} 10:00:00")
		_make_bml("Discharge", ir, from_bed=beds[0].name,
				  from_ward=ward.name,
				  movement_datetime=f"{today()} 14:00:00")

		rows = get_adt_census({"date": today(), "ward": ward.name})
		self.assertEqual(rows[0]["discharges"], 1)

	# ── 3. Transfer in/out ──────────────────────────────────────────

	def test_transfer_in_out(self):
		"""Transfer from ward A to ward B counts as out for A, in for B."""
		ward_a, _, beds_a = _setup_ward("TR01", ["A"])
		ward_b, _, beds_b = _setup_ward("TR02", ["B"])
		ir = _make_ir("ADT Patient 3")

		yesterday = add_days(today(), -1)
		_make_bml("Admission", ir, to_bed=beds_a[0].name,
				  to_ward=ward_a.name,
				  movement_datetime=f"{yesterday} 08:00:00")
		_make_bml("Transfer", ir,
				  from_bed=beds_a[0].name, to_bed=beds_b[0].name,
				  from_ward=ward_a.name, to_ward=ward_b.name,
				  movement_datetime=f"{today()} 11:00:00")

		rows_a = get_adt_census({"date": today(), "ward": ward_a.name})
		rows_b = get_adt_census({"date": today(), "ward": ward_b.name})

		self.assertEqual(rows_a[0]["transfers_out"], 1)
		self.assertEqual(rows_b[0]["transfers_in"], 1)

	# ── 4. Opening census ───────────────────────────────────────────

	def test_opening_census(self):
		"""Patient admitted yesterday and still in ward counts in opening."""
		ward, _, beds = _setup_ward("OC01", ["A"])
		ir = _make_ir("ADT Patient 4")

		yesterday = add_days(today(), -1)
		_make_bml("Admission", ir, to_bed=beds[0].name,
				  to_ward=ward.name,
				  movement_datetime=f"{yesterday} 10:00:00")

		rows = get_adt_census({"date": today(), "ward": ward.name})
		self.assertEqual(rows[0]["opening_census"], 1)

	def test_opening_census_excludes_discharged_before_midnight(self):
		"""Patient discharged yesterday is NOT in today's opening census."""
		ward, _, beds = _setup_ward("OC02", ["A"])
		ir = _make_ir("ADT Patient 5")

		yesterday = add_days(today(), -1)
		_make_bml("Admission", ir, to_bed=beds[0].name,
				  to_ward=ward.name,
				  movement_datetime=f"{yesterday} 08:00:00")
		_make_bml("Discharge", ir, from_bed=beds[0].name,
				  from_ward=ward.name,
				  movement_datetime=f"{yesterday} 20:00:00")

		rows = get_adt_census({"date": today(), "ward": ward.name})
		self.assertEqual(rows[0]["opening_census"], 0)

	# ── 5. Closing census formula ───────────────────────────────────

	def test_closing_equals_opening_plus_movements(self):
		"""Closing = opening + admissions + transfers_in - transfers_out - discharges."""
		ward, _, beds = _setup_ward("CL01", ["A", "B"])
		ir1 = _make_ir("ADT Patient 6")
		ir2 = _make_ir("ADT Patient 7")

		yesterday = add_days(today(), -1)
		# ir1 admitted yesterday (opening = 1)
		_make_bml("Admission", ir1, to_bed=beds[0].name,
				  to_ward=ward.name,
				  movement_datetime=f"{yesterday} 10:00:00")
		# ir2 admitted today (admissions = 1)
		_make_bml("Admission", ir2, to_bed=beds[1].name,
				  to_ward=ward.name,
				  movement_datetime=f"{today()} 09:00:00")

		rows = get_adt_census({"date": today(), "ward": ward.name})
		row = rows[0]
		expected_closing = (
			row["opening_census"] + row["admissions"] + row["transfers_in"]
			- row["transfers_out"] - row["discharges"]
		)
		self.assertEqual(row["closing_census"], expected_closing)
		self.assertEqual(row["closing_census"], 2)

	# ── 6. Same-day admit + discharge ───────────────────────────────

	def test_same_day_admit_discharge(self):
		"""Same-day admission and discharge both counted."""
		ward, _, beds = _setup_ward("SD01", ["A"])
		ir = _make_ir("ADT Patient 8")

		_make_bml("Admission", ir, to_bed=beds[0].name,
				  to_ward=ward.name,
				  movement_datetime=f"{today()} 08:00:00")
		_make_bml("Discharge", ir, from_bed=beds[0].name,
				  from_ward=ward.name,
				  movement_datetime=f"{today()} 18:00:00")

		rows = get_adt_census({"date": today(), "ward": ward.name})
		self.assertEqual(rows[0]["admissions"], 1)
		self.assertEqual(rows[0]["discharges"], 1)
		self.assertEqual(rows[0]["closing_census"], 0)

	# ── 7. Same-day admit + transfer ────────────────────────────────

	def test_same_day_admit_transfer(self):
		"""Admission in A, transfer from A to B — same day."""
		ward_a, _, beds_a = _setup_ward("ST01", ["A"])
		ward_b, _, beds_b = _setup_ward("ST02", ["B"])
		ir = _make_ir("ADT Patient 9")

		_make_bml("Admission", ir, to_bed=beds_a[0].name,
				  to_ward=ward_a.name,
				  movement_datetime=f"{today()} 08:00:00")
		_make_bml("Transfer", ir,
				  from_bed=beds_a[0].name, to_bed=beds_b[0].name,
				  from_ward=ward_a.name, to_ward=ward_b.name,
				  movement_datetime=f"{today()} 14:00:00")

		rows_a = get_adt_census({"date": today(), "ward": ward_a.name})
		rows_b = get_adt_census({"date": today(), "ward": ward_b.name})

		self.assertEqual(rows_a[0]["admissions"], 1)
		self.assertEqual(rows_a[0]["transfers_out"], 1)
		self.assertEqual(rows_a[0]["closing_census"], 0)

		self.assertEqual(rows_b[0]["transfers_in"], 1)
		self.assertEqual(rows_b[0]["closing_census"], 1)

	# ── 8. Empty day ────────────────────────────────────────────────

	def test_empty_day_returns_zeros(self):
		"""Ward with no activity returns all zeros."""
		ward, _, _ = _setup_ward("ED01", ["A"])

		rows = get_adt_census({"date": today(), "ward": ward.name})
		self.assertEqual(len(rows), 1)
		row = rows[0]
		self.assertEqual(row["opening_census"], 0)
		self.assertEqual(row["admissions"], 0)
		self.assertEqual(row["discharges"], 0)
		self.assertEqual(row["closing_census"], 0)

	# ── 9. Ward filter ──────────────────────────────────────────────

	def test_ward_filter_limits_results(self):
		"""Only the filtered ward appears."""
		ward_a, _, _ = _setup_ward("WF01", ["A"])
		ward_b, _, _ = _setup_ward("WF02", ["B"])

		rows = get_adt_census({"date": today(), "ward": ward_a.name})
		ward_names = {r["ward"] for r in rows}
		self.assertIn(ward_a.name, ward_names)
		self.assertNotIn(ward_b.name, ward_names)

	# ── 10. get_adt_totals ──────────────────────────────────────────

	def test_totals_computation(self):
		"""Totals aggregate across all rows correctly."""
		rows = [
			{"opening_census": 5, "admissions": 2, "transfers_in": 1,
			 "transfers_out": 1, "discharges": 3, "deaths": 0, "closing_census": 4},
			{"opening_census": 3, "admissions": 1, "transfers_in": 0,
			 "transfers_out": 0, "discharges": 1, "deaths": 1, "closing_census": 3},
		]
		totals = get_adt_totals(rows)
		self.assertEqual(totals["opening_census"], 8)
		self.assertEqual(totals["admissions"], 3)
		self.assertEqual(totals["discharges"], 4)
		self.assertEqual(totals["closing_census"], 7)
		self.assertEqual(totals["net_movement"], -1)

	# ── 11. Report execute() ────────────────────────────────────────

	def test_report_execute_returns_structure(self):
		"""Report returns columns, data, chart, and summary."""
		ward, _, beds = _setup_ward("RE01", ["A"])
		ir = _make_ir("ADT Report Patient")
		_make_bml("Admission", ir, to_bed=beds[0].name,
				  to_ward=ward.name,
				  movement_datetime=f"{today()} 10:00:00")

		columns, data, msg, chart, summary = report_execute({
			"date": today(),
			"ward": ward.name,
		})

		self.assertIsInstance(columns, list)
		self.assertTrue(len(columns) > 0)
		self.assertIsInstance(data, list)
		self.assertIsInstance(summary, list)
		self.assertEqual(len(summary), 6)

	def test_report_chart_structure(self):
		"""Report produces a stacked bar chart."""
		ward, _, beds = _setup_ward("RE02", ["A"])
		ir = _make_ir("ADT Chart Patient")
		_make_bml("Admission", ir, to_bed=beds[0].name,
				  to_ward=ward.name)

		_, data, _, chart, _ = report_execute({"date": today(), "ward": ward.name})
		if data:
			self.assertIsNotNone(chart)
			self.assertEqual(chart["type"], "bar")
			self.assertTrue(chart["barOptions"]["stacked"])

	def test_report_empty_no_chart(self):
		"""Empty data returns None chart."""
		_, _, _, chart, _ = report_execute({"date": "2020-01-01", "ward": "NONEXISTENT"})
		self.assertIsNone(chart)
