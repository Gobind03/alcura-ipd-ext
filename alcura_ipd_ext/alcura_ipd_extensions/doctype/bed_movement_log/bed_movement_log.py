"""Server controller for Bed Movement Log.

Bed Movement Log is an immutable audit record of every bed change in the
IPD journey (Admission, Transfer, Discharge).  Records are created by the
allocation and transfer services and should not be modified after creation.
"""

from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document


class BedMovementLog(Document):
	def before_insert(self):
		self.performed_by = frappe.session.user
		self.performed_on = frappe.utils.now_datetime()

	def validate(self):
		self._validate_movement_type_fields()
		self._validate_reason_for_transfer()

	def on_update(self):
		if not self.flags.get("allow_update"):
			if self.get_doc_before_save():
				frappe.throw(
					_("Bed Movement Log records are immutable. Create a new movement instead."),
					exc=frappe.ValidationError,
				)

	def _validate_movement_type_fields(self):
		if self.movement_type == "Admission":
			if not self.to_bed:
				frappe.throw(
					_("Destination bed is required for Admission movements."),
					exc=frappe.ValidationError,
				)
		elif self.movement_type == "Transfer":
			if not self.from_bed:
				frappe.throw(
					_("Source bed is required for Transfer movements."),
					exc=frappe.ValidationError,
				)
			if not self.to_bed:
				frappe.throw(
					_("Destination bed is required for Transfer movements."),
					exc=frappe.ValidationError,
				)
		elif self.movement_type == "Discharge":
			if not self.from_bed:
				frappe.throw(
					_("Source bed is required for Discharge movements."),
					exc=frappe.ValidationError,
				)

	def _validate_reason_for_transfer(self):
		if self.movement_type == "Transfer" and not self.reason:
			frappe.throw(
				_("Reason is mandatory for Transfer movements."),
				exc=frappe.ValidationError,
			)
