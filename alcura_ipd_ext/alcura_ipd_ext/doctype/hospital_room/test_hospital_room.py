"""Tests for Hospital Room DocType.

Covers: autoname, validation, uniqueness, HSU auto-creation, capacity,
deletion protection, and disable behaviour.
"""

import frappe
import pytest
from frappe.tests import IntegrationTestCase


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


def _get_or_create_hsut(name="Test IPD Room Type", inpatient_occupancy=1, **kw):
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


def _get_or_create_ward(ward_code="GW01", company=None, **overrides):
	company = company or _get_or_create_company()
	abbr = frappe.get_cached_value("Company", company, "abbr")
	ward_name_key = f"{abbr}-{ward_code.upper()}"
	if frappe.db.exists("Hospital Ward", ward_name_key):
		return frappe.get_doc("Hospital Ward", ward_name_key)
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


def _make_room(room_number="101", ward=None, **overrides):
	ward_doc = ward or _get_or_create_ward()
	hsut = overrides.pop("service_unit_type", None) or _get_or_create_hsut()
	doc = frappe.get_doc(
		{
			"doctype": "Hospital Room",
			"room_number": room_number,
			"room_name": overrides.pop("room_name", f"Room {room_number}"),
			"hospital_ward": ward_doc.name if hasattr(ward_doc, "name") else ward_doc,
			"service_unit_type": hsut,
			**overrides,
		}
	)
	doc.insert()
	return doc


