"""Discharge Billing Checklist controller.

Manages the discharge readiness checklist. Supports auto-derived
status checks, manual clearance, waivers, and authorized overrides.
"""

from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import now_datetime


class DischargeBillingChecklist(Document):
	def before_insert(self):
		self.created_by = frappe.session.user

	def validate(self):
		self._validate_waiver_reasons()
		self._update_status()

	@frappe.whitelist()
	def refresh_auto_checks(self):
		"""Re-evaluate all auto-derived checklist items from live data."""
		from alcura_ipd_ext.services.discharge_checklist_service import refresh_auto_checks

		refresh_auto_checks(self.name)
		self.reload()

	@frappe.whitelist()
	def authorize_override(self, reason: str = ""):
		"""Override all pending items and mark checklist as Overridden."""
		if not reason:
			frappe.throw(_("Override reason is required"), title=_("Missing Reason"))

		self.override_authorized = 1
		self.override_by = frappe.session.user
		self.override_datetime = now_datetime()
		self.override_reason = reason
		self.status = "Overridden"
		self.save()

	@frappe.whitelist()
	def clear_item(self, item_idx: int):
		"""Manually clear a checklist item."""
		for row in self.items:
			if row.idx == int(item_idx):
				row.check_status = "Cleared"
				row.cleared_by = frappe.session.user
				row.cleared_on = now_datetime()
				break
		self.save()

	@frappe.whitelist()
	def waive_item(self, item_idx: int, reason: str = ""):
		"""Waive a checklist item with a reason."""
		if not reason:
			frappe.throw(_("Waiver reason is required"), title=_("Missing Reason"))
		for row in self.items:
			if row.idx == int(item_idx):
				row.check_status = "Waived"
				row.waiver_reason = reason
				row.cleared_by = frappe.session.user
				row.cleared_on = now_datetime()
				break
		self.save()

	def _validate_waiver_reasons(self):
		for row in self.items:
			if row.check_status == "Waived" and not row.waiver_reason:
				frappe.throw(
					_("Row {0} ({1}): Waiver reason is required").format(
						row.idx, row.check_name
					),
					title=_("Missing Waiver Reason"),
				)

	def _update_status(self):
		"""Derive overall status from item statuses."""
		if self.override_authorized:
			self.status = "Overridden"
			return

		statuses = {row.check_status for row in self.items}
		if not statuses or statuses <= {"Cleared", "Waived", "Not Applicable"}:
			self.status = "Cleared"
			if not self.completed_by:
				self.completed_by = frappe.session.user
				self.completed_on = now_datetime()
		elif "Pending" in statuses:
			has_any_cleared = statuses & {"Cleared", "Waived"}
			self.status = "In Progress" if has_any_cleared else "Pending"
		else:
			self.status = "In Progress"
