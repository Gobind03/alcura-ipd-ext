"""IPD MAR Entry — Medication Administration Record."""

from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import now_datetime


class IPDMAREntry(Document):
	def before_insert(self):
		self._populate_location()

	def validate(self):
		self._validate_administration()
		self._validate_delay()
		self._compute_shift()
		self._validate_correction()

	def after_insert(self):
		if self.is_correction and self.corrects_entry:
			frappe.db.set_value(
				"IPD MAR Entry", self.corrects_entry, "status", "Corrected",
				update_modified=False,
			)

		if self.administration_status == "Missed":
			self._raise_missed_alert()

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

	def _validate_administration(self):
		if self.administration_status == "Held":
			if not (self.hold_reason or "").strip():
				frappe.throw(_("Hold reason is required when medication is held."))

		if self.administration_status == "Refused":
			if not (self.refusal_reason or "").strip():
				frappe.throw(_("Refusal reason is required when medication is refused."))

		if self.administration_status in ("Given", "Self-Administered"):
			if not self.administered_at:
				self.administered_at = now_datetime()
			if not self.administered_by:
				self.administered_by = frappe.session.user

	def _validate_delay(self):
		if self.administration_status == "Delayed":
			if not (self.delay_reason or "").strip():
				frappe.throw(_("Delay reason is required when medication is delayed."))

	def _compute_shift(self):
		if self.scheduled_time and not self.shift:
			from alcura_ipd_ext.services.mar_schedule_service import compute_shift

			self.shift = compute_shift(self.scheduled_time)

	def _validate_correction(self):
		if self.is_correction:
			if not self.corrects_entry:
				frappe.throw(_("Correction entries must specify which entry they correct."))
			if not (self.correction_reason or "").strip():
				frappe.throw(_("A correction reason is required."))
			original_status = frappe.db.get_value(
				"IPD MAR Entry", self.corrects_entry, "status"
			)
			if original_status == "Corrected":
				frappe.throw(_("The original entry has already been corrected."))

	def _raise_missed_alert(self):
		frappe.publish_realtime(
			"mar_missed_alert",
			{
				"entry": self.name,
				"patient": self.patient,
				"inpatient_record": self.inpatient_record,
				"medication": self.medication_name,
				"scheduled_time": str(self.scheduled_time or ""),
				"ward": self.ward,
			},
			after_commit=True,
		)
