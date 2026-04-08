"""Server controller for Nursing Discharge Checklist.

Manages the nursing discharge checklist lifecycle with item-level
completion tracking, mandatory item enforcement, and signoff/verification.
"""

from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import now_datetime


class NursingDischargeChecklist(Document):
	def validate(self):
		self._validate_skip_reasons()
		self._update_progress()
		self._update_status()

	@frappe.whitelist()
	def complete_item(self, item_idx: int):
		"""Mark a checklist item as Done."""
		for row in self.items:
			if row.idx == int(item_idx):
				row.item_status = "Done"
				row.completed_by = frappe.session.user
				row.completed_on = now_datetime()
				break
		self.save()

	@frappe.whitelist()
	def mark_not_applicable(self, item_idx: int):
		"""Mark a checklist item as Not Applicable."""
		for row in self.items:
			if row.idx == int(item_idx):
				row.item_status = "Not Applicable"
				row.completed_by = frappe.session.user
				row.completed_on = now_datetime()
				break
		self.save()

	@frappe.whitelist()
	def skip_item(self, item_idx: int, reason: str = ""):
		"""Skip a checklist item with mandatory reason."""
		if not reason:
			frappe.throw(_("Skip reason is required."), title=_("Missing Reason"))
		for row in self.items:
			if row.idx == int(item_idx):
				row.item_status = "Skipped"
				row.skip_reason = reason
				row.completed_by = frappe.session.user
				row.completed_on = now_datetime()
				break
		self.save()

	@frappe.whitelist()
	def sign_off(self, handover_notes: str = ""):
		"""Complete the checklist with signoff."""
		pending_mandatory = [
			row.item_name for row in self.items
			if row.is_mandatory and row.item_status == "Pending"
		]
		if pending_mandatory:
			frappe.throw(
				_("Cannot sign off. Mandatory items pending: {0}").format(
					", ".join(pending_mandatory)
				),
				title=_("Mandatory Items Incomplete"),
			)

		if handover_notes:
			self.handover_notes = handover_notes
		self.completed_by = frappe.session.user
		self.completed_on = now_datetime()
		self.status = "Completed"
		self.save()

		self._add_ir_comment(
			_("Nursing discharge checklist completed and signed off by {0}").format(
				frappe.bold(frappe.session.user)
			)
		)

	@frappe.whitelist()
	def verify(self):
		"""Senior nurse verification of completed checklist."""
		if self.status != "Completed":
			frappe.throw(
				_("Checklist must be completed before verification."),
				exc=frappe.ValidationError,
			)
		self.verified_by = frappe.session.user
		self.verified_on = now_datetime()
		self.save()

		self._add_ir_comment(
			_("Nursing discharge handover verified by {0}").format(
				frappe.bold(frappe.session.user)
			)
		)

	# ── Private helpers ──────────────────────────────────────────────

	def _validate_skip_reasons(self):
		for row in self.items:
			if row.item_status == "Skipped" and not row.skip_reason:
				frappe.throw(
					_("Row {0} ({1}): Skip reason is required.").format(
						row.idx, row.item_name
					),
					title=_("Missing Skip Reason"),
				)

	def _update_progress(self):
		self.total_items = len(self.items)
		self.completed_items = sum(
			1 for row in self.items
			if row.item_status in ("Done", "Not Applicable", "Skipped")
		)

	def _update_status(self):
		if self.status == "Completed":
			return

		if self.completed_items == 0:
			self.status = "Pending"
		elif self.completed_items < self.total_items:
			self.status = "In Progress"
		else:
			self.status = "In Progress"

	def _add_ir_comment(self, message: str):
		try:
			ir_doc = frappe.get_doc("Inpatient Record", self.inpatient_record)
			ir_doc.add_comment("Info", message)
		except Exception:
			pass
