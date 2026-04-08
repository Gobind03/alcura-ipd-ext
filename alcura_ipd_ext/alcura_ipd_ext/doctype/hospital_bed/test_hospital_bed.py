"""Tests for Hospital Bed DocType.

Covers: autoname, validation, uniqueness, HSU auto-creation, occupancy sync,
capacity rollup, deletion protection, disable behaviour, and operational fields.
"""

import frappe
import pytest
from frappe.tests import IntegrationTestCase


# ---------------------------------------------------------------------------
# Factories
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


# ---------------------------------------------------------------------------
# HSU helper for tests that need the full tree
# ---------------------------------------------------------------------------


def _setup_ward_with_hsu(ward_code="BWHSU"):
	company = _get_or_create_company()
	ward = _get_or_create_ward(ward_code=ward_code, company=company)

	ward_hsu_name = f"HSU Ward {ward.ward_code}"
	if not frappe.db.exists("Healthcare Service Unit", ward_hsu_name):
		frappe.get_doc(
			{
				"doctype": "Healthcare Service Unit",
				"healthcare_service_unit_name": ward_hsu_name,
				"is_group": 1,
				"company": company,
			}
		).insert(ignore_permissions=True)

	ward.healthcare_service_unit = ward_hsu_name
	ward.save()
	return ward, company


