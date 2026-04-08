"""IPD Intake Assessment controller.

Handles validation of mandatory responses, status transitions,
and audit field population.
"""

from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import now_datetime


class IPDIntakeAssessment(Document):
	def validate(self):
		self._set_status_on_save()

	def _set_status_on_save(self):
		"""Transition from Draft → In Progress when any response has data."""
		if self.status == "Completed":
			return

		has_any_response = False
		for row in self.responses or []:
			if (row.text_value or "").strip() or row.numeric_value or row.check_value:
				has_any_response = True
				break

		if has_any_response and self.status == "Draft":
			self.status = "In Progress"

	def complete(self):
		"""Validate mandatory fields and transition to Completed."""
		missing = []
		for row in self.responses or []:
			if not row.is_mandatory:
				continue
			has_value = (
				(row.text_value or "").strip()
				or row.numeric_value
				or row.check_value
			)
			if not has_value:
				missing.append(f"{row.section_label or ''} → {row.field_label}")

		if missing:
			frappe.throw(
				_("The following mandatory fields are not filled:<br>{0}").format(
					"<br>".join(f"• {m}" for m in missing)
				),
				exc=frappe.ValidationError,
			)

		self.status = "Completed"
		self.completed_by = frappe.session.user
		self.completed_on = now_datetime()
		self.save(ignore_permissions=True)

		if self.inpatient_record:
			frappe.get_doc("Inpatient Record", self.inpatient_record).add_comment(
				"Info",
				_("Intake Assessment {0} completed by {1}.").format(
					frappe.bold(self.name), frappe.session.user
				),
			)

			from alcura_ipd_ext.services.nursing_risk_service import update_risk_flags

			update_risk_flags(self.inpatient_record)
