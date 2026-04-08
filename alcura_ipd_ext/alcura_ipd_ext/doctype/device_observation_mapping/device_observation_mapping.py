"""Device Observation Mapping — configuration for device-to-chart parameter mapping."""

from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document


class DeviceObservationMapping(Document):
	def validate(self):
		self._validate_mappings()

	def _validate_mappings(self):
		if not self.mappings:
			frappe.throw(
				_("At least one parameter mapping is required."),
				exc=frappe.ValidationError,
			)

		seen_device = set()
		for row in self.mappings:
			if row.device_parameter in seen_device:
				frappe.throw(
					_("Duplicate device parameter in row {0}: {1}").format(
						row.idx, frappe.bold(row.device_parameter)
					),
					exc=frappe.ValidationError,
				)
			seen_device.add(row.device_parameter)

			if row.unit_conversion_factor == 0:
				frappe.throw(
					_("Conversion factor cannot be zero (row {0}).").format(row.idx),
					exc=frappe.ValidationError,
				)
