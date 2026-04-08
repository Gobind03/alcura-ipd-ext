"""Monitoring Protocol Bundle — master configuration for care protocols."""

from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document


class MonitoringProtocolBundle(Document):
	def validate(self):
		self._validate_steps()
		self._validate_compliance_target()

	def _validate_steps(self):
		if not self.steps:
			frappe.throw(
				_("At least one protocol step is required."),
				exc=frappe.ValidationError,
			)

		seen_names = set()
		seen_sequences = set()
		for row in self.steps:
			key = row.step_name.strip().lower()
			if key in seen_names:
				frappe.throw(
					_("Duplicate step name in row {0}: {1}").format(
						row.idx, frappe.bold(row.step_name)
					),
					exc=frappe.ValidationError,
				)
			seen_names.add(key)

			if row.sequence in seen_sequences:
				frappe.throw(
					_("Duplicate sequence number {0} in row {1}.").format(
						row.sequence, row.idx
					),
					exc=frappe.ValidationError,
				)
			seen_sequences.add(row.sequence)

			if row.due_within_minutes and row.due_within_minutes < 0:
				frappe.throw(
					_("Due-within minutes cannot be negative (row {0}).").format(row.idx),
					exc=frappe.ValidationError,
				)

			if row.recurrence_minutes and row.recurrence_minutes < 0:
				frappe.throw(
					_("Recurrence minutes cannot be negative (row {0}).").format(row.idx),
					exc=frappe.ValidationError,
				)

			if row.compliance_weight and row.compliance_weight < 0:
				frappe.throw(
					_("Compliance weight cannot be negative (row {0}).").format(row.idx),
					exc=frappe.ValidationError,
				)

	def _validate_compliance_target(self):
		if self.compliance_target_pct and (
			self.compliance_target_pct < 0 or self.compliance_target_pct > 100
		):
			frappe.throw(
				_("Compliance target must be between 0 and 100."),
				exc=frappe.ValidationError,
			)
