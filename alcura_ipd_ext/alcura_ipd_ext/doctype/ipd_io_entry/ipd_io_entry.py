"""IPD IO Entry — Intake/Output fluid recording."""

from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import get_datetime, now_datetime


class IPDIOEntry(Document):
	def before_insert(self):
		self.recorded_by = self.recorded_by or frappe.session.user
		self._populate_location()

	def validate(self):
		self._validate_volume()
		self._validate_correction()
		self._validate_entry_datetime()

	def after_insert(self):
		if self.is_correction and self.corrects_entry:
			frappe.db.set_value(
				"IPD IO Entry", self.corrects_entry, "status", "Corrected",
				update_modified=False,
			)

	def _populate_location(self):
		if self.inpatient_record:
			ir = frappe.db.get_value(
				"Inpatient Record",
				self.inpatient_record,
				["custom_current_ward", "custom_current_bed"],
				as_dict=True,
			)
			if ir:
				self.ward = ir.custom_current_ward
				self.bed = ir.custom_current_bed

	def _validate_volume(self):
		if not self.volume_ml or self.volume_ml <= 0:
			frappe.throw(_("Volume must be greater than 0."))

	def _validate_correction(self):
		if self.is_correction:
			if not self.corrects_entry:
				frappe.throw(_("Correction entries must specify which entry they correct."))
			if not (self.correction_reason or "").strip():
				frappe.throw(_("A correction reason is required."))
			original_status = frappe.db.get_value(
				"IPD IO Entry", self.corrects_entry, "status"
			)
			if original_status == "Corrected":
				frappe.throw(_("The original entry has already been corrected."))

	def _validate_entry_datetime(self):
		if self.entry_datetime:
			tolerance_minutes = 5
			future_limit = frappe.utils.add_to_date(now_datetime(), minutes=tolerance_minutes)
			if get_datetime(self.entry_datetime) > future_limit:
				frappe.throw(_("Entry date/time cannot be in the future."))
