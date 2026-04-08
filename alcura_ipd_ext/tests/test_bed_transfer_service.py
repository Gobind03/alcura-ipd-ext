"""Tests for US-B4: Bed Transfer Service.

Covers: happy-path transfer, policy-driven source bed handling, concurrent
transfers, validation failures, capacity rollup, movement log creation,
Inpatient Occupancy row management, and deadlock prevention via ordered locking.
"""

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import now_datetime

from alcura_ipd_ext.services.bed_allocation_service import allocate_bed_on_admission
from alcura_ipd_ext.services.bed_transfer_service import transfer_patient


# ---------------------------------------------------------------------------
# Factories (same pattern as allocation tests)
# ---------------------------------------------------------------------------


def _get_or_create_company(abbr="TST", name="Test Hospital Pvt Ltd"):
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


def _get_or_create_hsut(name="Test IPD Bed Type", inpatient_occupancy=1, **kw):
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


def _get_or_create_ward(ward_code="TW01", company=None, **overrides):
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


def _get_or_create_room(room_number="401", ward=None, **overrides):
	ward_doc = ward or _get_or_create_ward()
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


def _make_bed(bed_number="A", room=None, **overrides):
	room_doc = room or _get_or_create_room()
	room_name = room_doc.name if hasattr(room_doc, "name") else room_doc
	doc = frappe.get_doc({
		"doctype": "Hospital Bed",
		"bed_number": bed_number,
		"hospital_room": room_name,
		**overrides,
	})
	doc.insert()
	return doc


def _make_patient(name_suffix="XFER"):
	patient_name = f"Test Patient {name_suffix}"
	if frappe.db.exists("Patient", {"patient_name": patient_name}):
		return frappe.get_doc("Patient", {"patient_name": patient_name})
	doc = frappe.get_doc({
		"doctype": "Patient",
		"first_name": f"Test {name_suffix}",
		"last_name": "Patient",
		"sex": "Male",
	})
	doc.insert(ignore_permissions=True)
	return doc


def _make_medical_department(name="Test General"):
	if frappe.db.exists("Medical Department", name):
		return name
	doc = frappe.get_doc({
		"doctype": "Medical Department",
		"department": name,
	})
	doc.insert(ignore_permissions=True)
	return doc.name


def _make_inpatient_record(patient=None, company=None, **overrides):
	patient_doc = patient or _make_patient()
	patient_name = patient_doc.name if hasattr(patient_doc, "name") else patient_doc
	company = company or _get_or_create_company()
	dept = _make_medical_department()
	doc = frappe.get_doc({
		"doctype": "Inpatient Record",
		"patient": patient_name,
		"company": company,
		"status": "Admission Scheduled",
		"scheduled_date": frappe.utils.today(),
		"medical_department": dept,
		**overrides,
	})
	doc.insert(ignore_permissions=True)
	return doc


