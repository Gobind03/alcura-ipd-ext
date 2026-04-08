"""Server controller for IPD Discharge Advice.

Manages the discharge advice lifecycle: Draft -> Advised -> Acknowledged
-> Completed, with cancellation support and audit trail.
"""

from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import now_datetime


VALID_TRANSITIONS: dict[str, list[str]] = {
	"Draft": ["Advised", "Cancelled"],
	"Advised": ["Acknowledged", "Cancelled"],
	"Acknowledged": ["Completed"],
	"Completed": [],
	"Cancelled": [],
}


class IPDDischargeAdvice(Document):
	def validate(self):
		self._validate_inpatient_record()
		self._validate_no_duplicate_active()
		self._validate_cancellation_reason()

	@frappe.whitelist()
	def submit_advice(self):
		"""Transition from Draft to Advised."""
		self._transition_to("Advised")
		self.advised_by = frappe.session.user
		self.advised_on = now_datetime()
		self.save()

		self._link_to_inpatient_record()
		self._notify_departments()
		self._add_ir_comment(_("Discharge advice raised by {0}").format(
			frappe.bold(frappe.session.user)
		))

	@frappe.whitelist()
	def acknowledge(self):
		"""Nursing/desk acknowledgment of the discharge advice."""
		self._transition_to("Acknowledged")
		self.acknowledged_by = frappe.session.user
		self.acknowledged_on = now_datetime()
		self.save()

		self._add_ir_comment(_("Discharge advice acknowledged by {0}").format(
			frappe.bold(frappe.session.user)
		))

	@frappe.whitelist()
	def complete(self):
		"""Mark discharge as completed."""
		self._transition_to("Completed")
		self.actual_discharge_datetime = now_datetime()
		self.save()

		self._add_ir_comment(_("Discharge completed"))

	@frappe.whitelist()
	def cancel_advice(self, reason: str = ""):
		"""Cancel the discharge advice with mandatory reason."""
		if not reason:
			frappe.throw(
				_("Cancellation reason is required."),
				title=_("Missing Reason"),
			)
		self._transition_to("Cancelled")
		self.cancelled_by = frappe.session.user
		self.cancelled_on = now_datetime()
		self.cancellation_reason = reason
		self.save()

		self._clear_ir_link()
		self._add_ir_comment(
			_("Discharge advice cancelled by {0}. Reason: {1}").format(
				frappe.bold(frappe.session.user), reason
			)
		)

	# ── Private helpers ──────────────────────────────────────────────

	def _transition_to(self, new_status: str):
		allowed = VALID_TRANSITIONS.get(self.status, [])
		if new_status not in allowed:
			frappe.throw(
				_("Cannot transition from {0} to {1}.").format(
					frappe.bold(self.status), frappe.bold(new_status)
				),
				exc=frappe.ValidationError,
			)
		self.status = new_status

	def _validate_inpatient_record(self):
		if not self.inpatient_record:
			return
		ir_status = frappe.db.get_value(
			"Inpatient Record", self.inpatient_record, "status"
		)
		if ir_status not in ("Admitted", "Discharge Scheduled"):
			frappe.throw(
				_("Inpatient Record {0} has status {1}. "
				  "Discharge advice can only be raised for Admitted patients.").format(
					frappe.bold(self.inpatient_record),
					frappe.bold(ir_status),
				),
				exc=frappe.ValidationError,
			)

	def _validate_no_duplicate_active(self):
		if not self.inpatient_record or self.status == "Cancelled":
			return
		existing = frappe.db.get_value(
			"IPD Discharge Advice",
			{
				"inpatient_record": self.inpatient_record,
				"status": ("not in", ("Cancelled", "Completed")),
				"name": ("!=", self.name or ""),
			},
			"name",
		)
		if existing:
			frappe.throw(
				_("An active discharge advice {0} already exists for this admission.").format(
					frappe.bold(existing)
				),
				exc=frappe.ValidationError,
			)

	def _validate_cancellation_reason(self):
		if self.status == "Cancelled" and not self.cancellation_reason:
			frappe.throw(
				_("Cancellation reason is required."),
				title=_("Missing Reason"),
			)

	def _link_to_inpatient_record(self):
		frappe.db.set_value(
			"Inpatient Record",
			self.inpatient_record,
			{
				"custom_discharge_advice": self.name,
			},
			update_modified=False,
		)

	def _clear_ir_link(self):
		current = frappe.db.get_value(
			"Inpatient Record", self.inpatient_record, "custom_discharge_advice"
		)
		if current == self.name:
			frappe.db.set_value(
				"Inpatient Record",
				self.inpatient_record,
				{"custom_discharge_advice": None},
				update_modified=False,
			)

	def _add_ir_comment(self, message: str):
		try:
			ir_doc = frappe.get_doc("Inpatient Record", self.inpatient_record)
			ir_doc.add_comment("Info", message)
		except Exception:
			pass

	def _notify_departments(self):
		try:
			from alcura_ipd_ext.services.discharge_notification_service import (
				notify_discharge_advised,
			)
			notify_discharge_advised(self)
		except Exception:
			frappe.logger("alcura_ipd_ext").warning(
				f"Failed to send discharge notifications for {self.name}",
				exc_info=True,
			)
