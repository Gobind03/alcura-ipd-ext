"""IPD Clinical Order controller.

Handles validation, status lifecycle, location auto-population,
and SLA milestone management for all inpatient clinical orders
(Medication, Lab Test, Radiology, Procedure).
"""

from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import now_datetime


# Allowed forward transitions (from -> set of valid targets)
_VALID_TRANSITIONS: dict[str, set[str]] = {
	"Draft": {"Ordered", "Cancelled"},
	"Ordered": {"Acknowledged", "In Progress", "Cancelled", "On Hold"},
	"Acknowledged": {"In Progress", "Completed", "Cancelled", "On Hold"},
	"In Progress": {"Completed", "Cancelled", "On Hold"},
	"On Hold": {"Ordered", "Acknowledged", "In Progress", "Cancelled"},
}

_TERMINAL_STATUSES = frozenset({"Completed", "Cancelled"})


class IPDClinicalOrder(Document):
	def before_insert(self):
		self._populate_location()

	def validate(self):
		self._validate_ir_status()
		self._validate_order_type_fields()
		self._validate_prn()
		self._validate_stat_urgency()
		self._validate_cancellation()
		self._validate_hold()

	def after_insert(self):
		self._update_ir_order_counts()

	def on_update(self):
		if self.has_value_changed("status"):
			self._update_ir_order_counts()

	def on_trash(self):
		self._update_ir_order_counts()

	# ── Public helpers ───────────────────────────────────────────

	def transition_to(self, new_status: str, user: str | None = None) -> None:
		"""Enforce and execute a status transition with audit fields."""
		current = self.status
		if current == new_status:
			return
		if current in _TERMINAL_STATUSES:
			frappe.throw(
				_("Cannot change status of a {0} order.").format(current),
				exc=frappe.ValidationError,
			)
		valid = _VALID_TRANSITIONS.get(current, set())
		if new_status not in valid:
			frappe.throw(
				_("Invalid status transition from {0} to {1}.").format(current, new_status),
				exc=frappe.ValidationError,
			)

		now = now_datetime()
		acting_user = user or frappe.session.user
		self.status = new_status

		ts_map = {
			"Ordered": ("ordered_at", "ordered_by"),
			"Acknowledged": ("acknowledged_at", "acknowledged_by"),
			"Completed": ("completed_at", "completed_by"),
			"Cancelled": ("cancelled_at", "cancelled_by"),
		}
		if new_status in ts_map:
			ts_field, user_field = ts_map[new_status]
			if not self.get(ts_field):
				self.set(ts_field, now)
			self.set(user_field, acting_user)

	# ── Private validation ───────────────────────────────────────

	def _populate_location(self):
		if not self.inpatient_record:
			return
		ir = frappe.db.get_value(
			"Inpatient Record",
			self.inpatient_record,
			["custom_current_ward", "custom_current_room", "custom_current_bed"],
			as_dict=True,
		)
		if ir:
			self.ward = ir.custom_current_ward
			self.room = ir.custom_current_room
			self.bed = ir.custom_current_bed

	def _validate_ir_status(self):
		if not self.inpatient_record:
			return
		ir_status = frappe.db.get_value("Inpatient Record", self.inpatient_record, "status")
		if ir_status not in ("Admitted", "Admission Scheduled"):
			frappe.throw(
				_("Clinical orders can only be placed for Admitted or Admission Scheduled patients."),
				exc=frappe.ValidationError,
			)

	def _validate_order_type_fields(self):
		if self.order_type == "Medication" and not self.medication_name:
			frappe.throw(_("Medication Name is required for Medication orders."))
		if self.order_type == "Lab Test" and not self.lab_test_name:
			frappe.throw(_("Lab Test Name is required for Lab Test orders."))
		if self.order_type in ("Radiology", "Procedure") and not self.procedure_name:
			frappe.throw(_("Procedure / Investigation Name is required for {0} orders.").format(self.order_type))

	def _validate_prn(self):
		if self.is_prn and not self.prn_reason:
			frappe.throw(_("PRN reason is required when the order is marked as PRN."))

	def _validate_stat_urgency(self):
		if self.is_stat and self.urgency not in ("STAT", "Emergency"):
			self.urgency = "STAT"

	def _validate_cancellation(self):
		if self.status == "Cancelled" and not self.cancellation_reason:
			frappe.throw(_("Cancellation reason is required."))

	def _validate_hold(self):
		if self.status == "On Hold" and not self.hold_reason:
			frappe.throw(_("Hold reason is required when placing an order on hold."))

	def _update_ir_order_counts(self):
		if not self.inpatient_record:
			return
		from alcura_ipd_ext.services.clinical_order_service import update_ir_order_counts

		update_ir_order_counts(self.inpatient_record)
