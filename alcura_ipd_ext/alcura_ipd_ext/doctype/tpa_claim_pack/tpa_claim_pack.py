"""TPA Claim Pack controller.

Manages the lifecycle of TPA claim submission packs. Tracks document
availability, submission status, and settlement outcomes.
"""

from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import now_datetime


VALID_TRANSITIONS: dict[str, tuple[str, ...]] = {
	"Draft": ("In Review",),
	"In Review": ("Submitted", "Draft"),
	"Submitted": ("Acknowledged", "Disputed"),
	"Acknowledged": ("Settled", "Disputed"),
	"Settled": (),
	"Disputed": ("Submitted",),
}


class TPAClaimPack(Document):
	def before_insert(self):
		self.prepared_by = frappe.session.user
		self.prepared_on = now_datetime()

	def validate(self):
		self._validate_status_transition()
		self._validate_mandatory_documents()

	def on_update(self):
		if self.has_value_changed("status"):
			self._on_status_change()

	@frappe.whitelist()
	def action_send_for_review(self):
		self._transition_to("In Review")

	@frappe.whitelist()
	def action_mark_submitted(self):
		self._transition_to("Submitted")

	@frappe.whitelist()
	def action_mark_acknowledged(self):
		self._transition_to("Acknowledged")

	@frappe.whitelist()
	def action_mark_settled(self, settlement_amount: float = 0, settlement_reference: str = ""):
		if settlement_amount:
			self.settlement_amount = settlement_amount
		if settlement_reference:
			self.settlement_reference = settlement_reference
		self.settlement_date = frappe.utils.today()
		self._transition_to("Settled")

	@frappe.whitelist()
	def action_mark_disputed(self, disallowance_amount: float = 0, reason: str = ""):
		if disallowance_amount:
			self.disallowance_amount = disallowance_amount
		if reason:
			self.disallowance_reason = reason
		self._transition_to("Disputed")

	@frappe.whitelist()
	def refresh_document_availability(self):
		"""Check which documents have attachments and update is_available."""
		from alcura_ipd_ext.services.claim_pack_service import (
			refresh_document_availability,
		)

		refresh_document_availability(self.name)
		self.reload()

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

	def _validate_mandatory_documents(self):
		"""Warn if mandatory documents are not yet available."""
		if self.status in ("Submitted", "In Review"):
			missing = [
				row.document_type for row in self.documents
				if row.is_mandatory and not row.is_available and not row.file_attachment
			]
			if missing:
				frappe.msgprint(
					_("Missing mandatory documents: {0}").format(", ".join(missing)),
					title=_("Pending Documents"),
					indicator="orange",
				)

	def _on_status_change(self):
		now = now_datetime()
		user = frappe.session.user
		updates: dict = {}

		if self.status == "In Review":
			updates["reviewed_by"] = user
			updates["reviewed_on"] = now
		elif self.status == "Submitted":
			updates["submitted_by_user"] = user
			updates["submitted_on_datetime"] = now
			if not self.submission_date:
				updates["submission_date"] = frappe.utils.today()

		if updates:
			self.db_set(updates, update_modified=False)
			self.reload()

		self._add_timeline_comment()

	def _add_timeline_comment(self):
		msg = _("TPA Claim Pack {0} status changed to {1} by {2}").format(
			frappe.bold(self.name),
			frappe.bold(self.status),
			frappe.session.user,
		)
		if self.inpatient_record:
			try:
				frappe.get_doc("Inpatient Record", self.inpatient_record).add_comment("Info", msg)
			except Exception:
				pass
