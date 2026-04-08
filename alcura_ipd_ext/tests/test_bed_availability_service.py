"""Tests for the bed availability service and Live Bed Board report.

Covers: policy-based exclusions, user filters (ward, room type, floor,
critical care, gender, isolation, show_unavailable), payer eligibility
(Strict / Advisory / Ignore), summary counts, and the report execute()
entry point.
"""

import frappe
from frappe.tests import IntegrationTestCase

from alcura_ipd_ext.alcura_ipd_ext.report.live_bed_board.live_bed_board import (
	execute as report_execute,
)
from alcura_ipd_ext.services.bed_availability_service import (
	get_available_beds,
	get_bed_board_summary,
)

# ---------------------------------------------------------------------------
# Factories (duplicated from test_hospital_bed for isolation)
# ---------------------------------------------------------------------------


def _get_or_create_company(abbr="TST", name="Test Hospital Pvt Ltd"):
	if frappe.db.exists("Company", name):
		return name
	company = frappe.get_doc(
		{
			"doctype": "Company",
			"company_name": name,
			"abbr": abbr,
			"default_currency": "INR",
			"country": "India",
		}
	)
	company.insert(ignore_if_duplicate=True)
	return company.name


def _get_or_create_hsut(name="Test IPD Bed Type", inpatient_occupancy=1, **kw):
	if frappe.db.exists("Healthcare Service Unit Type", name):
		return name
	doc = frappe.get_doc(
		{
			"doctype": "Healthcare Service Unit Type",
			"healthcare_service_unit_type": name,
			"inpatient_occupancy": inpatient_occupancy,
			**kw,
		}
	)
	doc.flags.ignore_validate = True
	doc.insert(ignore_if_duplicate=True)
	return doc.name


def _get_or_create_ward(ward_code="BW01", company=None, **overrides):
	company = company or _get_or_create_company()
	abbr = frappe.get_cached_value("Company", company, "abbr")
	ward_key = f"{abbr}-{ward_code.upper()}"
	if frappe.db.exists("Hospital Ward", ward_key):
		return frappe.get_doc("Hospital Ward", ward_key)
	doc = frappe.get_doc(
		{
			"doctype": "Hospital Ward",
			"ward_code": ward_code,
			"ward_name": overrides.pop("ward_name", f"Test Ward {ward_code}"),
			"company": company,
			"ward_classification": overrides.pop("ward_classification", "General"),
			**overrides,
		}
	)
	doc.insert()
	return doc


def _get_or_create_room(room_number="101", ward=None, **overrides):
	ward_doc = ward or _get_or_create_ward()
	ward_name = ward_doc.name if hasattr(ward_doc, "name") else ward_doc
	room_key = f"{ward_name}-{room_number.upper()}"
	if frappe.db.exists("Hospital Room", room_key):
		return frappe.get_doc("Hospital Room", room_key)

	hsut = overrides.pop("service_unit_type", None) or _get_or_create_hsut()
	doc = frappe.get_doc(
		{
			"doctype": "Hospital Room",
			"room_number": room_number,
			"room_name": overrides.pop("room_name", f"Room {room_number}"),
			"hospital_ward": ward_name,
			"service_unit_type": hsut,
			**overrides,
		}
	)
	doc.insert()
	return doc


def _make_bed(bed_number="A", room=None, **overrides):
	room_doc = room or _get_or_create_room()
	room_name = room_doc.name if hasattr(room_doc, "name") else room_doc
	doc = frappe.get_doc(
		{
			"doctype": "Hospital Bed",
			"bed_number": bed_number,
			"hospital_room": room_name,
			**overrides,
		}
	)
	doc.insert()
	return doc


def _save_policy(**overrides):
	"""Save IPD Bed Policy with overrides."""
	doc = frappe.get_doc("IPD Bed Policy")
	for key, val in overrides.items():
		doc.set(key, val)
	doc.save()
	frappe.clear_cache()
	return doc


