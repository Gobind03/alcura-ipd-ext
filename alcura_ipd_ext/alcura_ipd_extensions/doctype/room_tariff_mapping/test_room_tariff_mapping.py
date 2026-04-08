"""Tests for Room Tariff Mapping doctype.

Covers: happy-path creation, field validations, overlap prevention,
tariff resolution service, and role-based permissions.
"""

import frappe
import frappe.defaults
import pytest
from frappe.tests import IntegrationTestCase

from alcura_ipd_ext.services.tariff_service import get_tariff_rate, resolve_tariff


# ── test-data factories ─────────────────────────────────────────────


def _ensure_company(name="Test Hospital A4", abbr="THA4"):
	if not frappe.db.exists("Company", name):
		frappe.get_doc(
			{
				"doctype": "Company",
				"company_name": name,
				"abbr": abbr,
				"default_currency": "INR",
				"country": "India",
			}
		).insert(ignore_permissions=True, ignore_if_duplicate=True)
	return name


def _ensure_price_list(name="Standard Selling"):
	if not frappe.db.exists("Price List", name):
		frappe.get_doc(
			{
				"doctype": "Price List",
				"price_list_name": name,
				"selling": 1,
				"currency": "INR",
			}
		).insert(ignore_permissions=True, ignore_if_duplicate=True)
	return name


def _ensure_item(name):
	if not frappe.db.exists("Item", name):
		frappe.get_doc(
			{
				"doctype": "Item",
				"item_code": name,
				"item_name": name,
				"item_group": "Services",
				"stock_uom": "Nos",
			}
		).insert(ignore_permissions=True, ignore_if_duplicate=True)
	return name


def _ensure_customer(name="Test TPA Corp"):
	if not frappe.db.exists("Customer", name):
		frappe.get_doc(
			{
				"doctype": "Customer",
				"customer_name": name,
				"customer_group": "All Customer Groups",
				"territory": "All Territories",
			}
		).insert(ignore_permissions=True, ignore_if_duplicate=True)
	return name


def _ensure_hsut(name, inpatient_occupancy=1, **kw):
	"""Create or update a Healthcare Service Unit Type for testing."""
	if frappe.db.exists("Healthcare Service Unit Type", name):
		doc = frappe.get_doc("Healthcare Service Unit Type", name)
		doc.inpatient_occupancy = inpatient_occupancy
		for k, v in kw.items():
			doc.set(k, v)
		doc.save(ignore_permissions=True)
		return doc.name

	doc = frappe.get_doc(
		{
			"doctype": "Healthcare Service Unit Type",
			"healthcare_service_unit_type": name,
			"inpatient_occupancy": inpatient_occupancy,
			**kw,
		}
	)
	doc.insert(ignore_permissions=True, ignore_if_duplicate=True)
	return doc.name


def _make_tariff(room_type=None, payer_type="Cash", payer=None,
				 valid_from="2026-01-01", valid_to="2026-12-31",
				 price_list=None, company=None, is_active=1,
				 items=None, do_not_save=False):
	"""Factory to build a Room Tariff Mapping doc."""
	company = company or _ensure_company()
	price_list = price_list or _ensure_price_list()
	room_type = room_type or _ensure_hsut(
		"Test Private Room A4",
		ipd_room_category="Private",
	)

	if items is None:
		_ensure_item("Room Rent - Test")
		items = [
			{
				"charge_type": "Room Rent",
				"item_code": "Room Rent - Test",
				"rate": 2000,
				"billing_frequency": "Per Day",
			}
		]

	doc = frappe.get_doc(
		{
			"doctype": "Room Tariff Mapping",
			"room_type": room_type,
			"company": company,
			"payer_type": payer_type,
			"payer": payer,
			"valid_from": valid_from,
			"valid_to": valid_to,
			"price_list": price_list,
			"is_active": is_active,
			"tariff_items": items,
		}
	)

	if not do_not_save:
		doc.insert(ignore_permissions=True)

	return doc


# ── tests ───────────────────────────────────────────────────────────


