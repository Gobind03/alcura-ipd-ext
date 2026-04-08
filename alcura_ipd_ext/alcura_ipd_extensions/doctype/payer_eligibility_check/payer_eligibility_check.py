"""Payer Eligibility Check controller.

Manages the lifecycle of payer eligibility verifications. Enforces
status transition rules, audit field population, and cross-validation
against Patient Payer Profile ownership.
"""

from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate, now_datetime

VALID_TRANSITIONS: dict[str, tuple[str, ...]] = {
	"Pending": ("Verified", "Conditional", "Rejected"),
	"Verified": ("Expired",),
	"Conditional": ("Verified", "Rejected", "Expired"),
	"Rejected": ("Pending",),
	"Expired": ("Pending",),
}

_VERIFIED_STATUSES = ("Verified", "Conditional", "Rejected")


class PayerEligibilityCheck(Document):
	def before_insert(self):
		self.submitted_by = frappe.session.user
		self.submitted_on = now_datetime()
		self.last_status_change_by = frappe.session.user
		self.last_status_change_on = now_datetime()

	def validate(self):
		self._validate_date_range()
		self._validate_profile_ownership()
		self._validate_status_transition()

	def on_update(self):
		if self.has_value_changed("verification_status"):
			self._on_status_change()

	def _validate_date_range(self):
		if self.valid_from and self.valid_to:
			if getdate(self.valid_from) > getdate(self.valid_to):
				frappe.throw(
					_("Valid From ({0}) cannot be after Valid To ({1})").format(
						self.valid_from, self.valid_to
					),
					title=_("Invalid Date Range"),
				)

	def _validate_profile_ownership(self):
		"""Ensure the payer profile belongs to the same patient."""
		if not self.patient_payer_profile:
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

	def _validate_status_transition(self):
		"""Enforce allowed status transitions on existing records."""
		if self.is_new():
			return

		old_status = self.get_db_value("verification_status")
		new_status = self.verification_status

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

	def _on_status_change(self):
		"""Handle side-effects when verification_status changes."""
		now = now_datetime()
		user = frappe.session.user

		updates = {
			"last_status_change_by": user,
			"last_status_change_on": now,
		}

		if self.verification_status in _VERIFIED_STATUSES:
			updates["verified_by"] = user
			updates["verification_datetime"] = now

		self.db_set(updates, update_modified=False)
		self.reload()

		self._add_timeline_comments()
		self._send_status_notifications()

	def _add_timeline_comments(self):
		"""Post timeline comments on linked Patient and Inpatient Record."""
		status = self.verification_status
		msg = _("Payer eligibility check {0} marked as {1} by {2}").format(
			frappe.bold(self.name),
			frappe.bold(status),
			frappe.session.user,
		)

		if self.patient:
			try:
				frappe.get_doc("Patient", self.patient).add_comment("Info", msg)
			except Exception:
				pass

		if self.inpatient_record:
			try:
				frappe.get_doc("Inpatient Record", self.inpatient_record).add_comment(
					"Info", msg
				)
			except Exception:
				pass

	def _send_status_notifications(self):
		"""Send in-app notifications on Rejected or Expired status changes."""
		if self.verification_status == "Rejected":
			self._notify_roles(
				("Healthcare Receptionist", "TPA Desk User"),
				_("Payer eligibility REJECTED for {0} ({1})").format(
					self.patient_name or self.patient, self.name
				),
			)
		elif self.verification_status == "Expired":
			self._notify_roles(
				("TPA Desk User",),
				_("Payer eligibility EXPIRED for {0} ({1})").format(
					self.patient_name or self.patient, self.name
				),
			)

	def _notify_roles(self, roles: tuple[str, ...], subject: str):
		"""Create Notification Log entries for users with the given roles."""
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