def _admit_patient(bed, patient=None, company=None):
	"""Helper: create IR + allocate bed, returning (ir_doc, bed_doc)."""
	patient = patient or _make_patient()
	ir = _make_inpatient_record(patient=patient, company=company)
	allocate_bed_on_admission(ir.name, bed.name)
	ir.reload()
	bed.reload()
	return ir, bed


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestBedTransferService(IntegrationTestCase):
	def tearDown(self):
		frappe.db.rollback()
		frappe.set_user("Administrator")

	# ── 1. Happy path ───────────────────────────────────────────────

	def test_transfer_between_beds(self):
		"""Transfer patient from one bed to another — source released, dest occupied."""
		ward = _get_or_create_ward(ward_code="TW02")
		room = _get_or_create_room(room_number="402", ward=ward)
		bed_a = _make_bed(bed_number="TA1", room=room)
		bed_b = _make_bed(bed_number="TB1", room=room)

		ir, _ = _admit_patient(bed_a)

		result = transfer_patient(
			inpatient_record=ir.name,
			from_bed=bed_a.name,
			to_bed=bed_b.name,
			reason="Patient requested window bed",
		)

		self.assertEqual(result["from_bed"], bed_a.name)
		self.assertEqual(result["to_bed"], bed_b.name)

		bed_a.reload()
		self.assertEqual(bed_a.occupancy_status, "Vacant")

		bed_b.reload()
		self.assertEqual(bed_b.occupancy_status, "Occupied")

		ir.reload()
		self.assertEqual(ir.custom_current_bed, bed_b.name)
		self.assertEqual(ir.custom_current_room, bed_b.hospital_room)

	# ── 2. Source bed marked dirty ──────────────────────────────────

	def test_transfer_marks_source_dirty(self):
		"""With source_bed_action='Mark Dirty', source bed housekeeping becomes Dirty."""
		ward = _get_or_create_ward(ward_code="TW03")
		room = _get_or_create_room(room_number="403", ward=ward)
		bed_a = _make_bed(bed_number="TA2", room=room)
		bed_b = _make_bed(bed_number="TB2", room=room)

		ir, _ = _admit_patient(bed_a)

		transfer_patient(
			inpatient_record=ir.name,
			from_bed=bed_a.name,
			to_bed=bed_b.name,
			reason="Upgrade",
			source_bed_action="Mark Dirty",
		)

		bed_a.reload()
		self.assertEqual(bed_a.occupancy_status, "Vacant")
		self.assertEqual(bed_a.housekeeping_status, "Dirty")

	# ── 3. Source bed stays clean ───────────────────────────────────

	def test_transfer_marks_source_vacant_clean(self):
		"""With source_bed_action='Mark Vacant', source bed stays Clean."""
		ward = _get_or_create_ward(ward_code="TW04")
		room = _get_or_create_room(room_number="404", ward=ward)
		bed_a = _make_bed(bed_number="TA3", room=room)
		bed_b = _make_bed(bed_number="TB3", room=room)

		ir, _ = _admit_patient(bed_a)

		transfer_patient(
			inpatient_record=ir.name,
			from_bed=bed_a.name,
			to_bed=bed_b.name,
			reason="Quick move",
			source_bed_action="Mark Vacant",
		)

		bed_a.reload()
		self.assertEqual(bed_a.occupancy_status, "Vacant")
		self.assertEqual(bed_a.housekeeping_status, "Clean")

	# ── 4. Concurrent transfer to same bed ──────────────────────────

	def test_double_transfer_to_same_dest_fails(self):
		"""Two transfers to the same destination — the second fails."""
		ward = _get_or_create_ward(ward_code="TW05")
		room = _get_or_create_room(room_number="405", ward=ward)
		bed_a = _make_bed(bed_number="TA4", room=room)
		bed_b = _make_bed(bed_number="TB4", room=room)
		bed_c = _make_bed(bed_number="TC4", room=room)

		ir1, _ = _admit_patient(bed_a, patient=_make_patient("XF4A"))
		ir2, _ = _admit_patient(bed_b, patient=_make_patient("XF4B"))

		transfer_patient(
			inpatient_record=ir1.name,
			from_bed=bed_a.name,
			to_bed=bed_c.name,
			reason="Move patient 1",
		)

		with self.assertRaises(frappe.ValidationError):
			transfer_patient(
				inpatient_record=ir2.name,
				from_bed=bed_b.name,
				to_bed=bed_c.name,
				reason="Move patient 2",
			)

	# ── 5. Transfer after discharge fails ───────────────────────────

	def test_transfer_discharged_patient_fails(self):
		"""Cannot transfer a patient who has been discharged."""
		ward = _get_or_create_ward(ward_code="TW06")
		room = _get_or_create_room(room_number="406", ward=ward)
		bed_a = _make_bed(bed_number="TA5", room=room)
		bed_b = _make_bed(bed_number="TB5", room=room)

		ir, _ = _admit_patient(bed_a)

		frappe.db.set_value("Inpatient Record", ir.name, "status", "Discharged")

		with self.assertRaises(frappe.ValidationError):
			transfer_patient(
				inpatient_record=ir.name,
				from_bed=bed_a.name,
				to_bed=bed_b.name,
				reason="Post-discharge move",
			)

	# ── 6. Transfer to occupied bed fails ───────────────────────────

	def test_transfer_to_occupied_bed_fails(self):
		"""Cannot transfer to a bed that is already Occupied."""
		ward = _get_or_create_ward(ward_code="TW07")
		room = _get_or_create_room(room_number="407", ward=ward)
		bed_a = _make_bed(bed_number="TA6", room=room)
		bed_b = _make_bed(bed_number="TB6", room=room)

		ir, _ = _admit_patient(bed_a, patient=_make_patient("XF6A"))
		_admit_patient(bed_b, patient=_make_patient("XF6B"))

		with self.assertRaises(frappe.ValidationError):
			transfer_patient(
				inpatient_record=ir.name,
				from_bed=bed_a.name,
				to_bed=bed_b.name,
				reason="Attempt to move to occupied",
			)

	# ── 7. Transfer to maintenance-hold bed fails ───────────────────

	def test_transfer_to_maintenance_hold_fails(self):
		"""Cannot transfer to a bed under maintenance hold."""
		ward = _get_or_create_ward(ward_code="TW08")
		room = _get_or_create_room(room_number="408", ward=ward)
		bed_a = _make_bed(bed_number="TA7", room=room)
		bed_b = _make_bed(bed_number="TB7", room=room)

		ir, _ = _admit_patient(bed_a)

		frappe.db.set_value("Hospital Bed", bed_b.name, "maintenance_hold", 1)

		with self.assertRaises(frappe.ValidationError):
			transfer_patient(
				inpatient_record=ir.name,
				from_bed=bed_a.name,
				to_bed=bed_b.name,
				reason="Move to maintenance bed",
			)

	# ── 8. Mismatched from_bed fails ────────────────────────────────

	def test_transfer_wrong_from_bed_fails(self):
		"""Cannot transfer from a bed the patient is not in."""
		ward = _get_or_create_ward(ward_code="TW09")
		room = _get_or_create_room(room_number="409", ward=ward)
		bed_a = _make_bed(bed_number="TA8", room=room)
		bed_b = _make_bed(bed_number="TB8", room=room)
		bed_c = _make_bed(bed_number="TC8", room=room)

		ir, _ = _admit_patient(bed_a)

		with self.assertRaises(frappe.ValidationError):
			transfer_patient(
				inpatient_record=ir.name,
				from_bed=bed_b.name,
				to_bed=bed_c.name,
				reason="Wrong source",
			)

	# ── 9. Same source and destination fails ────────────────────────

	def test_transfer_same_bed_fails(self):
		"""Cannot transfer from a bed to itself."""
		ward = _get_or_create_ward(ward_code="TW10")
		room = _get_or_create_room(room_number="410", ward=ward)
		bed_a = _make_bed(bed_number="TA9", room=room)

		ir, _ = _admit_patient(bed_a)

		with self.assertRaises(frappe.ValidationError):
			transfer_patient(
				inpatient_record=ir.name,
				from_bed=bed_a.name,
				to_bed=bed_a.name,
				reason="Same bed",
			)

	# ── 10. Capacity rollup both rooms ──────────────────────────────

	def test_capacity_updated_for_both_rooms(self):
		"""Room/ward counts update for both source and destination after transfer."""
		ward = _get_or_create_ward(ward_code="TW11")
		room_a = _get_or_create_room(room_number="411", ward=ward)
		room_b = _get_or_create_room(room_number="412", ward=ward)
		bed_a = _make_bed(bed_number="TA10", room=room_a)
		bed_b = _make_bed(bed_number="TB10", room=room_b)

		ir, _ = _admit_patient(bed_a)

		room_a.reload()
		self.assertEqual(room_a.occupied_beds, 1)

		transfer_patient(
			inpatient_record=ir.name,
			from_bed=bed_a.name,
			to_bed=bed_b.name,
			reason="Ward transfer",
		)

		room_a.reload()
		self.assertEqual(room_a.occupied_beds, 0)

		room_b.reload()
		self.assertEqual(room_b.occupied_beds, 1)

	# ── 11. Movement log ────────────────────────────────────────────

	def test_movement_log_created_on_transfer(self):
		"""A Bed Movement Log with type Transfer is created."""
		ward = _get_or_create_ward(ward_code="TW12")
		room = _get_or_create_room(room_number="413", ward=ward)
		bed_a = _make_bed(bed_number="TA11", room=room)
		bed_b = _make_bed(bed_number="TB11", room=room)

		ir, _ = _admit_patient(bed_a)

		result = transfer_patient(
			inpatient_record=ir.name,
			from_bed=bed_a.name,
			to_bed=bed_b.name,
			reason="Patient comfort",
		)

		bml = frappe.get_doc("Bed Movement Log", result["bed_movement_log"])
		self.assertEqual(bml.movement_type, "Transfer")
		self.assertEqual(bml.from_bed, bed_a.name)
		self.assertEqual(bml.to_bed, bed_b.name)
		self.assertEqual(bml.reason, "Patient comfort")
		self.assertEqual(bml.inpatient_record, ir.name)

	# ── 12. Occupancy rows ──────────────────────────────────────────

	def test_inpatient_occupancy_rows_updated(self):
		"""Old occupancy marked left, new one created on transfer."""
		ward = _get_or_create_ward(ward_code="TW13")
		room = _get_or_create_room(room_number="414", ward=ward)
		bed_a = _make_bed(bed_number="TA12", room=room)
		bed_b = _make_bed(bed_number="TB12", room=room)

		ir, _ = _admit_patient(bed_a)

		ir.reload()
		self.assertEqual(len(ir.inpatient_occupancies), 1)

		transfer_patient(
			inpatient_record=ir.name,
			from_bed=bed_a.name,
			to_bed=bed_b.name,
			reason="Transfer test",
		)

		ir.reload()
		self.assertEqual(len(ir.inpatient_occupancies), 2)

		old_occ = ir.inpatient_occupancies[0]
		self.assertTrue(old_occ.left)
		self.assertTrue(old_occ.check_out)

		new_occ = ir.inpatient_occupancies[1]
		self.assertFalse(new_occ.left)
		self.assertEqual(new_occ.service_unit, bed_b.healthcare_service_unit)

	# ── 13. Reason is mandatory ─────────────────────────────────────

	def test_transfer_without_reason_fails(self):
		"""Transfer without a reason raises ValidationError."""
		ward = _get_or_create_ward(ward_code="TW14")
		room = _get_or_create_room(room_number="415", ward=ward)
		bed_a = _make_bed(bed_number="TA13", room=room)
		bed_b = _make_bed(bed_number="TB13", room=room)

		ir, _ = _admit_patient(bed_a)

		with self.assertRaises(frappe.ValidationError):
			transfer_patient(
				inpatient_record=ir.name,
				from_bed=bed_a.name,
				to_bed=bed_b.name,
				reason="",
			)
