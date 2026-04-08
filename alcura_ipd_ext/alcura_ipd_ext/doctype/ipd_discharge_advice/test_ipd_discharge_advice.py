"""DocType-level tests for IPD Discharge Advice.

Tests validation rules, status immutability, and transition guards.
"""

from __future__ import annotations

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import add_days, now_datetime, today


class TestIPDDischargeAdvice(IntegrationTestCase):
	def setUp(self):
		if not frappe.db.exists("Company", "_Test DDA Company"):
			frappe.get_doc({
				"doctype": "Company",
				"company_name": "_Test DDA Company",
				"abbr": "TDDA",
				"default_currency": "INR",
				"country": "India",
			}).insert(ignore_permissions=True)

		if not frappe.db.exists("Patient", {"first_name": "_Test DDA Patient"}):
			frappe.get_doc({
				"doctype": "Patient",
				"first_name": "_Test DDA Patient",
				"sex": "Male",
			}).insert(ignore_permissions=True)

		if not frappe.db.exists(
			"Healthcare Practitioner",
			{"practitioner_name": "_Test DDA Dr"},
		):
			frappe.get_doc({
				"doctype": "Healthcare Practitioner",
				"first_name": "_Test DDA Dr",
			}).insert(ignore_permissions=True)

		self.patient = frappe.db.get_value(
			"Patient", {"first_name": "_Test DDA Patient"}, "name"
		)
		self.practitioner = frappe.db.get_value(
			"Healthcare Practitioner",
			{"practitioner_name": "_Test DDA Dr"},
			"name",
		)
		self.company = "_Test DDA Company"

	def _make_ir(self, status="Admitted"):
		doc = frappe.get_doc({
			"doctype": "Inpatient Record",
			"patient": self.patient,
			"company": self.company,
			"status": status,
			"scheduled_date": today(),
		})
		doc.insert(ignore_permissions=True)
		if status == "Admitted":
			doc.db_set("status", "Admitted")
			doc.db_set("admitted_datetime", now_datetime())
		return doc.name

	def _make_advice(self, ir_name):
		doc = frappe.get_doc({
			"doctype": "IPD Discharge Advice",
			"inpatient_record": ir_name,
			"patient": self.patient,
			"company": self.company,
			"consultant": self.practitioner,
			"expected_discharge_datetime": add_days(now_datetime(), 1),
			"discharge_type": "Normal",
		})
		doc.insert(ignore_permissions=True)
		return doc

	def test_submit_advice_transitions_to_advised(self):
		ir = self._make_ir()
		doc = self._make_advice(ir)
		assert doc.status == "Draft"

		doc.submit_advice()
		doc.reload()
		assert doc.status == "Advised"
		assert doc.advised_by is not None

	def test_cannot_transition_from_completed(self):
		ir = self._make_ir()
		doc = self._make_advice(ir)
		doc.submit_advice()
		doc.acknowledge()
		doc.complete()

		self.assertRaises(frappe.ValidationError, doc.submit_advice)
		self.assertRaises(frappe.ValidationError, doc.acknowledge)

	def test_cancellation_requires_reason(self):
		ir = self._make_ir()
		doc = self._make_advice(ir)
		doc.submit_advice()

		self.assertRaises(Exception, doc.cancel_advice, reason="")

	def test_cannot_create_for_non_admitted(self):
		ir = self._make_ir(status="Admission Scheduled")
		self.assertRaises(
			frappe.ValidationError,
			self._make_advice,
			ir,
		)