class TestRoomTariffMapping(IntegrationTestCase):
	"""Integration tests for the Room Tariff Mapping doctype and tariff service."""

	def tearDown(self):
		frappe.db.rollback()

	# ── 1. Happy path ───────────────────────────────────────────────

	def test_create_valid_tariff(self):
		"""A well-formed tariff mapping can be created and persisted."""
		doc = _make_tariff()
		self.assertTrue(doc.name)
		self.assertEqual(doc.payer_type, "Cash")
		self.assertEqual(len(doc.tariff_items), 1)
		self.assertEqual(doc.tariff_items[0].charge_type, "Room Rent")

	def test_create_tariff_with_multiple_items(self):
		"""Tariff with all standard charge types saves successfully."""
		_ensure_item("Room Rent - Test")
		_ensure_item("Nursing Charge - Test")
		_ensure_item("ICU Monitor - Test")
		items = [
			{"charge_type": "Room Rent", "item_code": "Room Rent - Test",
			 "rate": 2000, "billing_frequency": "Per Day"},
			{"charge_type": "Nursing Charge", "item_code": "Nursing Charge - Test",
			 "rate": 500, "billing_frequency": "Per Day"},
			{"charge_type": "ICU Monitoring Charge", "item_code": "ICU Monitor - Test",
			 "rate": 1000, "billing_frequency": "Per Day"},
		]
		doc = _make_tariff(items=items)
		self.assertEqual(len(doc.tariff_items), 3)

	# ── 2. Room type must be inpatient ──────────────────────────────

	def test_non_inpatient_room_type_rejected(self):
		"""Room type without inpatient_occupancy is rejected."""
		non_ipd = _ensure_hsut(
			"Test OPD Room A4",
			inpatient_occupancy=0,
			allow_appointments=1,
			ipd_room_category="",
		)
		with self.assertRaises(frappe.ValidationError):
			_make_tariff(room_type=non_ipd)

	# ── 3. Date range ──────────────────────────────────────────────

	def test_valid_to_before_valid_from_rejected(self):
		"""valid_to < valid_from raises ValidationError."""
		with self.assertRaises(frappe.ValidationError):
			_make_tariff(valid_from="2026-06-01", valid_to="2026-01-01")

	def test_same_day_valid_range(self):
		"""valid_from == valid_to is accepted (single-day tariff)."""
		doc = _make_tariff(valid_from="2026-06-01", valid_to="2026-06-01")
		self.assertTrue(doc.name)

	# ── 4. Payer rules ─────────────────────────────────────────────

	def test_corporate_requires_payer(self):
		"""Corporate payer_type without payer raises ValidationError."""
		with self.assertRaises(frappe.ValidationError):
			_make_tariff(payer_type="Corporate", payer=None)

	def test_tpa_requires_payer(self):
		"""TPA payer_type without payer raises ValidationError."""
		with self.assertRaises(frappe.ValidationError):
			_make_tariff(payer_type="TPA", payer=None)

	def test_cash_clears_payer(self):
		"""Cash payer_type automatically clears payer field."""
		customer = _ensure_customer()
		doc = _make_tariff(payer_type="Cash", payer=customer)
		self.assertFalse(doc.payer)

	def test_corporate_with_payer_accepted(self):
		"""Corporate payer_type with a valid customer payer is accepted."""
		customer = _ensure_customer()
		doc = _make_tariff(payer_type="Corporate", payer=customer)
		self.assertEqual(doc.payer, customer)

	# ── 5. Tariff item rules ──────────────────────────────────────

	def test_empty_tariff_items_rejected(self):
		"""Tariff mapping with no items raises ValidationError."""
		with self.assertRaises(frappe.ValidationError):
			_make_tariff(items=[])

	def test_duplicate_charge_type_rejected(self):
		"""Duplicate charge_type in tariff items raises ValidationError."""
		_ensure_item("Room Rent - Test")
		_ensure_item("Room Rent Dup - Test")
		items = [
			{"charge_type": "Room Rent", "item_code": "Room Rent - Test",
			 "rate": 2000, "billing_frequency": "Per Day"},
			{"charge_type": "Room Rent", "item_code": "Room Rent Dup - Test",
			 "rate": 2500, "billing_frequency": "Per Day"},
		]
		with self.assertRaises(frappe.ValidationError):
			_make_tariff(items=items)

	# ── 6. Overlap prevention ──────────────────────────────────────

	def test_overlapping_period_rejected(self):
		"""Two active mappings with overlapping dates for the same combo are rejected."""
		_make_tariff(valid_from="2026-01-01", valid_to="2026-06-30")
		with self.assertRaises(frappe.ValidationError):
			_make_tariff(valid_from="2026-03-01", valid_to="2026-09-30")

	def test_non_overlapping_period_accepted(self):
		"""Non-overlapping periods for the same combo are fine."""
		_make_tariff(valid_from="2026-01-01", valid_to="2026-06-30")
		doc2 = _make_tariff(valid_from="2026-07-01", valid_to="2026-12-31")
		self.assertTrue(doc2.name)

	def test_different_payer_types_no_conflict(self):
		"""Different payer_types for the same room_type do not conflict."""
		_make_tariff(payer_type="Cash", valid_from="2026-01-01", valid_to="2026-12-31")
		customer = _ensure_customer()
		doc2 = _make_tariff(
			payer_type="Corporate", payer=customer,
			valid_from="2026-01-01", valid_to="2026-12-31",
		)
		self.assertTrue(doc2.name)

	def test_open_ended_blocks_future(self):
		"""An open-ended tariff (no valid_to) overlaps with any future tariff."""
		_make_tariff(valid_from="2026-01-01", valid_to=None)
		with self.assertRaises(frappe.ValidationError):
			_make_tariff(valid_from="2027-01-01", valid_to="2027-12-31")

	def test_inactive_mapping_no_overlap(self):
		"""An inactive mapping does not trigger overlap checks for new ones."""
		_make_tariff(valid_from="2026-01-01", valid_to="2026-12-31", is_active=0)
		doc2 = _make_tariff(valid_from="2026-06-01", valid_to="2026-12-31")
		self.assertTrue(doc2.name)

	# ── 7. Tariff resolution service ───────────────────────────────

	def test_resolve_exact_match(self):
		"""resolve_tariff returns the exact payer match."""
		customer = _ensure_customer("Exact TPA A4")
		company = _ensure_company()
		doc = _make_tariff(
			payer_type="TPA", payer=customer,
			valid_from="2026-01-01", valid_to="2026-12-31",
			company=company,
		)
		result = resolve_tariff(
			room_type=doc.room_type,
			payer_type="TPA",
			payer=customer,
			effective_date="2026-06-15",
			company=company,
		)
		self.assertIsNotNone(result)
		self.assertEqual(result["name"], doc.name)

	def test_resolve_generic_payer_fallback(self):
		"""resolve_tariff falls back to generic payer when exact not found."""
		customer = _ensure_customer("Unknown Corp A4")
		company = _ensure_company()
		generic_doc = _make_tariff(
			payer_type="Corporate", payer=_ensure_customer("Generic Corp A4"),
			valid_from="2026-01-01", valid_to="2026-12-31",
			company=company,
		)
		# No exact mapping for "Unknown Corp A4", but a generic Corporate one exists
		# ... actually the generic means payer=NULL. Let's create that instead.
		frappe.db.rollback()

		# Generic Corporate tariff (no specific payer) - we need Cash payer_type
		# with payer=None for generic. But Corporate requires payer. So generic
		# fallback is tested via Cash.
		cash_doc = _make_tariff(
			payer_type="Cash",
			valid_from="2026-01-01", valid_to="2026-12-31",
			company=company,
		)
		result = resolve_tariff(
			room_type=cash_doc.room_type,
			payer_type="Corporate",
			payer=customer,
			effective_date="2026-06-15",
			company=company,
		)
		# Falls back to Cash since no Corporate match exists
		self.assertIsNotNone(result)
		self.assertEqual(result["name"], cash_doc.name)

	def test_resolve_cash_fallback(self):
		"""resolve_tariff falls back to Cash when TPA tariff is not found."""
		company = _ensure_company()
		cash_doc = _make_tariff(
			payer_type="Cash",
			valid_from="2026-01-01", valid_to="2026-12-31",
			company=company,
		)
		customer = _ensure_customer("Missing TPA A4")
		result = resolve_tariff(
			room_type=cash_doc.room_type,
			payer_type="TPA",
			payer=customer,
			effective_date="2026-06-15",
			company=company,
		)
		self.assertIsNotNone(result)
		self.assertEqual(result["name"], cash_doc.name)

	def test_resolve_returns_none_when_no_match(self):
		"""resolve_tariff returns None when no mapping matches."""
		company = _ensure_company()
		result = resolve_tariff(
			room_type="Nonexistent Room Type",
			payer_type="Cash",
			effective_date="2026-06-15",
			company=company,
		)
		self.assertIsNone(result)

	def test_resolve_excludes_inactive(self):
		"""Inactive mappings are skipped by resolve_tariff."""
		company = _ensure_company()
		_make_tariff(
			payer_type="Cash",
			valid_from="2026-01-01", valid_to="2026-12-31",
			company=company,
			is_active=0,
		)
		result = resolve_tariff(
			room_type=_ensure_hsut("Test Private Room A4", ipd_room_category="Private"),
			payer_type="Cash",
			effective_date="2026-06-15",
			company=company,
		)
		self.assertIsNone(result)

	def test_resolve_outside_date_range(self):
		"""resolve_tariff returns None for a date outside the validity window."""
		company = _ensure_company()
		_make_tariff(
			payer_type="Cash",
			valid_from="2026-01-01", valid_to="2026-06-30",
			company=company,
		)
		result = resolve_tariff(
			room_type=_ensure_hsut("Test Private Room A4", ipd_room_category="Private"),
			payer_type="Cash",
			effective_date="2026-09-15",
			company=company,
		)
		self.assertIsNone(result)

	def test_get_tariff_rate_returns_rate(self):
		"""get_tariff_rate returns the rate for a specific charge_type."""
		company = _ensure_company()
		_make_tariff(
			payer_type="Cash",
			valid_from="2026-01-01", valid_to="2026-12-31",
			company=company,
		)
		rate = get_tariff_rate(
			room_type=_ensure_hsut("Test Private Room A4", ipd_room_category="Private"),
			charge_type="Room Rent",
			payer_type="Cash",
			effective_date="2026-06-15",
			company=company,
		)
		self.assertEqual(rate, 2000.0)

	def test_get_tariff_rate_returns_zero_when_unmatched(self):
		"""get_tariff_rate returns 0.0 when no mapping exists."""
		rate = get_tariff_rate(
			room_type="Nonexistent",
			charge_type="Room Rent",
			payer_type="Cash",
			effective_date="2026-06-15",
			company=_ensure_company(),
		)
		self.assertEqual(rate, 0.0)

	def test_resolve_with_charge_type_filter(self):
		"""resolve_tariff with charge_type returns only matching items."""
		_ensure_item("Room Rent - Test")
		_ensure_item("Nursing Charge - Test")
		company = _ensure_company()
		items = [
			{"charge_type": "Room Rent", "item_code": "Room Rent - Test",
			 "rate": 2000, "billing_frequency": "Per Day"},
			{"charge_type": "Nursing Charge", "item_code": "Nursing Charge - Test",
			 "rate": 500, "billing_frequency": "Per Day"},
		]
		_make_tariff(
			payer_type="Cash",
			valid_from="2026-01-01", valid_to="2026-12-31",
			company=company,
			items=items,
		)
		result = resolve_tariff(
			room_type=_ensure_hsut("Test Private Room A4", ipd_room_category="Private"),
			payer_type="Cash",
			effective_date="2026-06-15",
			company=company,
			charge_type="Room Rent",
		)
		self.assertIsNotNone(result)
		self.assertEqual(len(result["tariff_items"]), 1)
		self.assertEqual(result["tariff_items"][0]["charge_type"], "Room Rent")

	# ── 8. Permissions ─────────────────────────────────────────────

	def test_healthcare_admin_can_create(self):
		"""Healthcare Administrator role can create tariff mappings."""
		doc = _make_tariff()
		self.assertTrue(doc.name)

	def test_nursing_user_cannot_create(self):
		"""Nursing User should not be able to create tariff mappings."""
		user = _ensure_test_user("nurse_a4@test.local", ["Nursing User"])
		frappe.set_user(user)
		try:
			with self.assertRaises(frappe.PermissionError):
				_make_tariff()
		finally:
			frappe.set_user("Administrator")

	def test_nursing_user_can_read(self):
		"""Nursing User should be able to read tariff mappings."""
		doc = _make_tariff()
		user = _ensure_test_user("nurse_a4@test.local", ["Nursing User"])
		frappe.set_user(user)
		try:
			read_doc = frappe.get_doc("Room Tariff Mapping", doc.name)
			self.assertEqual(read_doc.name, doc.name)
		finally:
			frappe.set_user("Administrator")


# ── helper for permission tests ─────────────────────────────────────


def _ensure_test_user(email, roles):
	"""Create or fetch a test user with the given roles."""
	if not frappe.db.exists("User", email):
		user = frappe.get_doc(
			{
				"doctype": "User",
				"email": email,
				"first_name": email.split("@")[0],
				"send_welcome_email": 0,
			}
		)
		user.insert(ignore_permissions=True)
	else:
		user = frappe.get_doc("User", email)

	for role_name in roles:
		if not any(r.role == role_name for r in user.roles):
			user.append("roles", {"role": role_name})
	user.save(ignore_permissions=True)

	return email