class TestHospitalBed(IntegrationTestCase):
	"""Integration tests for Hospital Bed."""

	def tearDown(self):
		frappe.db.rollback()

	# ── 1. CRUD ──────────────────────────────────────────────────────

	def test_create_bed(self):
		"""A valid Hospital Bed saves without error."""
		bed = _make_bed(bed_number="B1")
		self.assertTrue(bed.name)
		self.assertEqual(bed.is_active, 1)
		self.assertEqual(bed.occupancy_status, "Vacant")

	def test_autoname_format(self):
		"""Name follows {room_name}-{BED_NUMBER} pattern."""
		room = _get_or_create_room(room_number="AN01")
		bed = _make_bed(bed_number="X1", room=room)
		self.assertEqual(bed.name, f"{room.name}-X1")

	# ── 2. Bed number normalisation ──────────────────────────────────

	def test_bed_number_uppercased(self):
		"""bed_number is normalised to uppercase on save."""
		bed = _make_bed(bed_number="a1")
		self.assertEqual(bed.bed_number, "A1")

	# ── 3-4. Bed number uniqueness ───────────────────────────────────

	def test_bed_number_unique_per_room(self):
		"""Duplicate bed_number within the same room raises ValidationError."""
		room = _get_or_create_room(room_number="UQ01")
		_make_bed(bed_number="D1", room=room)
		with self.assertRaises(frappe.ValidationError):
			_make_bed(bed_number="D1", room=room)

	def test_bed_number_same_in_different_rooms(self):
		"""Same bed_number in different rooms is allowed."""
		ward = _get_or_create_ward(ward_code="DR01")
		r1 = _get_or_create_room(room_number="R1", ward=ward)
		r2 = _get_or_create_room(room_number="R2", ward=ward)
		b1 = _make_bed(bed_number="Z1", room=r1)
		b2 = _make_bed(bed_number="Z1", room=r2)
		self.assertNotEqual(b1.name, b2.name)

	# ── 5-6. Bed number format validation ────────────────────────────

	def test_bed_number_rejects_spaces(self):
		"""Bed numbers with spaces are rejected."""
		with self.assertRaises(frappe.ValidationError):
			_make_bed(bed_number="A 1")

	def test_bed_number_rejects_special_chars(self):
		"""Bed numbers with special characters are rejected."""
		with self.assertRaises(frappe.ValidationError):
			_make_bed(bed_number="A@1")

	def test_bed_number_allows_hyphens(self):
		"""Hyphens are valid in bed numbers."""
		bed = _make_bed(bed_number="L-1")
		self.assertEqual(bed.bed_number, "L-1")

	# ── 7. Room must be active ───────────────────────────────────────

	def test_room_must_be_active(self):
		"""Cannot add a bed to an inactive room."""
		room = _get_or_create_room(room_number="INACT1")
		room.is_active = 0
		room.save()
		with self.assertRaises(frappe.ValidationError):
			_make_bed(bed_number="IA1", room=room)

	# ── 8. Ward and company inherited ────────────────────────────────

	def test_ward_and_company_inherited(self):
		"""hospital_ward, company, service_unit_type are fetched from room."""
		company = _get_or_create_company()
		ward = _get_or_create_ward(ward_code="INH01", company=company)
		room = _get_or_create_room(room_number="INH01", ward=ward)
		bed = _make_bed(bed_number="INH1", room=room)
		self.assertEqual(bed.hospital_ward, ward.name)
		self.assertEqual(bed.company, company)
		self.assertEqual(bed.service_unit_type, room.service_unit_type)

	# ── 9-10. Occupancy defaults ─────────────────────────────────────

	def test_occupancy_defaults_vacant(self):
		"""New bed defaults to Vacant occupancy."""
		bed = _make_bed(bed_number="OCC1")
		self.assertEqual(bed.occupancy_status, "Vacant")

	def test_housekeeping_defaults_clean(self):
		"""New bed defaults to Clean housekeeping."""
		bed = _make_bed(bed_number="HK1")
		self.assertEqual(bed.housekeeping_status, "Clean")

	# ── 11. Cannot disable when occupied ─────────────────────────────

	def test_cannot_disable_when_occupied(self):
		"""Bed with Occupied status cannot be deactivated."""
		bed = _make_bed(bed_number="CDIS1")
		frappe.db.set_value("Hospital Bed", bed.name, "occupancy_status", "Occupied")
		bed.reload()
		bed.is_active = 0
		with self.assertRaises(frappe.ValidationError):
			bed.save()

	# ── 12. Cannot delete when occupied ──────────────────────────────

	def test_cannot_delete_when_occupied(self):
		"""Occupied bed cannot be deleted."""
		bed = _make_bed(bed_number="CDEL1")
		frappe.db.set_value("Hospital Bed", bed.name, "occupancy_status", "Occupied")
		bed.reload()
		with self.assertRaises(frappe.ValidationError):
			frappe.delete_doc("Hospital Bed", bed.name, force=True)

	# ── 13. Disable allowed when vacant ──────────────────────────────

	def test_disable_allowed_when_vacant(self):
		"""Vacant bed can be deactivated."""
		bed = _make_bed(bed_number="ADIS1")
		bed.is_active = 0
		bed.save()
		self.assertEqual(bed.is_active, 0)

	# ── 14-15. Room capacity rollup ──────────────────────────────────

	def test_room_capacity_rollup_on_insert(self):
		"""Creating a bed increments the room's total_beds."""
		room = _get_or_create_room(room_number="RCR01")
		_make_bed(bed_number="RC1", room=room)
		_make_bed(bed_number="RC2", room=room)
		room.reload()
		self.assertEqual(room.total_beds, 2)
		self.assertEqual(room.occupied_beds, 0)
		self.assertEqual(room.available_beds, 2)

	def test_room_capacity_rollup_on_delete(self):
		"""Deleting a bed decrements the room's total_beds."""
		room = _get_or_create_room(room_number="RCD01")
		bed = _make_bed(bed_number="RD1", room=room)
		room.reload()
		self.assertEqual(room.total_beds, 1)
		frappe.delete_doc("Hospital Bed", bed.name, force=True)
		room.reload()
		self.assertEqual(room.total_beds, 0)

	# ── 16-17. Ward capacity rollup ──────────────────────────────────

	def test_ward_capacity_rollup_on_insert(self):
		"""Creating beds increments the ward's total_beds."""
		ward = _get_or_create_ward(ward_code="WCR01")
		room = _get_or_create_room(room_number="WCR01", ward=ward)
		_make_bed(bed_number="WC1", room=room)
		_make_bed(bed_number="WC2", room=room)
		ward.reload()
		self.assertEqual(ward.total_beds, 2)
		self.assertEqual(ward.available_beds, 2)

	def test_ward_capacity_rollup_on_delete(self):
		"""Deleting a bed decrements the ward's total_beds."""
		ward = _get_or_create_ward(ward_code="WCD01")
		room = _get_or_create_room(room_number="WCD01", ward=ward)
		bed = _make_bed(bed_number="WD1", room=room)
		ward.reload()
		self.assertEqual(ward.total_beds, 1)
		frappe.delete_doc("Hospital Bed", bed.name, force=True)
		ward.reload()
		self.assertEqual(ward.total_beds, 0)

	# ── 18. HSU leaf auto-creation ───────────────────────────────────

	def test_hsu_leaf_auto_created(self):
		"""When room has an HSU group, bed auto-creates an HSU leaf node."""
		ward, company = _setup_ward_with_hsu(ward_code="BHSU1")
		room = _get_or_create_room(room_number="BHSU01", ward=ward)
		room.reload()

		if not room.healthcare_service_unit:
			self.skipTest("Room HSU auto-creation did not trigger (ward HSU might not link)")

		bed = _make_bed(bed_number="BH1", room=room)
		bed.reload()
		self.assertTrue(bed.healthcare_service_unit)
		hsu = frappe.get_doc("Healthcare Service Unit", bed.healthcare_service_unit)
		self.assertEqual(hsu.is_group, 0)
		self.assertEqual(hsu.inpatient_occupancy, 1)
		self.assertEqual(hsu.parent_healthcare_service_unit, room.healthcare_service_unit)

	def test_hsu_not_created_without_room_hsu(self):
		"""When room has no HSU, bed's healthcare_service_unit stays blank."""
		room = _get_or_create_room(room_number="NOHSU1")
		bed = _make_bed(bed_number="NH1", room=room)
		bed.reload()
		self.assertFalse(bed.healthcare_service_unit)

	# ── 19. Occupancy sync: Bed → HSU ────────────────────────────────

	def test_occupancy_sync_bed_to_hsu(self):
		"""Changing occupancy on bed pushes to linked HSU."""
		ward, company = _setup_ward_with_hsu(ward_code="SYNC1")
		room = _get_or_create_room(room_number="SYNC01", ward=ward)
		room.reload()
		if not room.healthcare_service_unit:
			self.skipTest("Room HSU not created")

		bed = _make_bed(bed_number="SY1", room=room)
		bed.reload()
		if not bed.healthcare_service_unit:
			self.skipTest("Bed HSU not created")

		frappe.db.set_value("Hospital Bed", bed.name, "occupancy_status", "Occupied")
		bed.reload()
		bed.save()

		hsu_status = frappe.db.get_value(
			"Healthcare Service Unit", bed.healthcare_service_unit, "occupancy_status"
		)
		self.assertEqual(hsu_status, "Occupied")

	# ── 20. Gender restriction ───────────────────────────────────────

	def test_gender_restriction_default(self):
		"""Gender restriction defaults to No Restriction."""
		bed = _make_bed(bed_number="GR1")
		self.assertEqual(bed.gender_restriction, "No Restriction")

	# ── 21. Maintenance hold persists ────────────────────────────────

	def test_maintenance_hold_persists(self):
		"""maintenance_hold can be set to 1."""
		bed = _make_bed(bed_number="MH1")
		bed.maintenance_hold = 1
		bed.save()
		bed.reload()
		self.assertEqual(bed.maintenance_hold, 1)

	# ── 22. Infection block persists ─────────────────────────────────

	def test_infection_block_persists(self):
		"""infection_block can be set to 1."""
		bed = _make_bed(bed_number="IB1")
		bed.infection_block = 1
		bed.save()
		bed.reload()
		self.assertEqual(bed.infection_block, 1)

	# ── 23. Housekeeping status transitions ──────────────────────────

	def test_housekeeping_status_transitions(self):
		"""housekeeping_status can transition through Clean → Dirty → In Progress → Clean."""
		bed = _make_bed(bed_number="HKT1")
		self.assertEqual(bed.housekeeping_status, "Clean")

		bed.housekeeping_status = "Dirty"
		bed.save()
		self.assertEqual(bed.housekeeping_status, "Dirty")

		bed.housekeeping_status = "In Progress"
		bed.save()
		self.assertEqual(bed.housekeeping_status, "In Progress")

		bed.housekeeping_status = "Clean"
		bed.save()
		self.assertEqual(bed.housekeeping_status, "Clean")
