"""IPD Order SLA Config controller."""

from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document


class IPDOrderSLAConfig(Document):
	def validate(self):
		self._validate_unique_combination()
		self._validate_milestones()

	def _validate_unique_combination(self):
		existing = frappe.db.get_value(
			"IPD Order SLA Config",
			{"order_type": self.order_type, "urgency": self.urgency, "name": ("!=", self.name)},
		)
		if existing:
			frappe.throw(
				_("An SLA Config already exists for {0} / {1}: {2}").format(
					self.order_type, self.urgency, existing
				)
			)

	def _validate_milestones(self):
		if not self.milestones:
			frappe.throw(_("At least one milestone target is required."))
		seen = set()
		for row in self.milestones:
			if row.milestone in seen:
				frappe.throw(_("Duplicate milestone: {0}").format(row.milestone))
			seen.add(row.milestone)
			if (row.target_minutes or 0) <= 0:
				frappe.throw(
					_("Target minutes must be positive for milestone {0}.").format(row.milestone)
				)
