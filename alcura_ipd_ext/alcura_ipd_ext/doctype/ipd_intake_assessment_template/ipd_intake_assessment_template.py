"""IPD Intake Assessment Template controller.

Validates template structure: unique field labels within a section,
at least one form field or scored assessment, and Select fields must
have options defined.
"""

from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document


class IPDIntakeAssessmentTemplate(Document):
	def validate(self):
		self._validate_has_content()
		self._validate_unique_field_labels()
		self._validate_select_options()

	def _validate_has_content(self):
		if not self.form_fields and not self.scored_assessments:
			frappe.throw(
				_("A template must have at least one form field or scored assessment."),
				exc=frappe.ValidationError,
			)

	def _validate_unique_field_labels(self):
		seen: set[tuple[str, str]] = set()
		for row in self.form_fields or []:
			key = (row.section_label or "", row.field_label)
			if key in seen:
				frappe.throw(
					_("Duplicate field label '{0}' in section '{1}'.").format(
						row.field_label, row.section_label or "(No Section)"
					),
					exc=frappe.ValidationError,
				)
			seen.add(key)

	def _validate_select_options(self):
		for row in self.form_fields or []:
			if row.field_type == "Select" and not (row.options or "").strip():
				frappe.throw(
					_("Field '{0}' is of type Select but has no options defined.").format(
						row.field_label
					),
					exc=frappe.ValidationError,
				)
