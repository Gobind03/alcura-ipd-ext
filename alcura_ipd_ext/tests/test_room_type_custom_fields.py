"""Tests for US-A2: Room types via custom fields on Healthcare Service Unit Type.

Covers: custom field existence, critical-care auto-flag, isolation flag,
nursing intensity suggestion, category-required validation, tariff fields,
and non-interference with standard HSUT behaviour.
"""

import frappe
import frappe.defaults
import pytest
from frappe.tests import IntegrationTestCase

from alcura_ipd_ext.overrides.healthcare_service_unit_type import CRITICAL_CARE_CATEGORIES
from alcura_ipd_ext.setup.custom_fields import get_custom_fields


def _ensure_custom_fields():
	"""Idempotently install custom fields so they exist during test runs."""
	from alcura_ipd_ext.setup.custom_fields import setup_custom_fields

	setup_custom_fields()


def _make_hsut(name, inpatient_occupancy=1, **overrides):
	"""Factory to create a Healthcare Service Unit Type for testing."""
	if frappe.db.exists("Healthcare Service Unit Type", name):
		doc = frappe.get_doc("Healthcare Service Unit Type", name)
		for k, v in overrides.items():
			doc.set(k, v)
		doc.inpatient_occupancy = inpatient_occupancy
		doc.save()
		return doc

	doc = frappe.get_doc(
		{
			"doctype": "Healthcare Service Unit Type",
			"healthcare_service_unit_type": name,
			"inpatient_occupancy": inpatient_occupancy,
			**overrides,
		}
	)
	doc.insert(ignore_if_duplicate=True)
	return doc


