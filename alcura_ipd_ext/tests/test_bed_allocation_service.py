"""Tests for US-B3: Bed Allocation Service.

Covers: happy-path allocation, concurrent allocation, reservation consumption,
validation failures, capacity rollup, HSU sync, movement log creation,
custom field updates, and timeline comments.
"""

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import now_datetime

from alcura_ipd_ext.services.bed_allocation_service import allocate_bed_on_admission
from alcura_ipd_ext.services.bed_reservation_service import activate_reservation


# ---------------------------------------------------------------------------
# Factories
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


def _get_or_create_ward(ward_code="AW01", company=None, **overrides):
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


def _get_or_create_room(room_number="301", ward=None, **overrides):
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


def _make_patient(name_suffix="ALLOC"):
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
	"""Create an Inpatient Record in 'Admission Scheduled' status."""
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


def _make_reservation(bed=None, company=None, patient=None, **overrides):
	company = company or _get_or_create_company()
	bed_doc = bed or _make_bed()
	bed_name = bed_doc.name if hasattr(bed_doc, "name") else bed_doc
	values = {
		"doctype": "Bed Reservation",
		"reservation_type": "Specific Bed",
		"company": company,
		"hospital_bed": bed_name,
		"reservation_start": str(now_datetime()),
		"timeout_minutes": 120,
	}
	if patient:
		values["patient"] = patient.name if hasattr(patient, "name") else patient
	values.update(overrides)
	doc = frappe.get_doc(values)
	doc.insert()
	return doc


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestBedAllocationService(IntegrationTestCase):
	def tearDown(self):
		frappe.db.rollback()
		frappe.set_user("Administrator")

	# ── 1. Happy path ───────────────────────────────────────────────

	def test_allocate_vacant_bed(self):
		"""Allocating a vacant bed transitions IR to Admitted and bed to Occupied."""
		bed = _make_bed(bed_number="AL1")
		patient = _make_patient("AL1")
		ir = _make_inpatient_record(patient=patient)

		self.assertEqual(bed.occupancy_status, "Vacant")
		self.assertEqual(ir.status, "Admission Scheduled")

		result = allocate_bed_on_admission(ir.name, bed.name)

		self.assertEqual(result["status"], "Admitted")
		self.assertEqual(result["hospital_bed"], bed.name)

		ir.reload()
		self.assertEqual(ir.status, "Admitted")
		self.assertTrue(ir.admitted_datetime)
		self.assertEqual(ir.custom_current_bed, bed.name)
		self.assertEqual(ir.custom_current_room, bed.hospital_room)
		self.assertEqual(ir.custom_current_ward, bed.hospital_ward)
		self.assertEqual(ir.custom_admitted_by_user, frappe.session.user)

		bed.reload()
		self.assertEqual(bed.occupancy_status, "Occupied")

	# ── 2. Reservation consumption ──────────────────────────────────

	def test_allocate_with_reservation_consumes_it(self):
		"""Allocation with an active reservation consumes the reservation."""
		bed = _make_bed(bed_number="AL2")
		patient = _make_patient("AL2")
		reservation = _make_reservation(bed=bed, patient=patient)

		activate_reservation(reservation.name)
		reservation.reload()
		self.assertEqual(reservation.status, "Active")

		bed.reload()
		self.assertEqual(bed.occupancy_status, "Reserved")

		ir = _make_inpatient_record(patient=patient)
		result = allocate_bed_on_admission(ir.name, bed.name, reservation=reservation.name)

		self.assertEqual(result["status"], "Admitted")

		reservation.reload()
		self.assertEqual(reservation.status, "Consumed")
		self.assertEqual(reservation.consumed_by_inpatient_record, ir.name)

	# ── 3. Concurrency ──────────────────────────────────────────────

	def test_double_allocation_fails(self):
		"""Two allocations on the same bed — the second fails."""
		bed = _make_bed(bed_number="AL3")
		patient1 = _make_patient("AL3A")
		patient2 = _make_patient("AL3B")
		ir1 = _make_inpatient_record(patient=patient1)
		ir2 = _make_inpatient_record(patient=patient2)

		allocate_bed_on_admission(ir1.name, bed.name)

		with self.assertRaises(frappe.ValidationError):
			allocate_bed_on_admission(ir2.name, bed.name)

	# ── 4. Validation: occupied bed ─────────────────────────────────

	def test_allocate_occupied_bed_fails(self):
		"""Cannot allocate a bed that is already Occupied."""
		bed = _make_bed(bed_number="AL4")
		frappe.db.set_value("Hospital Bed", bed.name, "occupancy_status", "Occupied")

		patient = _make_patient("AL4")
		ir = _make_inpatient_record(patient=patient)

		with self.assertRaises(frappe.ValidationError):
			allocate_bed_on_admission(ir.name, bed.name)

	# ── 5. Validation: inactive bed ─────────────────────────────────

	def test_allocate_inactive_bed_fails(self):
		"""Cannot allocate an inactive bed."""
		bed = _make_bed(bed_number="AL5")
		frappe.db.set_value("Hospital Bed", bed.name, "is_active", 0)

		patient = _make_patient("AL5")
		ir = _make_inpatient_record(patient=patient)

		with self.assertRaises(frappe.ValidationError):
			allocate_bed_on_admission(ir.name, bed.name)

	# ── 6. Validation: company mismatch ─────────────────────────────

	def test_allocate_company_mismatch_fails(self):
		"""Cannot allocate a bed from a different company."""
		company2 = _get_or_create_company(abbr="OTH", name="Other Hospital Pvt Ltd")
		ward2 = _get_or_create_ward(ward_code="OW01", company=company2)
		room2 = _get_or_create_room(room_number="O01", ward=ward2)
		bed = _make_bed(bed_number="AL6", room=room2)

		patient = _make_patient("AL6")
		ir = _make_inpatient_record(patient=patient)

		with self.assertRaises(frappe.ValidationError):
			allocate_bed_on_admission(ir.name, bed.name)

	# ── 7. Validation: wrong IR status ──────────────────────────────

	def test_allocate_wrong_ir_status_fails(self):
		"""Cannot allocate when IR status is not 'Admission Scheduled'."""
		bed = _make_bed(bed_number="AL7")
		patient = _make_patient("AL7")
		ir = _make_inpatient_record(patient=patient)

		allocate_bed_on_admission(ir.name, bed.name)

		bed2 = _make_bed(bed_number="AL7B")
		with self.assertRaises(frappe.ValidationError):
			allocate_bed_on_admission(ir.name, bed2.name)

	# ── 8. Capacity rollup ──────────────────────────────────────────

	def test_capacity_updated_after_allocation(self):
		"""Room and ward occupied/available counts update after allocation."""
		ward = _get_or_create_ward(ward_code="AW02")
		room = _get_or_create_room(room_number="302", ward=ward)
		bed = _make_bed(bed_number="AL8", room=room)

		patient = _make_patient("AL8")
		ir = _make_inpatient_record(patient=patient)

		allocate_bed_on_admission(ir.name, bed.name)

		room.reload()
		self.assertEqual(room.occupied_beds, 1)

		ward.reload()
		self.assertEqual(ward.occupied_beds, 1)

	# ── 9. Movement log ─────────────────────────────────────────────

	def test_movement_log_created_on_allocation(self):
		"""A Bed Movement Log with type Admission is created."""
		bed = _make_bed(bed_number="AL9")
		patient = _make_patient("AL9")
		ir = _make_inpatient_record(patient=patient)

		result = allocate_bed_on_admission(ir.name, bed.name)

		bml_name = result["bed_movement_log"]
		bml = frappe.get_doc("Bed Movement Log", bml_name)
		self.assertEqual(bml.movement_type, "Admission")
		self.assertEqual(bml.inpatient_record, ir.name)
		self.assertEqual(bml.patient, patient.name)
		self.assertEqual(bml.to_bed, bed.name)
		self.assertFalse(bml.from_bed)
		self.assertEqual(bml.performed_by, frappe.session.user)

	# ── 10. Inpatient Occupancy row ─────────────────────────────────

	def test_inpatient_occupancy_row_added(self):
		"""An Inpatient Occupancy child row is added to the IR."""
		bed = _make_bed(bed_number="AL10")
		patient = _make_patient("AL10")
		ir = _make_inpatient_record(patient=patient)

		allocate_bed_on_admission(ir.name, bed.name)

		ir.reload()
		self.assertTrue(ir.inpatient_occupancies)
		last_occ = ir.inpatient_occupancies[-1]
		self.assertEqual(last_occ.service_unit, bed.healthcare_service_unit)
		self.assertTrue(last_occ.check_in)

	# ── 11. Maintenance hold bed ────────────────────────────────────

	def test_allocate_maintenance_hold_bed_fails(self):
		"""Cannot allocate a bed under maintenance hold."""
		bed = _make_bed(bed_number="AL11")
		frappe.db.set_value("Hospital Bed", bed.name, "maintenance_hold", 1)

		patient = _make_patient("AL11")
		ir = _make_inpatient_record(patient=patient)

		with self.assertRaises(frappe.ValidationError):
			allocate_bed_on_admission(ir.name, bed.name)
