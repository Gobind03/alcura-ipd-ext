"""Device Observation Feed — records incoming device readings for audit and processing."""

from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document


class DeviceObservationFeed(Document):
	def validate(self):
		if not self.source_device_type:
			frappe.throw(_("Device type is required."), exc=frappe.ValidationError)
		if not self.source_device_id:
			frappe.throw(_("Device ID is required."), exc=frappe.ValidationError)
