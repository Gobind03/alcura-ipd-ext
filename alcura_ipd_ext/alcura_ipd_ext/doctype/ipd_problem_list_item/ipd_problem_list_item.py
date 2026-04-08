"""IPD Problem List Item — tracks active clinical problems per admission (US-E5)."""

from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import now_datetime


class IPDProblemListItem(Document):
	def before_insert(self):
		self.added_on = self.added_on or now_datetime()
		self._resolve_added_by()

	def validate(self):
		self._validate_ir_status()
		self._handle_resolution()

	def after_insert(self):
		self._update_ir_count()

	def on_update(self):
		self._update_ir_count()

	def on_trash(self):
		self._update_ir_count()

	def _resolve_added_by(self):
		if self.added_by:
			return
		practitioner = frappe.db.get_value(
			"Healthcare Practitioner",
			{"user_id": frappe.session.user},
			"name",
		)
		if practitioner:
			self.added_by = practitioner

	def _validate_ir_status(self):
		if not self.inpatient_record:
			return
		ir_status = frappe.db.get_value(
			"Inpatient Record", self.inpatient_record, "status"
		)
		if ir_status and ir_status not in ("Admitted", "Admission Scheduled"):
			frappe.throw(
				_("Cannot modify problem list: Inpatient Record {0} is in '{1}' status.").format(
					frappe.bold(self.inpatient_record), ir_status
				),
				exc=frappe.ValidationError,
			)

	def _handle_resolution(self):
		"""Set resolved_by / resolved_on when status transitions to Resolved."""
		if self.status == "Resolved" and not self.resolved_on:
			self.resolved_on = now_datetime()
			if not self.resolved_by:
				practitioner = frappe.db.get_value(
					"Healthcare Practitioner",
					{"user_id": frappe.session.user},
					"name",
				)
				if practitioner:
					self.resolved_by = practitioner

		if self.status != "Resolved":
			self.resolved_on = None
			self.resolved_by = None

	def _update_ir_count(self):
		if not self.inpatient_record:
			return
		count = frappe.db.count(
			"IPD Problem List Item",
			{"inpatient_record": self.inpatient_record, "status": ("in", ("Active", "Monitoring"))},
		)
		frappe.db.set_value(
			"Inpatient Record",
			self.inpatient_record,
			"custom_active_problems_count",
			count,
			update_modified=False,
		)