class TestRoomTypeCustomFields(IntegrationTestCase):
	"""Integration tests for IPD room-type custom fields on Healthcare Service Unit Type."""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		_ensure_custom_fields()

	def tearDown(self):
		frappe.db.rollback()

	# ── 1. Custom fields exist ───────────────────────────────────────

	def test_custom_fields_installed(self):
		"""All expected custom fields exist on Healthcare Service Unit Type."""
		field_defs = get_custom_fields()["Healthcare Service Unit Type"]
		for field_def in field_defs:
			cf_name = f"Healthcare Service Unit Type-{field_def['fieldname']}"
			self.assertTrue(
				frappe.db.exists("Custom Field", cf_name),
				f"Custom field {cf_name} not found",
			)

	# ── 2-3. Critical care auto-flag ─────────────────────────────────

	def test_icu_sets_critical_care_flag(self):
		"""ipd_room_category=ICU sets is_critical_care_unit=1."""
		doc = _make_hsut("Test ICU Room A2", ipd_room_category="ICU")
		self.assertEqual(doc.is_critical_care_unit, 1)

	def test_general_clears_critical_care_flag(self):
		"""ipd_room_category=General keeps is_critical_care_unit=0."""
		doc = _make_hsut("Test General Room A2", ipd_room_category="General")
		self.assertEqual(doc.is_critical_care_unit, 0)

	# ── 4. Isolation auto-flag ───────────────────────────────────────

	def test_isolation_sets_supports_isolation(self):
		"""ipd_room_category=Isolation auto-sets supports_isolation=1."""
		doc = _make_hsut("Test Isolation Room A2", ipd_room_category="Isolation")
		self.assertEqual(doc.supports_isolation, 1)

	# ── 5. Nursing intensity suggestion ──────────────────────────────

	def test_critical_care_suggests_nursing_intensity(self):
		"""Critical care category auto-sets nursing_intensity=Critical when blank."""
		doc = _make_hsut(
			"Test MICU Room A2",
			ipd_room_category="MICU",
			nursing_intensity="",
		)
		self.assertEqual(doc.nursing_intensity, "Critical")

	# ── 6. Non-inpatient type skips validation ───────────────────────

	def test_non_inpatient_type_no_category_required(self):
		"""Non-inpatient types do not require ipd_room_category."""
		doc = _make_hsut(
			"Test Consulting Room A2",
			inpatient_occupancy=0,
			allow_appointments=1,
			ipd_room_category="",
		)
		self.assertTrue(doc.name)

	# ── 7. Inpatient without category raises error ───────────────────

	def test_inpatient_requires_room_category(self):
		"""Inpatient type without ipd_room_category raises ValidationError."""
		with self.assertRaises(frappe.ValidationError):
			_make_hsut(
				"Test Missing Category A2",
				inpatient_occupancy=1,
				ipd_room_category="",
			)

	# ── 8. Default price list linkage ────────────────────────────────

	def test_default_price_list_can_be_set(self):
		"""default_price_list accepts a valid Price List."""
		pl_name = "Standard Selling"
		if not frappe.db.exists("Price List", pl_name):
			frappe.get_doc(
				{"doctype": "Price List", "price_list_name": pl_name, "selling": 1, "currency": "INR"}
			).insert(ignore_if_duplicate=True)

		doc = _make_hsut(
			"Test Tariff Room A2",
			ipd_room_category="Private",
			default_price_list=pl_name,
		)
		self.assertEqual(doc.default_price_list, pl_name)

	# ── 9. Package eligible toggle ───────────────────────────────────

	def test_package_eligible_toggle(self):
		"""package_eligible can be independently set to 1."""
		doc = _make_hsut(
			"Test Package Room A2",
			ipd_room_category="Suite",
			package_eligible=1,
		)
		self.assertEqual(doc.package_eligible, 1)

	# ── 10. All critical care categories detected ────────────────────

	def test_all_critical_care_categories(self):
		"""Every category in CRITICAL_CARE_CATEGORIES sets the flag to 1."""
		for idx, cat in enumerate(sorted(CRITICAL_CARE_CATEGORIES)):
			name = f"Test CC {cat} A2-{idx}"
			doc = _make_hsut(name, ipd_room_category=cat)
			self.assertEqual(
				doc.is_critical_care_unit, 1,
				f"{cat} should set is_critical_care_unit=1",
			)

	# ── 11. Non-critical categories stay 0 ───────────────────────────

	def test_non_critical_categories(self):
		"""Non-critical categories keep is_critical_care_unit=0."""
		non_critical = ["General", "Twin Sharing", "Semi-Private", "Private", "Deluxe", "Suite", "Other"]
		for idx, cat in enumerate(non_critical):
			name = f"Test NonCC {cat} A2-{idx}"
			doc = _make_hsut(name, ipd_room_category=cat)
			self.assertEqual(
				doc.is_critical_care_unit, 0,
				f"{cat} should keep is_critical_care_unit=0",
			)

	# ── 12. Standard billing item still created ──────────────────────

	def test_standard_item_creation_unaffected(self):
		"""Standard HSUT billing-item creation works with custom fields present."""
		doc = _make_hsut(
			"Test Billable Room A2",
			ipd_room_category="Private",
			is_billable=1,
		)
		self.assertTrue(doc.name)
		if doc.get("item"):
			self.assertTrue(frappe.db.exists("Item", doc.item))

	# ── 13. Occupancy class persists ─────────────────────────────────

	def test_occupancy_class_persists(self):
		"""occupancy_class value is stored correctly."""
		doc = _make_hsut(
			"Test Twin A2",
			ipd_room_category="Twin Sharing",
			occupancy_class="Double",
		)
		self.assertEqual(doc.occupancy_class, "Double")

	# ── 14. Nursing intensity override respected ─────────────────────

	def test_nursing_intensity_manual_override(self):
		"""Explicit nursing_intensity is not overwritten by auto-suggest."""
		doc = _make_hsut(
			"Test HDU Override A2",
			ipd_room_category="HDU",
			nursing_intensity="High",
		)
		self.assertEqual(doc.nursing_intensity, "High")

	# ── 15. Isolation flag not reset for non-isolation types ─────────

	def test_isolation_flag_not_cleared_for_others(self):
		"""supports_isolation can be manually set for non-Isolation categories."""
		doc = _make_hsut(
			"Test Manual Iso A2",
			ipd_room_category="Private",
			supports_isolation=1,
		)
		self.assertEqual(doc.supports_isolation, 1)
