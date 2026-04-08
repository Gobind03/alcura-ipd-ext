"""DocType-level tests for Nursing Discharge Checklist.

Tests item completion, status derivation, and signoff/verify logic.
"""

from __future__ import annotations

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import now_datetime, today


class TestNursingDischargeChecklist(IntegrationTestCase):
	def setUp(self):
		if not frappe.db.exists("Company", "_Test NDC2 Company"):
			frappe.get_doc({
				"doctype": "Company",
				"company_name": "_Test NDC2 Company",
				"abbr": "TND2",
				"default_currency": "INR",
				"country": "India",
			}).insert(ignore_permissions=True)

		if not frappe.db.exists("Patient", {"first_name": "_Test NDC2 Patient"}):
			frappe.get_doc({
				"doctype": "Patient",
				"first_name": "_Test NDC2 Patient",
				"sex": "Female",
			}).insert(ignore_permissions=True)

		self.patient = frappe.db.get_value(
			"Patient", {"first_name": "_Test NDC2 Patient"}, "name"
		)
		self.company = "_Test NDC2 Company"

	def _make_ir(self):
		doc = frappe.get_doc({
			"doctype": "Inpatient Record",
			"patient": self.patient,
			"company": self.company,
			"status": "Admitted",
			"scheduled_date": today(),
		})
		doc.insert(ignore_permissions=True)
		doc.db_set("status", "Admitted")
		return doc.name

	def _make_checklist(self, ir_name):
		from alcura_ipd_ext.services.nursing_discharge_service import (
			create_nursing_checklist,
		)
		name = create_nursing_checklist(inpatient_record=ir_name)
		return frappe.get_doc("Nursing Discharge Checklist", name)

	def test_checklist_has_15_standard_items(self):
		ir = self._make_ir()
		doc = self._make_checklist(ir)
		self.assertEqual(len(doc.items), 15)

	def test_status_moves_to_in_progress_on_first_completion(self):
		ir = self._make_ir()
		doc = self._make_checklist(ir)
		doc.complete_item(item_idx=1)
		doc.reload()
		self.assertEqual(doc.status, "In Progress")

	def test_signoff_fails_with_pending_mandatory_items(self):
		ir = self._make_ir()
		doc = self._make_checklist(ir)
		self.assertRaises(Exception, doc.sign_off)

	def test_verify_fails_before_signoff(self):
		ir = self._make_ir()
		doc = self._make_checklist(ir)
		self.assertRaises(frappe.ValidationError, doc.verify)
