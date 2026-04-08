"""Tests for US-D2: Admission Checklist Service.

Covers: template selection, checklist creation, item completion,
mandatory blocking, waiver flow, role-based override, status
recomputation, duplicate prevention, and IR link sync.
"""

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import today

from alcura_ipd_ext.services.admission_checklist_service import (
	complete_item,
	create_checklist_for_admission,
	waive_item,
)


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


def _make_medical_department(name="Test General"):
	if frappe.db.exists("Medical Department", name):
		return name
	doc = frappe.get_doc({
		"doctype": "Medical Department",
		"department": name,
	})
	doc.insert(ignore_permissions=True)
	return doc.name


def _make_patient(suffix="CL"):
	patient_name = f"Test Patient {suffix}"
	existing = frappe.db.exists("Patient", {"patient_name": patient_name})
	if existing:
		return frappe.get_doc("Patient", existing)
	doc = frappe.get_doc({
		"doctype": "Patient",
		"first_name": f"Test {suffix}",
		"last_name": "Patient",
		"sex": "Male",
	})
	doc.insert(ignore_permissions=True)
	return doc


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
		"scheduled_date": today(),
		"medical_department": dept,
	})
	doc.insert(ignore_permissions=True)
	return doc


def _make_template(name="Default Checklist", items=None, **overrides):
	if frappe.db.exists("Admission Checklist Template", name):
		frappe.delete_doc("Admission Checklist Template", name, force=True)

	default_items = items or [
		{"item_label": "General Consent", "category": "Consent", "is_mandatory": 1, "can_override": 1},
		{"item_label": "ID Proof Verified", "category": "Identity", "is_mandatory": 1, "can_override": 0},
		{"item_label": "Deposit Collected", "category": "Financial", "is_mandatory": 1, "can_override": 1},
		{"item_label": "Allergy Assessment", "category": "Clinical", "is_mandatory": 0, "can_override": 0},
	]

	doc = frappe.get_doc({
		"doctype": "Admission Checklist Template",
		"template_name": name,
		"is_active": 1,
		"is_default": overrides.get("is_default", 1),
		"payer_type": overrides.get("payer_type", ""),
		"care_setting": overrides.get("care_setting", "All"),
		"checklist_items": default_items,
	})
	doc.insert(ignore_permissions=True)
	return doc


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestAdmissionChecklistService(IntegrationTestCase):
	def tearDown(self):
		frappe.db.rollback()
		frappe.set_user("Administrator")

	# ── 1. Checklist creation ──────────────────────────────────────

	def test_create_checklist_from_template(self):
		"""Creating a checklist from template populates entries correctly."""
		template = _make_template()
		ir = _make_inpatient_record(patient=_make_patient("CL1"))

		result = create_checklist_for_admission(ir.name)

		self.assertTrue(result["checklist"])
		self.assertEqual(result["status"], "Incomplete")

		checklist = frappe.get_doc("Admission Checklist", result["checklist"])
		self.assertEqual(checklist.inpatient_record, ir.name)
		self.assertEqual(checklist.template_used, template.name)
		self.assertEqual(len(checklist.checklist_entries), 4)

		# All entries start as Pending
		for entry in checklist.checklist_entries:
			self.assertEqual(entry.status, "Pending")

	# ── 2. Duplicate prevention ────────────────────────────────────

	def test_duplicate_checklist_fails(self):
		"""Cannot create two checklists for the same Inpatient Record."""
		_make_template()
		ir = _make_inpatient_record(patient=_make_patient("CL2"))

		create_checklist_for_admission(ir.name)

		with self.assertRaises(frappe.ValidationError):
			create_checklist_for_admission(ir.name)

	# ── 3. Complete item ───────────────────────────────────────────

	def test_complete_item(self):
		"""Completing a pending item sets user and timestamp."""
		_make_template()
		ir = _make_inpatient_record(patient=_make_patient("CL3"))
		result = create_checklist_for_admission(ir.name)

		complete_item(result["checklist"], 1)

		checklist = frappe.get_doc("Admission Checklist", result["checklist"])
		entry = checklist.checklist_entries[0]
		self.assertEqual(entry.status, "Completed")
		self.assertEqual(entry.completed_by, frappe.session.user)
		self.assertTrue(entry.completed_on)

	# ── 4. All mandatory complete → status Complete ────────────────

	def test_status_becomes_complete(self):
		"""When all mandatory items are completed, status = Complete."""
		_make_template()
		ir = _make_inpatient_record(patient=_make_patient("CL4"))
		result = create_checklist_for_admission(ir.name)

		# Complete mandatory items (rows 1, 2, 3)
		for idx in [1, 2, 3]:
			complete_item(result["checklist"], idx)

		checklist = frappe.get_doc("Admission Checklist", result["checklist"])
		self.assertEqual(checklist.status, "Complete")
		self.assertTrue(checklist.completed_by)
		self.assertTrue(checklist.completed_on)

	# ── 5. Status remains Incomplete when mandatory pending ────────

	def test_status_incomplete_with_mandatory_pending(self):
		"""Status stays Incomplete when mandatory items are pending."""
		_make_template()
		ir = _make_inpatient_record(patient=_make_patient("CL5"))
		result = create_checklist_for_admission(ir.name)

		# Complete only first item
		complete_item(result["checklist"], 1)

		checklist = frappe.get_doc("Admission Checklist", result["checklist"])
		self.assertEqual(checklist.status, "Incomplete")

	# ── 6. Waive item → Overridden ────────────────────────────────

	def test_waive_item_changes_status_to_overridden(self):
		"""Waiving a mandatory item results in Overridden status."""
		_make_template()
		ir = _make_inpatient_record(patient=_make_patient("CL6"))
		result = create_checklist_for_admission(ir.name)

		# Complete items 2, 3 (mandatory) and waive item 1 (has can_override=1)
		complete_item(result["checklist"], 2)
		complete_item(result["checklist"], 3)
		waive_item(result["checklist"], 1, "Patient unable to sign, verbal consent obtained")

		checklist = frappe.get_doc("Admission Checklist", result["checklist"])
		self.assertEqual(checklist.status, "Overridden")

		entry = checklist.checklist_entries[0]
		self.assertEqual(entry.status, "Waived")
		self.assertEqual(entry.override_by, frappe.session.user)
		self.assertIn("verbal consent", entry.override_reason)

	# ── 7. Cannot waive non-overridable item ──────────────────────

	def test_cannot_waive_non_overridable(self):
		"""Waiving an item not marked as can_override fails."""
		_make_template()
		ir = _make_inpatient_record(patient=_make_patient("CL7"))
		result = create_checklist_for_admission(ir.name)

		# Item 2 (ID Proof Verified) has can_override=0
		with self.assertRaises(frappe.ValidationError):
			waive_item(result["checklist"], 2, "Some reason")

	# ── 8. Waive requires reason ──────────────────────────────────

	def test_waive_requires_reason(self):
		"""Waiving without a reason fails validation."""
		_make_template()
		ir = _make_inpatient_record(patient=_make_patient("CL8"))
		result = create_checklist_for_admission(ir.name)

		with self.assertRaises(frappe.ValidationError):
			waive_item(result["checklist"], 1, "")

	# ── 9. Cannot complete already completed ──────────────────────

	def test_double_complete_fails(self):
		"""Cannot complete an already completed item."""
		_make_template()
		ir = _make_inpatient_record(patient=_make_patient("CL9"))
		result = create_checklist_for_admission(ir.name)

		complete_item(result["checklist"], 1)

		with self.assertRaises(frappe.ValidationError):
			complete_item(result["checklist"], 1)

	# ── 10. IR link sync ──────────────────────────────────────────

	def test_ir_checklist_link_set(self):
		"""Creating a checklist sets the custom_admission_checklist on IR."""
		_make_template()
		ir = _make_inpatient_record(patient=_make_patient("CL10"))

		result = create_checklist_for_admission(ir.name)

		ir.reload()
		self.assertEqual(ir.custom_admission_checklist, result["checklist"])

	# ── 11. No template fails ─────────────────────────────────────

	def test_no_template_fails(self):
		"""Checklist creation fails when no template exists."""
		# Delete all templates
		for t in frappe.get_all("Admission Checklist Template"):
			frappe.delete_doc("Admission Checklist Template", t.name, force=True)

		ir = _make_inpatient_record(patient=_make_patient("CL11"))

		with self.assertRaises(frappe.ValidationError):
			create_checklist_for_admission(ir.name)

	# ── 12. Template validation: unique labels ────────────────────

	def test_template_duplicate_labels_fail(self):
		"""Template with duplicate item labels fails validation."""
		with self.assertRaises(frappe.ValidationError):
			_make_template(
				name="Bad Template",
				items=[
					{"item_label": "Consent", "category": "Consent", "is_mandatory": 1},
					{"item_label": "Consent", "category": "Consent", "is_mandatory": 1},
				],
			)
