"""Active Protocol Bundle — tracks an activated protocol for a specific admission."""

from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document


class ActiveProtocolBundle(Document):
	def validate(self):
		if not self.is_new() and self.has_value_changed("status"):
			self._validate_status_transition()

	def _validate_status_transition(self):
		old_status = self.get_doc_before_save().status if self.get_doc_before_save() else "Active"
		valid = {
			"Active": ("Completed", "Discontinued", "Expired"),
		}
		allowed = valid.get(old_status, ())
		if self.status not in allowed:
			frappe.throw(
				_("Cannot transition from {0} to {1}.").format(old_status, self.status),
				exc=frappe.ValidationError,
			)
