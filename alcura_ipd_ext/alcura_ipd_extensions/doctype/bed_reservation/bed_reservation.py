"""Server controller for Bed Reservation."""

from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import get_datetime

from alcura_ipd_ext.services.bed_reservation_service import (
	activate_reservation,
	cancel_reservation,
	compute_reservation_end,
	consume_reservation,
	get_default_timeout,
	validate_transition,
)


class BedReservation(Document):
	def before_insert(self):
		self._set_default_timeout()
		self._compute_end()
		self.status = "Draft"

	def validate(self):
		self._validate_type_fields()
		self._validate_reservation_window()
		self._validate_company_match()
		self._compute_end()

	# ── Whitelisted server actions ──────────────────────────────────

	@frappe.whitelist()
	def action_activate(self):
		activate_reservation(self.name)
		self.reload()

	@frappe.whitelist()
	def action_cancel(self, reason: str = "", is_override: bool = False, override_reason: str = ""):
		cancel_reservation(
			self.name,
			reason=reason,
			is_override=is_override,
			override_reason=override_reason,
		)
		self.reload()

	@frappe.whitelist()
	def action_consume(self, inpatient_record: str = ""):
		consume_reservation(self.name, inpatient_record=inpatient_record)
		self.reload()

	# ── Private validation helpers ──────────────────────────────────

	def _set_default_timeout(self):
		if not self.timeout_minutes:
			self.timeout_minutes = get_default_timeout()

	def _compute_end(self):
		if self.reservation_start and self.timeout_minutes:
			self.reservation_end = compute_reservation_end(
				self.reservation_start, int(self.timeout_minutes)
			)

	def _validate_type_fields(self):
		if self.reservation_type == "Specific Bed":
			if not self.hospital_bed:
				frappe.throw(
					_("Hospital Bed is required for Specific Bed reservations."),
					exc=frappe.ValidationError,
				)
			bed_data = frappe.db.get_value(
				"Hospital Bed",
				self.hospital_bed,
				["hospital_room", "hospital_ward", "service_unit_type"],
				as_dict=True,
			)
			if bed_data:
				self.hospital_room = bed_data.hospital_room
				self.hospital_ward = bed_data.hospital_ward
				if not self.service_unit_type:
					self.service_unit_type = bed_data.service_unit_type

		elif self.reservation_type == "Room Type Hold":
			if not self.service_unit_type:
				frappe.throw(
					_("Room Type is required for Room Type Hold reservations."),
					exc=frappe.ValidationError,
				)

	def _validate_reservation_window(self):
		if self.reservation_start and self.reservation_end:
			if get_datetime(self.reservation_end) <= get_datetime(self.reservation_start):
				frappe.throw(
					_("Reservation End must be after Reservation Start."),
					exc=frappe.ValidationError,
				)

		if self.timeout_minutes is not None and int(self.timeout_minutes) <= 0:
			frappe.throw(
				_("Timeout must be a positive number of minutes."),
				exc=frappe.ValidationError,
			)

	def _validate_company_match(self):
		if (
			self.reservation_type == "Specific Bed"
			and self.hospital_bed
			and self.company
		):
			bed_company = frappe.db.get_value("Hospital Bed", self.hospital_bed, "company")
			if bed_company and bed_company != self.company:
				frappe.throw(
					_("Bed company ({0}) does not match reservation company ({1}).").format(
						bed_company, self.company
					),
					exc=frappe.ValidationError,
				)
