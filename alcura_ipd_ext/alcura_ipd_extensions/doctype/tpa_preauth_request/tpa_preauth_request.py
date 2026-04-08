"""TPA Preauth Request controller.

Manages the lifecycle of pre-authorization requests to TPA/insurers.
Enforces status transitions, populates audit fields, and sends
notifications on key status changes.
"""

from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate, now_datetime


VALID_TRANSITIONS: dict[str, tuple[str, ...]] = {
	"Draft": ("Submitted",),
	"Submitted": ("Query Raised", "Approved", "Partially Approved", "Rejected"),
	"Query Raised": ("Resubmitted",),
	"Resubmitted": ("Query Raised", "Approved", "Partially Approved", "Rejected"),
	"Approved": ("Closed",),
	"Partially Approved": ("Closed",),
	"Rejected": ("Closed", "Submitted"),
	"Closed": (),
}

_APPROVAL_STATUSES = ("Approved", "Partially Approved")
_REJECTION_STATUSES = ("Rejected",)
_NOTIFY_TPA_STATUSES = ("Query Raised",)
_NOTIFY_PHYSICIAN_STATUSES = ("Approved", "Partially Approved", "Rejected")


class TPAPreauthRequest(Document):
	def before_insert(self):
		self.last_status_change_by = frappe.session.user
		self.last_status_change_on = now_datetime()

	def validate(self):
		self._validate_date_range()
		self._validate_profile_patient_match()
		self._validate_approved_amount()
		self._validate_status_transition()
		self._auto_fill_response_metadata()

	def on_update(self):
		if self.has_value_changed("status"):
			self._on_status_change()

	# ── Whitelisted status transition methods ───────────────────

	@frappe.whitelist()
	def action_submit_request(self):
		"""Transition from Draft to Submitted."""
		self._transition_to("Submitted")

	@frappe.whitelist()
	def action_raise_query(self):
		"""Transition to Query Raised."""
		self._transition_to("Query Raised")

	@frappe.whitelist()
	def action_resubmit(self):
		"""Transition from Query Raised to Resubmitted."""
		self._transition_to("Resubmitted")

	@frappe.whitelist()
	def action_approve(self, approved_amount: float | None = None):
		"""Transition to Approved."""
		if approved_amount is not None:
			self.approved_amount = approved_amount
		self._transition_to("Approved")

	@frappe.whitelist()
	def action_partially_approve(self, approved_amount: float | None = None):
		"""Transition to Partially Approved."""
		if approved_amount is not None:
			self.approved_amount = approved_amount
		self._transition_to("Partially Approved")

	@frappe.whitelist()
	def action_reject(self):
		"""Transition to Rejected."""
		self._transition_to("Rejected")

	@frappe.whitelist()
	def action_close(self):
		"""Transition to Closed."""
		self._transition_to("Closed")

	# ── Internal helpers ────────────────────────────────────────

	def _transition_to(self, new_status: str):
		old_status = self.status
		allowed = VALID_TRANSITIONS.get(old_status, ())
		if new_status not in allowed:
			frappe.throw(
				_("Cannot change status from {0} to {1}. Allowed: {2}").format(
					frappe.bold(old_status),
					frappe.bold(new_status),
					", ".join(allowed) or _("none"),
				),
				title=_("Invalid Status Transition"),
			)
		self.status = new_status
		self.save()

	def _validate_date_range(self):
		if self.valid_from and self.valid_to:
			if getdate(self.valid_from) > getdate(self.valid_to):
				frappe.throw(
					_("Valid From ({0}) cannot be after Valid To ({1})").format(
						self.valid_from, self.valid_to
					),
					title=_("Invalid Date Range"),
				)

	def _validate_profile_patient_match(self):
		"""Ensure payer profile belongs to the same patient."""
		if not self.patient_payer_profile or not self.patient:
			return
		profile_patient = frappe.db.get_value(
			"Patient Payer Profile", self.patient_payer_profile, "patient"
		)
		if profile_patient and profile_patient != self.patient:
			frappe.throw(
				_("Payer Profile {0} belongs to Patient {1}, not {2}").format(
					self.patient_payer_profile, profile_patient, self.patient
				),
				title=_("Patient Mismatch"),
			)

	def _validate_approved_amount(self):
		if self.status in _APPROVAL_STATUSES and not self.approved_amount:
			frappe.throw(
				_("Approved Amount is required when status is {0}").format(self.status),
				title=_("Missing Approved Amount"),
			)

	def _validate_status_transition(self):
		if self.is_new():
			return
		old_status = self.get_db_value("status")
		new_status = self.status
		if old_status == new_status:
			return
		allowed = VALID_TRANSITIONS.get(old_status, ())
		if new_status not in allowed:
			frappe.throw(
				_("Cannot change status from {0} to {1}. Allowed: {2}").format(
					frappe.bold(old_status),
					frappe.bold(new_status),
					", ".join(allowed) or _("none"),
				),
				title=_("Invalid Status Transition"),
			)

	def _auto_fill_response_metadata(self):
		"""Auto-populate response_by and response_datetime for new child rows."""
		now = now_datetime()
		for row in self.responses or []:
			if not row.response_by:
				row.response_by = frappe.session.user
			if not row.response_datetime:
				row.response_datetime = now

	def _on_status_change(self):
		now = now_datetime()
		user = frappe.session.user
		updates: dict = {
			"last_status_change_by": user,
			"last_status_change_on": now,
		}

		if self.status == "Submitted" and not self.submitted_by:
			updates["submitted_by"] = user
			updates["submitted_on"] = now
		elif self.status in _APPROVAL_STATUSES:
			updates["approved_by"] = user
			updates["approved_on"] = now
		elif self.status in _REJECTION_STATUSES:
			updates["rejected_by"] = user
			updates["rejected_on"] = now
		elif self.status == "Closed":
			updates["closed_by"] = user
			updates["closed_on"] = now

		self.db_set(updates, update_modified=False)
		self.reload()

		self._add_timeline_comments()
		self._send_notifications()

	def _add_timeline_comments(self):
		msg = _("TPA Preauth {0} status changed to {1} by {2}").format(
			frappe.bold(self.name),
			frappe.bold(self.status),
			frappe.session.user,
		)
		if self.patient:
			try:
				frappe.get_doc("Patient", self.patient).add_comment("Info", msg)
			except Exception:
				pass
		if self.inpatient_record:
			try:
				frappe.get_doc("Inpatient Record", self.inpatient_record).add_comment("Info", msg)
			except Exception:
				pass

	def _send_notifications(self):
		if self.status in _NOTIFY_TPA_STATUSES:
			self._notify_roles(
				("TPA Desk User",),
				_("TPA Preauth {0} — Query Raised for {1}").format(
					self.name, self.patient_name or self.patient
				),
			)
		elif self.status in _NOTIFY_PHYSICIAN_STATUSES:
			self._notify_roles(
				("Physician",),
				_("TPA Preauth {0} — {1} for {2}").format(
					self.name, self.status, self.patient_name or self.patient
				),
			)

	def _notify_roles(self, roles: tuple[str, ...], subject: str):
		users: set[str] = set()
		for role in roles:
			role_users = frappe.db.get_all(
				"Has Role",
				filters={"role": role, "parenttype": "User"},
				fields=["parent"],
			)
			users.update(u.parent for u in role_users)
		users.discard("Administrator")
		users.discard("Guest")

		for user in users:
			notification = frappe.new_doc("Notification Log")
			notification.update({
				"for_user": user,
				"from_user": frappe.session.user,
				"type": "Alert",
				"document_type": self.doctype,
				"document_name": self.name,
				"subject": subject,
			})
			notification.insert(ignore_permissions=True)
