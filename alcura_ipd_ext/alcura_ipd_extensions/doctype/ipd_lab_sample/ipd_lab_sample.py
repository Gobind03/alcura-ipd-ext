"""IPD Lab Sample — tracks sample lifecycle from collection to lab receipt."""

from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import now_datetime


_VALID_TRANSITIONS: dict[str, set[str]] = {
	"Pending": {"Collected", "Rejected"},
	"Collected": {"In Transit", "Received", "Rejected"},
	"In Transit": {"Received", "Rejected"},
	"Received": {"Processing", "Rejected"},
	"Processing": {"Completed", "Rejected"},
}

_TERMINAL_STATUSES = frozenset({"Completed", "Rejected"})


class IPDLabSample(Document):
	def before_insert(self):
		self._populate_from_order()
		if not self.barcode:
			self.barcode = _generate_barcode(self.name or "")

	def validate(self):
		self._validate_order_type()
		self._validate_recollection()
		self._validate_critical_ack()

	def after_insert(self):
		if not self.barcode or self.barcode.startswith("TEMP-"):
			self.barcode = f"SAMP-{self.name}"
			self.db_set("barcode", self.barcode, update_modified=False)

	def transition_to(self, new_status: str) -> None:
		"""Enforce status transition rules."""
		current = self.status
		if current == new_status:
			return
		if current in _TERMINAL_STATUSES:
			frappe.throw(
				_("Cannot change status of a {0} sample.").format(current),
				exc=frappe.ValidationError,
			)
		valid = _VALID_TRANSITIONS.get(current, set())
		if new_status not in valid:
			frappe.throw(
				_("Invalid sample transition from {0} to {1}.").format(current, new_status),
				exc=frappe.ValidationError,
			)
		self.status = new_status

	def _populate_from_order(self):
		if not self.clinical_order:
			return
		order = frappe.db.get_value(
			"IPD Clinical Order",
			self.clinical_order,
			[
				"patient", "inpatient_record", "lab_test_name",
				"sample_type", "is_fasting_required", "ward", "bed",
			],
			as_dict=True,
		)
		if not order:
			return
		for field in ("patient", "inpatient_record", "lab_test_name", "sample_type", "ward", "bed"):
			if not self.get(field) and order.get(field):
				self.set(field, order.get(field))
		if order.is_fasting_required and not self.is_fasting_sample:
			self.is_fasting_sample = 1

	def _validate_order_type(self):
		if not self.clinical_order:
			return
		order_type = frappe.db.get_value("IPD Clinical Order", self.clinical_order, "order_type")
		if order_type != "Lab Test":
			frappe.throw(
				_("Lab samples can only be created for Lab Test orders."),
				exc=frappe.ValidationError,
			)

	def _validate_recollection(self):
		if self.collection_status == "Recollection Needed" and not self.recollection_reason:
			frappe.throw(_("Recollection reason is required."))

	def _validate_critical_ack(self):
		if self.is_critical_result and self.critical_result_acknowledged_by:
			if not self.critical_result_acknowledged_at:
				self.critical_result_acknowledged_at = now_datetime()


def _generate_barcode(name: str) -> str:
	return f"TEMP-{frappe.generate_hash(length=8).upper()}"
