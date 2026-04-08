"""Tests for Bed Reservation DocType.

Covers: creation, activation (specific bed + room type hold), cancellation,
expiry, consumption, override, race safety, status transitions, company
match, capacity rollup, and bed board integration.
"""

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import add_to_date, now_datetime

from alcura_ipd_ext.services.bed_reservation_service import (
	activate_reservation,
	cancel_reservation,
	compute_reservation_end,
	consume_reservation,
	expire_overdue_reservations,
	get_default_timeout,
	validate_transition,
)
from alcura_ipd_ext.services.bed_availability_service import (
	get_available_beds,
	get_bed_board_summary,
)


# ---------------------------------------------------------------------------
# Factories (reuse the same pattern as test_hospital_bed.py)
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


def _get_or_create_ward(ward_code="RW01", company=None, **overrides):
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


def _get_or_create_room(room_number="201", ward=None, **overrides):
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


def _make_reservation(
	reservation_type="Specific Bed",
	bed=None,
	room=None,
	ward=None,
	company=None,
	service_unit_type=None,
	timeout_minutes=120,
	**overrides,
):
	"""Create a Bed Reservation in Draft status."""
	company = company or _get_or_create_company()
	values = {
		"doctype": "Bed Reservation",
		"reservation_type": reservation_type,
		"company": company,
		"reservation_start": str(now_datetime()),
		"timeout_minutes": timeout_minutes,
	}
	if reservation_type == "Specific Bed":
		bed_doc = bed or _make_bed()
		values["hospital_bed"] = bed_doc.name if hasattr(bed_doc, "name") else bed_doc
	else:
		values["service_unit_type"] = service_unit_type or _get_or_create_hsut()
		if ward:
			values["hospital_ward"] = ward.name if hasattr(ward, "name") else ward

	values.update(overrides)
	doc = frappe.get_doc(values)
	doc.insert()
	return doc


