"""Tests for IPD Bed Policy (Single DocType).

Covers: validation, cached get_policy(), defaults, and role-based permissions.
"""

import frappe
from frappe.tests import IntegrationTestCase

from alcura_ipd_ext.alcura_ipd_ext.doctype.ipd_bed_policy.ipd_bed_policy import (
	get_policy,
)


def _save_policy(**overrides):
	"""Load the Single doc, apply overrides, and save."""
	doc = frappe.get_doc("IPD Bed Policy")
	for key, val in overrides.items():
		doc.set(key, val)
	doc.save()
	return doc


def _ensure_test_user(email, roles):
	"""Create a user with the given roles if it does not exist."""
	if not frappe.db.exists("User", email):
		user = frappe.get_doc(
			{
				"doctype": "User",
				"email": email,
				"first_name": email.split("@")[0].replace("_", " ").title(),
				"send_welcome_email": 0,
			}
		)
		user.insert(ignore_permissions=True)

	user = frappe.get_doc("User", email)
	user.roles = []
	for role in roles:
		user.append("roles", {"role": role})
	user.save(ignore_permissions=True)
	return email


class TestIPDBedPolicy(IntegrationTestCase):
	def tearDown(self):
		frappe.db.rollback()
		frappe.clear_cache()

	# ── 1. Defaults ──────────────────────────────────────────────────

	def test_get_policy_returns_defaults(self):
		"""get_policy() returns sensible defaults even if never saved."""
		policy = get_policy()
		self.assertTrue(policy["exclude_dirty_beds"])
		self.assertTrue(policy["exclude_cleaning_beds"])
		self.assertTrue(policy["exclude_maintenance_beds"])
		self.assertTrue(policy["exclude_infection_blocked"])
		self.assertEqual(policy["gender_enforcement"], "Strict")
		self.assertEqual(policy["cleaning_turnaround_sla_minutes"], 60)
		self.assertTrue(policy["auto_mark_dirty_on_discharge"])
		self.assertEqual(policy["reservation_timeout_minutes"], 120)
		self.assertEqual(policy["enforce_payer_eligibility"], "Advisory")
		self.assertEqual(policy["min_buffer_beds_per_ward"], 0)

	# ── 2. Saved values propagate ────────────────────────────────────

	def test_saved_values_returned(self):
		"""Saved overrides are reflected in get_policy()."""
		_save_policy(
			exclude_dirty_beds=0,
			gender_enforcement="Ignore",
			cleaning_turnaround_sla_minutes=30,
			enforce_payer_eligibility="Strict",
		)
		frappe.clear_cache()

		policy = get_policy()
		self.assertFalse(policy["exclude_dirty_beds"])
		self.assertEqual(policy["gender_enforcement"], "Ignore")
		self.assertEqual(policy["cleaning_turnaround_sla_minutes"], 30)
		self.assertEqual(policy["enforce_payer_eligibility"], "Strict")

	# ── 3. Validation: non-negative integers ─────────────────────────

	def test_negative_sla_rejected(self):
		"""Negative cleaning SLA raises ValidationError."""
		with self.assertRaises(frappe.ValidationError):
			_save_policy(cleaning_turnaround_sla_minutes=-10)

	def test_negative_reservation_timeout_rejected(self):
		"""Negative reservation timeout raises ValidationError."""
		with self.assertRaises(frappe.ValidationError):
			_save_policy(reservation_timeout_minutes=-5)

	def test_negative_buffer_rejected(self):
		"""Negative buffer beds raises ValidationError."""
		with self.assertRaises(frappe.ValidationError):
			_save_policy(min_buffer_beds_per_ward=-1)

	def test_zero_values_accepted(self):
		"""Zero values are valid for integer fields."""
		doc = _save_policy(
			cleaning_turnaround_sla_minutes=0,
			reservation_timeout_minutes=0,
			min_buffer_beds_per_ward=0,
		)
		self.assertEqual(doc.cleaning_turnaround_sla_minutes, 0)
		self.assertEqual(doc.reservation_timeout_minutes, 0)
		self.assertEqual(doc.min_buffer_beds_per_ward, 0)

	# ── 4. Permissions ───────────────────────────────────────────────

	def test_healthcare_admin_can_write(self):
		"""Healthcare Administrator can save the policy."""
		email = _ensure_test_user(
			"bedpolicy_admin@test.com", ["Healthcare Administrator"]
		)
		frappe.set_user(email)
		try:
			doc = frappe.get_doc("IPD Bed Policy")
			doc.cleaning_turnaround_sla_minutes = 45
			doc.save()
			self.assertEqual(doc.cleaning_turnaround_sla_minutes, 45)
		finally:
			frappe.set_user("Administrator")

	def test_nursing_user_cannot_write(self):
		"""Nursing User can read but not write the policy."""
		email = _ensure_test_user("bedpolicy_nurse@test.com", ["Nursing User"])
		frappe.set_user(email)
		try:
			doc = frappe.get_doc("IPD Bed Policy")
			doc.cleaning_turnaround_sla_minutes = 90
			with self.assertRaises(frappe.PermissionError):
				doc.save()
		finally:
			frappe.set_user("Administrator")

	def test_nursing_user_can_read(self):
		"""Nursing User can read the policy."""
		email = _ensure_test_user("bedpolicy_nurse2@test.com", ["Nursing User"])
		frappe.set_user(email)
		try:
			doc = frappe.get_doc("IPD Bed Policy")
			self.assertIsNotNone(doc.gender_enforcement)
		finally:
			frappe.set_user("Administrator")
