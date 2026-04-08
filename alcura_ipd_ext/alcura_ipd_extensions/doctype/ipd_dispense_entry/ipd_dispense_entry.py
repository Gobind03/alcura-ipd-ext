"""IPD Dispense Entry — tracks each medication dispense event."""

from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import now_datetime


class IPDDispenseEntry(Document):
	def before_insert(self):
		self._populate_from_order()
		if not self.dispensed_at:
			self.dispensed_at = now_datetime()
		if not self.dispensed_by:
			self.dispensed_by = frappe.session.user

	def validate(self):
		self._validate_dispense_qty()
		self._validate_substitution()
		self._validate_order_status()

	def after_insert(self):
		self._update_order_dispense_status()

	def on_update(self):
		if self.has_value_changed("status"):
			self._update_order_dispense_status()

	def on_trash(self):
		self._update_order_dispense_status()

	def _populate_from_order(self):
		if not self.clinical_order:
			return
		order = frappe.db.get_value(
			"IPD Clinical Order",
			self.clinical_order,
			[
				"patient", "inpatient_record", "medication_item",
				"medication_name", "dose", "dose_uom", "ward", "room", "bed",
			],
			as_dict=True,
		)
		if not order:
			return
		for field in ("patient", "inpatient_record", "medication_name", "dose", "dose_uom", "ward", "bed"):
			if not self.get(field) and order.get(field):
				self.set(field, order.get(field))
		if not self.medication_item and order.medication_item:
			self.medication_item = order.medication_item

	def _validate_dispense_qty(self):
		if self.dispensed_qty is None or self.dispensed_qty <= 0:
			frappe.throw(_("Dispensed quantity must be greater than zero."))

	def _validate_substitution(self):
		if self.is_substitution:
			if not self.substitution_reason:
				frappe.throw(_("Substitution reason is required."))
			if not self.substitution_approved_by:
				frappe.throw(_("Substitution must be approved by a practitioner."))

	def _validate_order_status(self):
		if not self.clinical_order:
			return
		order_status = frappe.db.get_value("IPD Clinical Order", self.clinical_order, "status")
		if order_status in ("Cancelled", "Draft"):
			frappe.throw(
				_("Cannot dispense against a {0} order.").format(order_status),
				exc=frappe.ValidationError,
			)

	def _update_order_dispense_status(self):
		if not self.clinical_order:
			return
		from alcura_ipd_ext.services.pharmacy_dispense_service import update_order_dispense_status

		update_order_dispense_status(self.clinical_order)