def _ensure_test_user(email, roles):
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


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestBedReservation(IntegrationTestCase):
	def tearDown(self):
		frappe.db.rollback()
		frappe.set_user("Administrator")

	# ── 1. Creation ─────────────────────────────────────────────────

	def test_create_specific_bed_reservation(self):
		"""A Specific Bed reservation saves in Draft with computed end time."""
		bed = _make_bed(bed_number="CR1")
		res = _make_reservation(bed=bed, timeout_minutes=60)
		self.assertEqual(res.status, "Draft")
		self.assertEqual(res.reservation_type, "Specific Bed")
		self.assertEqual(res.hospital_bed, bed.name)
		self.assertTrue(res.reservation_end)
		self.assertEqual(res.hospital_room, bed.hospital_room)
		self.assertEqual(res.hospital_ward, bed.hospital_ward)

	# ── 2. Activate specific bed ────────────────────────────────────

	def test_activate_specific_bed_sets_bed_reserved(self):
		"""Activating a Specific Bed reservation sets the bed to Reserved."""
		bed = _make_bed(bed_number="ACT1")
		res = _make_reservation(bed=bed)
		activate_reservation(res.name)
		res.reload()
		bed.reload()

		self.assertEqual(res.status, "Active")
		self.assertEqual(bed.occupancy_status, "Reserved")
		self.assertEqual(res.reserved_by, frappe.session.user)
		self.assertTrue(res.reserved_on)

	# ── 3. Activate room type hold ──────────────────────────────────

	def test_activate_room_type_hold(self):
		"""Room Type Hold activates without changing any specific bed status."""
		ward = _get_or_create_ward(ward_code="RTH1")
		room = _get_or_create_room(room_number="RTH01", ward=ward)
		bed = _make_bed(bed_number="RTH-A", room=room)

		res = _make_reservation(
			reservation_type="Room Type Hold",
			service_unit_type=bed.service_unit_type,
			ward=ward,
			company=bed.company,
		)
		activate_reservation(res.name)
		res.reload()
		bed.reload()

		self.assertEqual(res.status, "Active")
		self.assertEqual(bed.occupancy_status, "Vacant")

	# ── 4. Cannot activate on occupied bed ──────────────────────────

	def test_cannot_activate_on_occupied_bed(self):
		"""Activation fails if the bed is Occupied."""
		bed = _make_bed(bed_number="OCC1")
		frappe.db.set_value("Hospital Bed", bed.name, "occupancy_status", "Occupied")
		res = _make_reservation(bed=bed)

		with self.assertRaises(frappe.ValidationError):
			activate_reservation(res.name)

	# ── 5. Cannot activate on already-reserved bed ──────────────────

	def test_cannot_activate_on_already_reserved_bed(self):
		"""Activation fails if the bed is already Reserved."""
		bed = _make_bed(bed_number="RSV1")
		frappe.db.set_value("Hospital Bed", bed.name, "occupancy_status", "Reserved")
		res = _make_reservation(bed=bed)

		with self.assertRaises(frappe.ValidationError):
			activate_reservation(res.name)

	# ── 6. Cannot double-reserve the same bed ───────────────────────

	def test_cannot_double_reserve_same_bed(self):
		"""Second reservation on a bed with an active one fails."""
		bed = _make_bed(bed_number="DBL1")
		res1 = _make_reservation(bed=bed)
		activate_reservation(res1.name)

		res2 = _make_reservation(bed=bed)
		with self.assertRaises(frappe.ValidationError):
			activate_reservation(res2.name)

	# ── 7. Cancel reservation resets bed ────────────────────────────

	def test_cancel_reservation_resets_bed(self):
		"""Cancelling an active reservation sets the bed back to Vacant."""
		bed = _make_bed(bed_number="CAN1")
		res = _make_reservation(bed=bed)
		activate_reservation(res.name)

		cancel_reservation(res.name, reason="Patient cancelled")
		res.reload()
		bed.reload()

		self.assertEqual(res.status, "Cancelled")
		self.assertEqual(bed.occupancy_status, "Vacant")
		self.assertTrue(res.cancelled_by)
		self.assertTrue(res.cancelled_on)
		self.assertEqual(res.cancellation_reason, "Patient cancelled")

	# ── 8. Cancel requires reason ───────────────────────────────────

	def test_cancel_requires_reason(self):
		"""Cancellation without a reason throws ValidationError."""
		bed = _make_bed(bed_number="NR1")
		res = _make_reservation(bed=bed)
		activate_reservation(res.name)

		with self.assertRaises(frappe.ValidationError):
			cancel_reservation(res.name, reason="")

	# ── 9. Expire reservation resets bed ────────────────────────────

	def test_expire_reservation_resets_bed(self):
		"""Expiry job resets the bed to Vacant."""
		bed = _make_bed(bed_number="EXP1")
		res = _make_reservation(bed=bed, timeout_minutes=1)
		activate_reservation(res.name)

		# Manually backdate reservation_end to force expiry
		past = add_to_date(now_datetime(), minutes=-10)
		frappe.db.set_value("Bed Reservation", res.name, "reservation_end", past)

		count = expire_overdue_reservations()
		self.assertGreaterEqual(count, 1)

		res.reload()
		bed.reload()
		self.assertEqual(res.status, "Expired")
		self.assertEqual(bed.occupancy_status, "Vacant")
		self.assertTrue(res.expired_on)

	# ── 10. Expire skips non-overdue ────────────────────────────────

	def test_expire_skips_non_overdue(self):
		"""Expiry job does not touch reservations that have not passed their end."""
		bed = _make_bed(bed_number="SKP1")
		res = _make_reservation(bed=bed, timeout_minutes=999)
		activate_reservation(res.name)

		count = expire_overdue_reservations()
		res.reload()
		self.assertEqual(res.status, "Active")
		self.assertEqual(count, 0)

	# ── 11. Consume reservation ─────────────────────────────────────

	def test_consume_reservation(self):
		"""Consuming links to Inpatient Record and sets status to Consumed."""
		bed = _make_bed(bed_number="CON1")
		res = _make_reservation(bed=bed)
		activate_reservation(res.name)

		# Use a fake inpatient record name (we just test the state machine)
		consume_reservation(res.name, inpatient_record="IP-TEST-001")
		res.reload()

		self.assertEqual(res.status, "Consumed")
		self.assertEqual(res.consumed_by_inpatient_record, "IP-TEST-001")
		self.assertTrue(res.consumed_on)

	# ── 12. Consume requires inpatient record ───────────────────────

	def test_consume_requires_inpatient_record(self):
		"""Consuming without an inpatient record throws ValidationError."""
		bed = _make_bed(bed_number="CNR1")
		res = _make_reservation(bed=bed)
		activate_reservation(res.name)

		with self.assertRaises(frappe.ValidationError):
			consume_reservation(res.name, inpatient_record="")

	# ── 13. Override requires admin role ─────────────────────────────

	def test_override_requires_admin_role(self):
		"""Non-admin cannot override another user's reservation."""
		bed = _make_bed(bed_number="OVR1")
		res = _make_reservation(bed=bed)
		activate_reservation(res.name)

		nurse_email = _ensure_test_user(
			"nurse_res_test@example.com", ["Nursing User"]
		)
		frappe.set_user(nurse_email)

		with self.assertRaises(frappe.PermissionError):
			cancel_reservation(
				res.name,
				reason="Override attempt",
				is_override=True,
				override_reason="Testing",
			)

	# ── 14. Override records audit trail ─────────────────────────────

	def test_override_records_audit_trail(self):
		"""Override cancellation records audit fields correctly."""
		bed = _make_bed(bed_number="OVA1")
		res = _make_reservation(bed=bed)
		activate_reservation(res.name)

		cancel_reservation(
			res.name,
			reason="Room needed for emergency",
			is_override=True,
			override_reason="Emergency admission priority",
		)
		res.reload()

		self.assertEqual(res.status, "Cancelled")
		self.assertTrue(res.is_override)
		self.assertEqual(res.override_authorized_by, frappe.session.user)
		self.assertEqual(res.override_reason, "Emergency admission priority")

	# ── 15. Invalid status transition ────────────────────────────────

	def test_invalid_status_transition(self):
		"""Draft -> Consumed is an invalid transition."""
		bed = _make_bed(bed_number="INV1")
		res = _make_reservation(bed=bed)

		with self.assertRaises(frappe.ValidationError):
			validate_transition("Draft", "Consumed")

		with self.assertRaises(frappe.ValidationError):
			validate_transition("Draft", "Expired")

		with self.assertRaises(frappe.ValidationError):
			validate_transition("Expired", "Active")

	# ── 16. Auto-computed reservation end ────────────────────────────

	def test_auto_computed_reservation_end(self):
		"""reservation_end = reservation_start + timeout_minutes."""
		bed = _make_bed(bed_number="AE1")
		res = _make_reservation(bed=bed, timeout_minutes=90)

		expected_end = compute_reservation_end(res.reservation_start, 90)
		self.assertEqual(str(res.reservation_end), expected_end)

	# ── 17. Company mismatch blocked ────────────────────────────────

	def test_company_mismatch_blocked(self):
		"""Reservation with mismatched company is rejected on validate."""
		bed = _make_bed(bed_number="CM1")

		other_company = "Other Hospital Pvt Ltd"
		if not frappe.db.exists("Company", other_company):
			frappe.get_doc(
				{
					"doctype": "Company",
					"company_name": other_company,
					"abbr": "OTH",
					"default_currency": "INR",
					"country": "India",
				}
			).insert(ignore_if_duplicate=True)

		with self.assertRaises(frappe.ValidationError):
			_make_reservation(bed=bed, company=other_company)

	# ── 18. Capacity rollup after expiry ─────────────────────────────

	def test_capacity_rollup_after_expiry(self):
		"""Ward/room capacity counts are correct after expiring a reservation."""
		ward = _get_or_create_ward(ward_code="CAP1")
		room = _get_or_create_room(room_number="CAP01", ward=ward)
		bed = _make_bed(bed_number="CAP-A", room=room)

		res = _make_reservation(bed=bed, timeout_minutes=1)
		activate_reservation(res.name)

		ward.reload()
		room.reload()
		# Bed is Reserved, so it counts as non-available
		self.assertEqual(room.available_beds, 0)

		past = add_to_date(now_datetime(), minutes=-10)
		frappe.db.set_value("Bed Reservation", res.name, "reservation_end", past)
		expire_overdue_reservations()

		ward.reload()
		room.reload()
		self.assertEqual(room.available_beds, 1)
		self.assertEqual(ward.available_beds, 1)

	# ── 19. Bed board shows reserved count ───────────────────────────

	def test_bed_board_shows_reserved_count(self):
		"""Summary API returns a reserved count."""
		ward = _get_or_create_ward(ward_code="BB1")
		room = _get_or_create_room(room_number="BB01", ward=ward)
		bed = _make_bed(bed_number="BB-A", room=room)

		res = _make_reservation(bed=bed)
		activate_reservation(res.name)

		summary = get_bed_board_summary({"ward": ward.name})
		self.assertIn("reserved", summary)
		self.assertEqual(summary["reserved"], 1)

	# ── 20. Reserved bed excluded from available ─────────────────────

	def test_reserved_bed_excluded_from_available(self):
		"""Reserved beds do not appear in the available beds list."""
		ward = _get_or_create_ward(ward_code="EX1")
		room = _get_or_create_room(room_number="EX01", ward=ward)
		bed = _make_bed(bed_number="EX-A", room=room)

		available_before = get_available_beds({"ward": ward.name})
		bed_names_before = [b["bed"] for b in available_before]
		self.assertIn(bed.name, bed_names_before)

		res = _make_reservation(bed=bed)
		activate_reservation(res.name)

		available_after = get_available_beds({"ward": ward.name})
		bed_names_after = [b["bed"] for b in available_after]
		self.assertNotIn(bed.name, bed_names_after)
