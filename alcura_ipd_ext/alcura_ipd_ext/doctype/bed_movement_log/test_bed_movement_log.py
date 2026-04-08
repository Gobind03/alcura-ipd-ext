"""Tests for Bed Movement Log DocType.

Covers: creation, validation (type-field coupling), reason enforcement,
immutability, and permissions.
"""

import frappe
from frappe.tests import IntegrationTestCase


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


def _get_or_create_hsut(name="Test IPD Bed Type", inpatient_occupancy=1):
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


def _get_or_create_ward(ward_code="MW01", company=None):
	company = company or _get_or_create_company()
	abbr = frappe.get_cached_value("Company", company, "abbr")
	ward_key = f"{abbr}-{ward_code.upper()}"
	if frappe.db.exists("Hospital Ward", ward_key):
		return frappe.get_doc("Hospital Ward", ward_key)
	doc = frappe.get_doc({
		"doctype": "Hospital Ward",
		"ward_code": ward_code,
		"ward_name": f"Test Ward {ward_code}",
		"company": company,
		"ward_classification": "General",
	})
	doc.insert()
	return doc


def _get_or_create_room(room_number="501", ward=None):
	ward_doc = ward or _get_or_create_ward()
	ward_name = ward_doc.name if hasattr(ward_doc, "name") else ward_doc
	room_key = f"{ward_name}-{room_number.upper()}"
	if frappe.db.exists("Hospital Room", room_key):
		return frappe.get_doc("Hospital Room", room_key)
	doc = frappe.get_doc({
		"doctype": "Hospital Room",
		"room_number": room_number,
		"room_name": f"Room {room_number}",
		"hospital_ward": ward_name,
		"service_unit_type": _get_or_create_hsut(),
	})
	doc.insert()
	return doc


def _make_bed(bed_number="A", room=None):
	room_doc = room or _get_or_create_room()
	room_name = room_doc.name if hasattr(room_doc, "name") else room_doc
	doc = frappe.get_doc({
		"doctype": "Hospital Bed",
		"bed_number": bed_number,
		"hospital_room": room_name,
	})
	doc.insert()
	return doc


def _make_patient(name_suffix="BML"):
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


def _make_inpatient_record(patient=None, company=None):
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
	})
	doc.insert(ignore_permissions=True)
	return doc


def _make_movement_log(movement_type="Admission", **overrides):
	company = _get_or_create_company()
	patient = overrides.pop("patient", None) or _make_patient()
	ir = overrides.pop("inpatient_record", None) or _make_inpatient_record(patient=patient)

	values = {
		"doctype": "Bed Movement Log",
		"movement_type": movement_type,
		"movement_datetime": frappe.utils.now_datetime(),
		"inpatient_record": ir.name if hasattr(ir, "name") else ir,
		"patient": patient.name if hasattr(patient, "name") else patient,
		"company": company,
	}
	values.update(overrides)
	doc = frappe.get_doc(values)
	doc.flags.ignore_permissions = True
	doc.insert()
	return doc


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestBedMovementLog(IntegrationTestCase):
	def tearDown(self):
		frappe.db.rollback()
		frappe.set_user("Administrator")

	# ── 1. Admission creation ───────────────────────────────────────

	def test_create_admission_movement(self):
		"""An Admission movement log can be created with a destination bed."""
		bed = _make_bed(bed_number="BM1")
		bml = _make_movement_log(
			movement_type="Admission",
			to_bed=bed.name,
		)
		self.assertEqual(bml.movement_type, "Admission")
		self.assertEqual(bml.to_bed, bed.name)
		self.assertTrue(bml.performed_by)
		self.assertTrue(bml.performed_on)

	# ── 2. Admission requires destination ───────────────────────────

	def test_admission_without_to_bed_fails(self):
		"""Admission movement without destination bed raises ValidationError."""
		with self.assertRaises(frappe.ValidationError):
			_make_movement_log(movement_type="Admission")

	# ── 3. Transfer requires both beds ──────────────────────────────

	def test_transfer_without_from_bed_fails(self):
		"""Transfer movement without source bed raises ValidationError."""
		bed_b = _make_bed(bed_number="BM2")
		with self.assertRaises(frappe.ValidationError):
			_make_movement_log(movement_type="Transfer", to_bed=bed_b.name, reason="Test")

	def test_transfer_without_to_bed_fails(self):
		"""Transfer movement without destination bed raises ValidationError."""
		bed_a = _make_bed(bed_number="BM3")
		with self.assertRaises(frappe.ValidationError):
			_make_movement_log(movement_type="Transfer", from_bed=bed_a.name, reason="Test")

	# ── 4. Transfer requires reason ─────────────────────────────────

	def test_transfer_without_reason_fails(self):
		"""Transfer movement without reason raises ValidationError."""
		bed_a = _make_bed(bed_number="BM4A")
		bed_b = _make_bed(bed_number="BM4B")
		with self.assertRaises(frappe.ValidationError):
			_make_movement_log(
				movement_type="Transfer",
				from_bed=bed_a.name,
				to_bed=bed_b.name,
			)

	# ── 5. Transfer with all fields ─────────────────────────────────

	def test_create_transfer_movement(self):
		"""A Transfer movement log with all fields saves correctly."""
		bed_a = _make_bed(bed_number="BM5A")
		bed_b = _make_bed(bed_number="BM5B")
		bml = _make_movement_log(
			movement_type="Transfer",
			from_bed=bed_a.name,
			to_bed=bed_b.name,
			reason="Patient upgrade",
		)
		self.assertEqual(bml.movement_type, "Transfer")
		self.assertEqual(bml.from_bed, bed_a.name)
		self.assertEqual(bml.to_bed, bed_b.name)
		self.assertEqual(bml.reason, "Patient upgrade")

	# ── 6. Discharge requires source ────────────────────────────────

	def test_discharge_without_from_bed_fails(self):
		"""Discharge movement without source bed raises ValidationError."""
		with self.assertRaises(frappe.ValidationError):
			_make_movement_log(movement_type="Discharge")

	def test_create_discharge_movement(self):
		"""A Discharge movement log with source bed saves correctly."""
		bed = _make_bed(bed_number="BM6")
		bml = _make_movement_log(
			movement_type="Discharge",
			from_bed=bed.name,
		)
		self.assertEqual(bml.movement_type, "Discharge")
		self.assertEqual(bml.from_bed, bed.name)

	# ── 7. Immutability ─────────────────────────────────────────────

	def test_update_after_creation_fails(self):
		"""Updating a Bed Movement Log after creation raises ValidationError."""
		bed = _make_bed(bed_number="BM7")
		bml = _make_movement_log(
			movement_type="Admission",
			to_bed=bed.name,
		)

		bml.reason = "Modified reason"
		with self.assertRaises(frappe.ValidationError):
			bml.save()

	# ── 8. Auto-sets audit fields ───────────────────────────────────

	def test_auto_sets_performed_by_and_on(self):
		"""performed_by and performed_on are auto-set on insert."""
		bed = _make_bed(bed_number="BM8")
		bml = _make_movement_log(
			movement_type="Admission",
			to_bed=bed.name,
		)
		self.assertEqual(bml.performed_by, frappe.session.user)
		self.assertTrue(bml.performed_on)
