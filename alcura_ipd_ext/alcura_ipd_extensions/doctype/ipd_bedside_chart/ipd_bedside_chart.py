"""IPD Bedside Chart — per-admission chart schedule with overdue detection."""

from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import add_to_date, get_datetime, now_datetime


class IPDBedsideChart(Document):
	def before_insert(self):
		self.started_by = self.started_by or frappe.session.user
		self._populate_location()

	def validate(self):
		self._validate_frequency()
		self._validate_status_transition()

	def _validate_frequency(self):
		if self.frequency_minutes and self.frequency_minutes < 1:
			frappe.throw(_("Frequency must be at least 1 minute."))

	def _validate_status_transition(self):
		if not self.is_new() and self.has_value_changed("status"):
			old_status = self.get_doc_before_save().status if self.get_doc_before_save() else "Active"
			valid = {
				"Active": ("Paused", "Discontinued"),
				"Paused": ("Active", "Discontinued"),
			}
			allowed = valid.get(old_status, ())
			if self.status not in allowed:
				frappe.throw(
					_("Cannot transition from {0} to {1}.").format(old_status, self.status)
				)

			if self.status == "Discontinued":
				self.discontinued_at = now_datetime()
				self.discontinued_by = frappe.session.user

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

	@property
	def next_due_at(self):
		if not self.last_entry_at or not self.frequency_minutes:
			return self.started_at
		return add_to_date(get_datetime(self.last_entry_at), minutes=self.frequency_minutes)

	@property
	def is_overdue(self):
		if self.status != "Active":
			return False
		return now_datetime() > get_datetime(self.next_due_at)

	@property
	def overdue_minutes(self):
		if not self.is_overdue:
			return 0
		diff = now_datetime() - get_datetime(self.next_due_at)
		return int(diff.total_seconds() / 60)
