"""Controller for Admission Checklist Template."""

from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document


class AdmissionChecklistTemplate(Document):
	def validate(self):
		self._validate_items()
		self._validate_single_default()

	def _validate_items(self):
		if not self.checklist_items:
			frappe.throw(_("At least one checklist item is required."))

		labels = set()
		for row in self.checklist_items:
			if row.item_label in labels:
				frappe.throw(
					_("Duplicate item label: {0}").format(frappe.bold(row.item_label))
				)
			labels.add(row.item_label)

	def _validate_single_default(self):
		"""Only one default template per payer_type + care_setting combo."""
		if not self.is_default:
			return

		existing = frappe.db.exists(
			"Admission Checklist Template",
			{
				"is_default": 1,
				"is_active": 1,
				"payer_type": self.payer_type or "",
				"care_setting": self.care_setting or "All",
				"name": ("!=", self.name),
			},
		)
		if existing:
			frappe.throw(
				_("Another default template already exists for payer type "
				  "'{0}' / care setting '{1}': {2}").format(
					self.payer_type or "All",
					self.care_setting or "All",
					frappe.bold(existing),
				)
			)
