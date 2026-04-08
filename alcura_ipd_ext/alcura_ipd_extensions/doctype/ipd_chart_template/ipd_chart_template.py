"""IPD Chart Template — master definition for parameter-based charts."""

from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document


class IPDChartTemplate(Document):
	def validate(self):
		self._validate_parameters()
		self._validate_frequency()

	def _validate_parameters(self):
		if not self.parameters:
			frappe.throw(_("At least one chart parameter is required."))

		seen: set[str] = set()
		for row in self.parameters:
			key = row.parameter_name.strip().lower()
			if key in seen:
				frappe.throw(
					_("Duplicate parameter name '{0}' at row {1}.").format(
						row.parameter_name, row.idx
					)
				)
			seen.add(key)

			if row.parameter_type == "Select" and not (row.options or "").strip():
				frappe.throw(
					_("Parameter '{0}' is Select type but has no options defined.").format(
						row.parameter_name
					)
				)

			if row.parameter_type == "Numeric":
				if row.min_value and row.max_value and row.min_value >= row.max_value:
					frappe.throw(
						_("Parameter '{0}': min_value must be less than max_value.").format(
							row.parameter_name
						)
					)

	def _validate_frequency(self):
		if self.default_frequency_minutes and self.default_frequency_minutes < 1:
			frappe.throw(_("Default frequency must be at least 1 minute."))