def _make_tariff(room_type, payer_type="Cash", payer=None, rate=1000, company=None):
	"""Create a Room Tariff Mapping with a single Room Rent item."""
	company = company or _get_or_create_company()

	pl_name = "Test IPD Price List"
	if not frappe.db.exists("Price List", pl_name):
		frappe.get_doc({
			"doctype": "Price List",
			"price_list_name": pl_name,
			"selling": 1,
		}).insert(ignore_permissions=True)

	item_code = "Room Rent"
	if not frappe.db.exists("Item", item_code):
		frappe.get_doc({
			"doctype": "Item",
			"item_code": item_code,
			"item_name": "Room Rent",
			"item_group": "Services",
		}).insert(ignore_permissions=True)

	customer = None
	if payer and payer_type in ("Corporate", "TPA"):
		if not frappe.db.exists("Customer", payer):
			frappe.get_doc({
				"doctype": "Customer",
				"customer_name": payer,
				"customer_group": "All Customer Groups",
				"territory": "All Territories",
			}).insert(ignore_permissions=True)
		customer = payer

	doc = frappe.get_doc({
		"doctype": "Room Tariff Mapping",
		"room_type": room_type,
		"company": company,
		"payer_type": payer_type,
		"payer": customer,
		"valid_from": "2020-01-01",
		"price_list": pl_name,
		"is_active": 1,
		"tariff_items": [
			{
				"charge_type": "Room Rent",
				"item_code": item_code,
				"rate": rate,
				"uom": "Nos",
				"billing_frequency": "Per Day",
			}
		],
	})
	doc.insert(ignore_permissions=True)
	return doc


# ---------------------------------------------------------------------------
# Test class
# ---------------------------------------------------------------------------


