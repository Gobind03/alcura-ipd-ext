"""IPD Nursing Note — narrative nursing documentation with addendum support."""

from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import get_datetime, now_datetime


class IPDNursingNote(Document):
	def before_insert(self):
		self.recorded_by = self.recorded_by or frappe.session.user
		self._populate_location()

	def validate(self):
		self._validate_note_text()
		self._validate_addendum()
		self._validate_datetime()

	def after_insert(self):
		if self.is_addendum and self.addendum_to:
			frappe.db.set_value(
				"IPD Nursing Note", self.addendum_to, "status", "Amended",
				update_modified=False,
			)

		if self.urgency == "Critical":
			self._raise_critical_note_alert()

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

	def _validate_note_text(self):
		if not (self.note_text or "").strip():
			frappe.throw(_("Note text is required."))

	def _validate_addendum(self):
		if self.is_addendum:
			if not self.addendum_to:
				frappe.throw(_("Addendum notes must reference the original note."))
			if not (self.addendum_reason or "").strip():
				frappe.throw(_("An addendum reason is required."))
			original_status = frappe.db.get_value(
				"IPD Nursing Note", self.addendum_to, "status"
			)
			if original_status == "Amended":
				frappe.throw(_("The original note has already been amended."))

	def _validate_datetime(self):
		if self.note_datetime:
			tolerance_minutes = 5
			future_limit = frappe.utils.add_to_date(now_datetime(), minutes=tolerance_minutes)
			if get_datetime(self.note_datetime) > future_limit:
				frappe.throw(_("Note date/time cannot be in the future."))

	def _raise_critical_note_alert(self):
		frappe.publish_realtime(
			"critical_nursing_note",
			{
				"note": self.name,
				"patient": self.patient,
				"inpatient_record": self.inpatient_record,
				"category": self.category,
				"ward": self.ward,
			},
			after_commit=True,
		)
