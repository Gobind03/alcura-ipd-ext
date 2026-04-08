"""ICU Monitoring Profile — maps ward classifications to chart templates.

Ensures that when a patient is admitted to or transferred into a specific
unit type (e.g. MICU), the correct set of bedside charts is auto-started.
"""

from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document


class ICUMonitoringProfile(Document):
	def validate(self):
		self._validate_unique_unit_company()
		self._validate_templates()
		self._validate_frequency_overrides()

	def _validate_unique_unit_company(self):
		"""Only one active profile per (unit_type, company) pair."""
		if not self.is_active:
			return

		filters = {
			"unit_type": self.unit_type,
			"is_active": 1,
			"name": ("!=", self.name),
		}
		if self.company:
			filters["company"] = self.company
		else:
			filters["company"] = ("is", "not set")

		duplicate = frappe.db.exists("ICU Monitoring Profile", filters)
		if duplicate:
			frappe.throw(
				_("An active monitoring profile already exists for unit type {0}{1}: {2}").format(
					frappe.bold(self.unit_type),
					f" / {frappe.bold(self.company)}" if self.company else "",
					frappe.bold(duplicate),
				),
				exc=frappe.ValidationError,
			)

	def _validate_templates(self):
		if not self.chart_templates:
			frappe.throw(
				_("At least one chart template is required."),
				exc=frappe.ValidationError,
			)

		seen = set()
		for row in self.chart_templates:
			if row.chart_template in seen:
				frappe.throw(
					_("Duplicate chart template in row {0}: {1}").format(
						row.idx, frappe.bold(row.chart_template)
					),
					exc=frappe.ValidationError,
				)
			seen.add(row.chart_template)

			if not frappe.db.get_value(
				"IPD Chart Template", row.chart_template, "is_active"
			):
				frappe.throw(
					_("Chart template {0} (row {1}) is not active.").format(
						frappe.bold(row.chart_template), row.idx
					),
					exc=frappe.ValidationError,
				)

	def _validate_frequency_overrides(self):
		for row in self.chart_templates:
			if row.frequency_override and row.frequency_override < 1:
				frappe.throw(
					_("Frequency override must be at least 1 minute (row {0}).").format(row.idx),
					exc=frappe.ValidationError,
				)