class TestBedAvailabilityService(IntegrationTestCase):
	def tearDown(self):
		frappe.db.rollback()
		frappe.clear_cache()

	# ── helpers ──────────────────────────────────────────────────────

	def _setup_ward_with_beds(
		self,
		ward_code,
		room_number,
		bed_numbers,
		ward_overrides=None,
		room_overrides=None,
	):
		"""Create a ward with a room and beds, returning (ward, room, beds)."""
		ward = _get_or_create_ward(ward_code=ward_code, **(ward_overrides or {}))
		room = _get_or_create_room(
			room_number=room_number, ward=ward, **(room_overrides or {})
		)
		beds = []
		for bn in bed_numbers:
			beds.append(_make_bed(bed_number=bn, room=room))
		return ward, room, beds

	# ── 1. Basic availability ────────────────────────────────────────

	def test_vacant_beds_returned(self):
		"""Vacant, clean, active beds appear in the result."""
		_save_policy(
			exclude_dirty_beds=0, exclude_cleaning_beds=0,
			exclude_maintenance_beds=0, exclude_infection_blocked=0,
		)
		_, _, beds = self._setup_ward_with_beds("AV01", "AV01", ["A1", "A2"])
		result = get_available_beds()
		bed_names = {r["bed"] for r in result}
		for b in beds:
			self.assertIn(b.name, bed_names)

	def test_occupied_beds_excluded_by_default(self):
		"""Occupied beds are excluded when show_unavailable is off."""
		_save_policy(
			exclude_dirty_beds=0, exclude_cleaning_beds=0,
			exclude_maintenance_beds=0, exclude_infection_blocked=0,
		)
		_, _, beds = self._setup_ward_with_beds("OC01", "OC01", ["O1", "O2"])
		frappe.db.set_value("Hospital Bed", beds[0].name, "occupancy_status", "Occupied")

		result = get_available_beds()
		bed_names = {r["bed"] for r in result}
		self.assertNotIn(beds[0].name, bed_names)
		self.assertIn(beds[1].name, bed_names)

	def test_show_unavailable_includes_occupied(self):
		"""With show_unavailable=1, occupied beds appear."""
		_save_policy(
			exclude_dirty_beds=0, exclude_cleaning_beds=0,
			exclude_maintenance_beds=0, exclude_infection_blocked=0,
		)
		_, _, beds = self._setup_ward_with_beds("SU01", "SU01", ["S1", "S2"])
		frappe.db.set_value("Hospital Bed", beds[0].name, "occupancy_status", "Occupied")

		result = get_available_beds({"show_unavailable": 1})
		bed_names = {r["bed"] for r in result}
		self.assertIn(beds[0].name, bed_names)
		self.assertIn(beds[1].name, bed_names)

	def test_inactive_beds_excluded(self):
		"""Inactive beds are never shown."""
		_save_policy(
			exclude_dirty_beds=0, exclude_cleaning_beds=0,
			exclude_maintenance_beds=0, exclude_infection_blocked=0,
		)
		_, _, beds = self._setup_ward_with_beds("IA01", "IA01", ["I1", "I2"])
		frappe.db.set_value("Hospital Bed", beds[0].name, "is_active", 0)

		result = get_available_beds({"show_unavailable": 1})
		bed_names = {r["bed"] for r in result}
		self.assertNotIn(beds[0].name, bed_names)

	# ── 2. Policy exclusions ─────────────────────────────────────────

	def test_dirty_beds_excluded_by_policy(self):
		"""Dirty beds excluded when policy says so."""
		_save_policy(exclude_dirty_beds=1, exclude_cleaning_beds=0,
			exclude_maintenance_beds=0, exclude_infection_blocked=0)
		_, _, beds = self._setup_ward_with_beds("DR01", "DR01", ["D1", "D2"])
		frappe.db.set_value("Hospital Bed", beds[0].name, "housekeeping_status", "Dirty")

		result = get_available_beds()
		bed_names = {r["bed"] for r in result}
		self.assertNotIn(beds[0].name, bed_names)
		self.assertIn(beds[1].name, bed_names)

	def test_dirty_beds_included_when_policy_off(self):
		"""Dirty beds included when exclusion is disabled."""
		_save_policy(exclude_dirty_beds=0, exclude_cleaning_beds=0,
			exclude_maintenance_beds=0, exclude_infection_blocked=0)
		_, _, beds = self._setup_ward_with_beds("DI01", "DI01", ["D1"])
		frappe.db.set_value("Hospital Bed", beds[0].name, "housekeeping_status", "Dirty")

		result = get_available_beds()
		bed_names = {r["bed"] for r in result}
		self.assertIn(beds[0].name, bed_names)

	def test_cleaning_beds_excluded_by_policy(self):
		"""Beds being cleaned excluded when policy says so."""
		_save_policy(exclude_dirty_beds=0, exclude_cleaning_beds=1,
			exclude_maintenance_beds=0, exclude_infection_blocked=0)
		_, _, beds = self._setup_ward_with_beds("CL01", "CL01", ["C1"])
		frappe.db.set_value(
			"Hospital Bed", beds[0].name, "housekeeping_status", "In Progress"
		)

		result = get_available_beds()
		bed_names = {r["bed"] for r in result}
		self.assertNotIn(beds[0].name, bed_names)

	def test_maintenance_beds_excluded_by_policy(self):
		"""Maintenance-hold beds excluded when policy says so."""
		_save_policy(exclude_dirty_beds=0, exclude_cleaning_beds=0,
			exclude_maintenance_beds=1, exclude_infection_blocked=0)
		_, _, beds = self._setup_ward_with_beds("MT01", "MT01", ["M1"])
		frappe.db.set_value("Hospital Bed", beds[0].name, "maintenance_hold", 1)

		result = get_available_beds()
		bed_names = {r["bed"] for r in result}
		self.assertNotIn(beds[0].name, bed_names)

	def test_infection_blocked_excluded_by_policy(self):
		"""Infection-blocked beds excluded when policy says so."""
		_save_policy(exclude_dirty_beds=0, exclude_cleaning_beds=0,
			exclude_maintenance_beds=0, exclude_infection_blocked=1)
		_, _, beds = self._setup_ward_with_beds("IB01", "IB01", ["I1"])
		frappe.db.set_value("Hospital Bed", beds[0].name, "infection_block", 1)

		result = get_available_beds()
		bed_names = {r["bed"] for r in result}
		self.assertNotIn(beds[0].name, bed_names)

	# ── 3. User filters ─────────────────────────────────────────────

	def test_filter_by_ward(self):
		"""Ward filter returns only beds in that ward."""
		_save_policy(exclude_dirty_beds=0, exclude_cleaning_beds=0,
			exclude_maintenance_beds=0, exclude_infection_blocked=0)
		ward1, _, beds1 = self._setup_ward_with_beds("FW01", "FW01", ["W1"])
		ward2, _, beds2 = self._setup_ward_with_beds("FW02", "FW02", ["W2"])

		result = get_available_beds({"ward": ward1.name})
		bed_names = {r["bed"] for r in result}
		self.assertIn(beds1[0].name, bed_names)
		self.assertNotIn(beds2[0].name, bed_names)

	def test_filter_by_room_type(self):
		"""Room type filter returns only matching beds."""
		_save_policy(exclude_dirty_beds=0, exclude_cleaning_beds=0,
			exclude_maintenance_beds=0, exclude_infection_blocked=0)
		hsut1 = _get_or_create_hsut("ICU Type RT", inpatient_occupancy=1)
		hsut2 = _get_or_create_hsut("General Type RT", inpatient_occupancy=1)

		ward = _get_or_create_ward(ward_code="RT01")
		room1 = _get_or_create_room(
			room_number="RT01", ward=ward, service_unit_type=hsut1
		)
		room2 = _get_or_create_room(
			room_number="RT02", ward=ward, service_unit_type=hsut2
		)
		bed1 = _make_bed(bed_number="R1", room=room1)
		bed2 = _make_bed(bed_number="R2", room=room2)

		result = get_available_beds({"room_type": hsut1})
		bed_names = {r["bed"] for r in result}
		self.assertIn(bed1.name, bed_names)
		self.assertNotIn(bed2.name, bed_names)

	def test_filter_by_floor(self):
		"""Floor filter returns only beds on that floor."""
		_save_policy(exclude_dirty_beds=0, exclude_cleaning_beds=0,
			exclude_maintenance_beds=0, exclude_infection_blocked=0)
		ward = _get_or_create_ward(ward_code="FL01")
		room1 = _get_or_create_room(room_number="FL01", ward=ward, floor="1")
		room2 = _get_or_create_room(room_number="FL02", ward=ward, floor="2")
		bed1 = _make_bed(bed_number="F1", room=room1)
		bed2 = _make_bed(bed_number="F2", room=room2)

		result = get_available_beds({"floor": "1"})
		bed_names = {r["bed"] for r in result}
		self.assertIn(bed1.name, bed_names)
		self.assertNotIn(bed2.name, bed_names)

	def test_filter_critical_care_only(self):
		"""Critical care filter shows only ICU/HDU wards."""
		_save_policy(exclude_dirty_beds=0, exclude_cleaning_beds=0,
			exclude_maintenance_beds=0, exclude_infection_blocked=0)
		_, _, beds_gen = self._setup_ward_with_beds(
			"CC01", "CC01", ["G1"],
			ward_overrides={"ward_classification": "General"},
		)
		_, _, beds_icu = self._setup_ward_with_beds(
			"CC02", "CC02", ["I1"],
			ward_overrides={"ward_classification": "ICU"},
		)

		result = get_available_beds({"critical_care_only": 1})
		bed_names = {r["bed"] for r in result}
		self.assertNotIn(beds_gen[0].name, bed_names)
		self.assertIn(beds_icu[0].name, bed_names)

	def test_filter_isolation_only(self):
		"""Isolation filter shows only isolation-capable wards."""
		_save_policy(exclude_dirty_beds=0, exclude_cleaning_beds=0,
			exclude_maintenance_beds=0, exclude_infection_blocked=0)
		_, _, beds_no = self._setup_ward_with_beds(
			"IS01", "IS01", ["N1"],
			ward_overrides={"supports_isolation": 0},
		)
		_, _, beds_yes = self._setup_ward_with_beds(
			"IS02", "IS02", ["Y1"],
			ward_overrides={"supports_isolation": 1},
		)

		result = get_available_beds({"isolation_only": 1})
		bed_names = {r["bed"] for r in result}
		self.assertNotIn(beds_no[0].name, bed_names)
		self.assertIn(beds_yes[0].name, bed_names)

	def test_filter_gender_strict(self):
		"""Under Strict gender policy, beds with mismatched restriction are hidden."""
		_save_policy(
			exclude_dirty_beds=0, exclude_cleaning_beds=0,
			exclude_maintenance_beds=0, exclude_infection_blocked=0,
			gender_enforcement="Strict",
		)
		_, _, beds = self._setup_ward_with_beds("GS01", "GS01", ["G1", "G2", "G3"])
		frappe.db.set_value("Hospital Bed", beds[0].name, "gender_restriction", "Male Only")
		frappe.db.set_value("Hospital Bed", beds[1].name, "gender_restriction", "Female Only")
		# beds[2] stays "No Restriction"

		result = get_available_beds({"gender": "Male Only"})
		bed_names = {r["bed"] for r in result}
		self.assertIn(beds[0].name, bed_names)
		self.assertNotIn(beds[1].name, bed_names)
		self.assertIn(beds[2].name, bed_names)

	def test_filter_gender_ignore(self):
		"""Under Ignore gender policy, all beds appear regardless of restriction."""
		_save_policy(
			exclude_dirty_beds=0, exclude_cleaning_beds=0,
			exclude_maintenance_beds=0, exclude_infection_blocked=0,
			gender_enforcement="Ignore",
		)
		_, _, beds = self._setup_ward_with_beds("GI01", "GI01", ["G1", "G2"])
		frappe.db.set_value("Hospital Bed", beds[0].name, "gender_restriction", "Male Only")
		frappe.db.set_value("Hospital Bed", beds[1].name, "gender_restriction", "Female Only")

		result = get_available_beds({"gender": "Male Only"})
		bed_names = {r["bed"] for r in result}
		self.assertIn(beds[0].name, bed_names)
		self.assertIn(beds[1].name, bed_names)

	# ── 4. Availability labels ───────────────────────────────────────

	def test_availability_label_available(self):
		"""Vacant, clean bed gets 'Available' label."""
		_save_policy(exclude_dirty_beds=0, exclude_cleaning_beds=0,
			exclude_maintenance_beds=0, exclude_infection_blocked=0)
		_, _, beds = self._setup_ward_with_beds("LB01", "LB01", ["L1"])
		result = get_available_beds()
		row = next(r for r in result if r["bed"] == beds[0].name)
		self.assertEqual(row["availability"], "Available")

	def test_availability_label_occupied(self):
		"""Occupied bed gets 'Occupied' label."""
		_save_policy(exclude_dirty_beds=0, exclude_cleaning_beds=0,
			exclude_maintenance_beds=0, exclude_infection_blocked=0)
		_, _, beds = self._setup_ward_with_beds("LB02", "LB02", ["L1"])
		frappe.db.set_value("Hospital Bed", beds[0].name, "occupancy_status", "Occupied")
		result = get_available_beds({"show_unavailable": 1})
		row = next(r for r in result if r["bed"] == beds[0].name)
		self.assertEqual(row["availability"], "Occupied")

	def test_availability_label_maintenance(self):
		"""Maintenance-hold bed gets 'Maintenance' label."""
		_save_policy(exclude_dirty_beds=0, exclude_cleaning_beds=0,
			exclude_maintenance_beds=0, exclude_infection_blocked=0)
		_, _, beds = self._setup_ward_with_beds("LB03", "LB03", ["L1"])
		frappe.db.set_value("Hospital Bed", beds[0].name, "maintenance_hold", 1)
		result = get_available_beds()
		row = next(r for r in result if r["bed"] == beds[0].name)
		self.assertEqual(row["availability"], "Maintenance")

	def test_availability_label_dirty(self):
		"""Dirty bed gets 'Dirty' label."""
		_save_policy(exclude_dirty_beds=0, exclude_cleaning_beds=0,
			exclude_maintenance_beds=0, exclude_infection_blocked=0)
		_, _, beds = self._setup_ward_with_beds("LB04", "LB04", ["L1"])
		frappe.db.set_value("Hospital Bed", beds[0].name, "housekeeping_status", "Dirty")
		result = get_available_beds()
		row = next(r for r in result if r["bed"] == beds[0].name)
		self.assertEqual(row["availability"], "Dirty")

	# ── 5. Payer eligibility ─────────────────────────────────────────

	def test_payer_strict_hides_no_tariff(self):
		"""With Strict payer policy, beds without tariff are excluded."""
		_save_policy(
			exclude_dirty_beds=0, exclude_cleaning_beds=0,
			exclude_maintenance_beds=0, exclude_infection_blocked=0,
			enforce_payer_eligibility="Strict",
		)
		hsut1 = _get_or_create_hsut("Tariff Type PE1", inpatient_occupancy=1)
		hsut2 = _get_or_create_hsut("No Tariff Type PE1", inpatient_occupancy=1)

		company = _get_or_create_company()
		ward = _get_or_create_ward(ward_code="PE01")
		room1 = _get_or_create_room(
			room_number="PE01", ward=ward, service_unit_type=hsut1
		)
		room2 = _get_or_create_room(
			room_number="PE02", ward=ward, service_unit_type=hsut2
		)
		bed1 = _make_bed(bed_number="P1", room=room1)
		bed2 = _make_bed(bed_number="P2", room=room2)

		_make_tariff(room_type=hsut1, payer_type="Cash", rate=500, company=company)

		result = get_available_beds({
			"payer_type": "Cash",
			"company": company,
		})
		bed_names = {r["bed"] for r in result}
		self.assertIn(bed1.name, bed_names)
		self.assertNotIn(bed2.name, bed_names)

	def test_payer_advisory_flags_no_tariff(self):
		"""With Advisory payer policy, beds without tariff are shown but flagged."""
		_save_policy(
			exclude_dirty_beds=0, exclude_cleaning_beds=0,
			exclude_maintenance_beds=0, exclude_infection_blocked=0,
			enforce_payer_eligibility="Advisory",
		)
		hsut1 = _get_or_create_hsut("Tariff Type PE2", inpatient_occupancy=1)
		hsut2 = _get_or_create_hsut("No Tariff Type PE2", inpatient_occupancy=1)

		company = _get_or_create_company()
		ward = _get_or_create_ward(ward_code="PE02")
		room1 = _get_or_create_room(
			room_number="PE03", ward=ward, service_unit_type=hsut1
		)
		room2 = _get_or_create_room(
			room_number="PE04", ward=ward, service_unit_type=hsut2
		)
		bed1 = _make_bed(bed_number="P1", room=room1)
		bed2 = _make_bed(bed_number="P2", room=room2)

		_make_tariff(room_type=hsut1, payer_type="Cash", rate=500, company=company)

		result = get_available_beds({
			"payer_type": "Cash",
			"company": company,
		})
		bed_names = {r["bed"] for r in result}
		self.assertIn(bed1.name, bed_names)
		self.assertIn(bed2.name, bed_names)

		row1 = next(r for r in result if r["bed"] == bed1.name)
		row2 = next(r for r in result if r["bed"] == bed2.name)
		self.assertEqual(row1["payer_eligible"], "Yes")
		self.assertEqual(row2["payer_eligible"], "No")
		self.assertEqual(row1["daily_rate"], 500.0)

	def test_payer_ignore_skips_tariff_check(self):
		"""With Ignore payer policy, no tariff check is performed."""
		_save_policy(
			exclude_dirty_beds=0, exclude_cleaning_beds=0,
			exclude_maintenance_beds=0, exclude_infection_blocked=0,
			enforce_payer_eligibility="Ignore",
		)
		_, _, beds = self._setup_ward_with_beds("PI01", "PI01", ["P1"])

		result = get_available_beds({"payer_type": "Cash"})
		bed_names = {r["bed"] for r in result}
		self.assertIn(beds[0].name, bed_names)

		row = next(r for r in result if r["bed"] == beds[0].name)
		self.assertIsNone(row.get("daily_rate"))

	# ── 6. Summary ───────────────────────────────────────────────────

	def test_summary_counts(self):
		"""Summary returns correct total, available, occupied, blocked."""
		_save_policy(
			exclude_dirty_beds=0, exclude_cleaning_beds=0,
			exclude_maintenance_beds=0, exclude_infection_blocked=0,
		)
		_, _, beds = self._setup_ward_with_beds(
			"SM01", "SM01", ["S1", "S2", "S3", "S4"]
		)
		frappe.db.set_value("Hospital Bed", beds[0].name, "occupancy_status", "Occupied")
		frappe.db.set_value("Hospital Bed", beds[1].name, "housekeeping_status", "Dirty")
		frappe.db.set_value("Hospital Bed", beds[2].name, "maintenance_hold", 1)
		# beds[3] stays Clean / Vacant

		summary = get_bed_board_summary({"ward": beds[0].hospital_ward})
		self.assertEqual(summary["total"], 4)
		self.assertEqual(summary["occupied"], 1)
		self.assertEqual(summary["blocked"], 2)
		self.assertEqual(summary["available"], 1)

	# ── 7. Empty result set ──────────────────────────────────────────

	def test_empty_result_handled(self):
		"""No matching beds returns empty list."""
		result = get_available_beds({"ward": "NONEXISTENT-WARD"})
		self.assertEqual(result, [])

	def test_empty_summary_handled(self):
		"""No matching beds returns zero counts."""
		summary = get_bed_board_summary({"ward": "NONEXISTENT-WARD"})
		self.assertEqual(summary["total"], 0)
		self.assertEqual(summary["available"], 0)

	# ── 8. Report execute() ──────────────────────────────────────────

	def test_report_execute_returns_columns_and_data(self):
		"""The report entry point returns a tuple of (columns, data, ...)."""
		_save_policy(
			exclude_dirty_beds=0, exclude_cleaning_beds=0,
			exclude_maintenance_beds=0, exclude_infection_blocked=0,
		)
		_, _, beds = self._setup_ward_with_beds("RP01", "RP01", ["R1"])

		columns, data, _, _, summary = report_execute({})
		self.assertIsInstance(columns, list)
		self.assertTrue(len(columns) > 0)
		self.assertIsInstance(data, list)
		bed_names = {r["bed"] for r in data}
		self.assertIn(beds[0].name, bed_names)
		self.assertIsInstance(summary, list)

	def test_report_payer_columns_appear_with_payer_filter(self):
		"""When payer_type is set, Daily Rate and Payer Eligible columns appear."""
		_save_policy(
			exclude_dirty_beds=0, exclude_cleaning_beds=0,
			exclude_maintenance_beds=0, exclude_infection_blocked=0,
			enforce_payer_eligibility="Ignore",
		)
		_, _, _ = self._setup_ward_with_beds("RP02", "RP02", ["R1"])

		columns, _, _, _, _ = report_execute({"payer_type": "Cash"})
		col_names = {c["fieldname"] for c in columns}
		self.assertIn("daily_rate", col_names)
		self.assertIn("payer_eligible", col_names)

	def test_report_no_payer_columns_without_filter(self):
		"""Without payer_type filter, payer columns are absent."""
		_save_policy(
			exclude_dirty_beds=0, exclude_cleaning_beds=0,
			exclude_maintenance_beds=0, exclude_infection_blocked=0,
		)
		columns, _, _, _, _ = report_execute({})
		col_names = {c["fieldname"] for c in columns}
		self.assertNotIn("daily_rate", col_names)
		self.assertNotIn("payer_eligible", col_names)