class TestHospitalRoom(IntegrationTestCase):
	"""Integration tests for Hospital Room."""

	def tearDown(self):
		frappe.db.rollback()

	# ── 1. CRUD ──────────────────────────────────────────────────────

	def test_create_room(self):
		"""A valid Hospital Room saves without error."""
		room = _make_room(room_number="CR01")
		self.assertTrue(room.name)
		self.assertEqual(room.is_active, 1)

	def test_autoname_format(self):
		"""Name follows {ward_name}-{ROOM_NUMBER} pattern."""
		ward = _get_or_create_ward(ward_code="AN01")
		room = _make_room(room_number="201", ward=ward)
		self.assertEqual(room.name, f"{ward.name}-201")

	# ── 2. Room number normalisation ─────────────────────────────────

	def test_room_number_uppercased(self):
		"""room_number is normalised to uppercase on save."""
		room = _make_room(room_number="a1b")
		self.assertEqual(room.room_number, "A1B")

	# ── 3-4. Room number uniqueness ──────────────────────────────────

	def test_room_number_unique_per_ward(self):
		"""Duplicate room_number within the same ward raises ValidationError."""
		ward = _get_or_create_ward(ward_code="UQ01")
		_make_room(room_number="DUP1", ward=ward)
		with self.assertRaises(frappe.ValidationError):
			_make_room(room_number="DUP1", ward=ward)

	def test_room_number_same_number_different_ward(self):
		"""Same room_number in different wards is allowed."""
		company = _get_or_create_company()
		w1 = _get_or_create_ward(ward_code="DW01", company=company)
		w2 = _get_or_create_ward(ward_code="DW02", company=company)
		r1 = _make_room(room_number="301", ward=w1)
		r2 = _make_room(room_number="301", ward=w2)
		self.assertNotEqual(r1.name, r2.name)

	# ── 5-6. Room number format validation ───────────────────────────

	def test_room_number_rejects_spaces(self):
		"""Room numbers with spaces are rejected."""
		with self.assertRaises(frappe.ValidationError):
			_make_room(room_number="10 1")

	def test_room_number_rejects_special_chars(self):
		"""Room numbers with special characters are rejected."""
		with self.assertRaises(frappe.ValidationError):
			_make_room(room_number="10@1")

	def test_room_number_allows_hyphens(self):
		"""Hyphens are valid in room numbers."""
		room = _make_room(room_number="ICU-1")
		self.assertEqual(room.room_number, "ICU-1")

	# ── 7. Service unit type validation ──────────────────────────────

	def test_hsut_must_have_inpatient_occupancy(self):
		"""A service unit type without inpatient_occupancy is rejected."""
		non_ipd = _get_or_create_hsut(
			name="Test Consulting Type", inpatient_occupancy=0, allow_appointments=1
		)
		with self.assertRaises(frappe.ValidationError):
			_make_room(room_number="BAD01", service_unit_type=non_ipd)

	# ── 8. Ward must be active ───────────────────────────────────────

	def test_ward_must_be_active(self):
		"""Cannot add a room to an inactive ward."""
		ward = _get_or_create_ward(ward_code="INACT1")
		ward.is_active = 0
		ward.save()
		with self.assertRaises(frappe.ValidationError):
			_make_room(room_number="401", ward=ward)

	# ── 9. Company fetched from ward ─────────────────────────────────

	def test_company_fetched_from_ward(self):
		"""Company is populated from the ward on save."""
		company = _get_or_create_company()
		ward = _get_or_create_ward(ward_code="CF01", company=company)
		room = _make_room(room_number="501", ward=ward)
		self.assertEqual(room.company, company)

	# ── 10-11. Capacity defaults ─────────────────────────────────────

	def test_capacity_defaults_to_zero(self):
		"""New room has zero bed counts."""
		room = _make_room(room_number="CAP01")
		self.assertEqual(room.total_beds, 0)
		self.assertEqual(room.occupied_beds, 0)
		self.assertEqual(room.available_beds, 0)

	def test_available_beds_computed(self):
		"""available_beds = total_beds - occupied_beds on save."""
		room = _make_room(room_number="CAP02")
		frappe.db.set_value("Hospital Room", room.name, {"total_beds": 4, "occupied_beds": 1})
		room.reload()
		room.save()
		self.assertEqual(room.available_beds, 3)

	# ── 12. Deletion protection ──────────────────────────────────────

	def test_delete_blocked_when_beds_exist(self):
		"""Cannot delete a room that has beds."""
		room = _make_room(room_number="DEL01")
		frappe.get_doc(
			{
				"doctype": "Hospital Bed",
				"bed_number": "A",
				"hospital_room": room.name,
			}
		).insert()
		with self.assertRaises(frappe.LinkExistsError):
			frappe.delete_doc("Hospital Room", room.name, force=True)

	# ── 13. Disable allowed ──────────────────────────────────────────

	def test_disable_allowed(self):
		"""Room can be deactivated when no beds."""
		room = _make_room(room_number="DIS01")
		room.is_active = 0
		room.save()
		self.assertEqual(room.is_active, 0)

	# ── 14. HSU auto-creation ────────────────────────────────────────

	def test_hsu_group_auto_created(self):
		"""When ward has an HSU group, room auto-creates an HSU group node."""
		company = _get_or_create_company()
		ward = _get_or_create_ward(ward_code="HSUC1", company=company)

		ward_hsu = frappe.get_doc(
			{
				"doctype": "Healthcare Service Unit",
				"healthcare_service_unit_name": f"HSU Ward {ward.ward_code}",
				"is_group": 1,
				"company": company,
			}
		)
		ward_hsu.insert(ignore_permissions=True)
		ward.healthcare_service_unit = ward_hsu.name
		ward.save()

		room = _make_room(room_number="HSU01", ward=ward)
		room.reload()
		self.assertTrue(room.healthcare_service_unit)
		hsu = frappe.get_doc("Healthcare Service Unit", room.healthcare_service_unit)
		self.assertEqual(hsu.is_group, 1)
		self.assertEqual(hsu.parent_healthcare_service_unit, ward_hsu.name)

	def test_hsu_not_created_without_ward_hsu(self):
		"""When ward has no HSU group, room's healthcare_service_unit stays blank."""
		ward = _get_or_create_ward(ward_code="NOHSU1")
		ward.healthcare_service_unit = None
		ward.save()

		room = _make_room(room_number="NOHSU01", ward=ward)
		room.reload()
		self.assertFalse(room.healthcare_service_unit)

	# ── 15. Ward deletion blocked when rooms exist ───────────────────

	def test_ward_deletion_blocked_when_rooms_exist(self):
		"""Ward cannot be deleted when rooms are linked."""
		ward = _get_or_create_ward(ward_code="WDB01")
		_make_room(room_number="WR01", ward=ward)
		with self.assertRaises(frappe.LinkExistsError):
			frappe.delete_doc("Hospital Ward", ward.name, force=True)
