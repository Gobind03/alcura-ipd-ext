"""Server controller for Bed Housekeeping Task.

Tracks individual bed cleaning jobs with SLA monitoring,
TAT computation, and bed state synchronization.
"""

from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import now_datetime, time_diff_in_seconds


VALID_TRANSITIONS: dict[str, list[str]] = {
	"Pending": ["In Progress", "Cancelled"],
	"In Progress": ["Completed", "Cancelled"],
	"Completed": [],
	"Cancelled": [],
}


class BedHousekeepingTask(Document):
	def validate(self):
		self._validate_no_duplicate_active()
		self._compute_turnaround()

	@frappe.whitelist()
	def start_task(self):
		"""Start the cleaning task."""
		self._transition_to("In Progress")
		self.started_on = now_datetime()
		self.started_by = frappe.session.user
		self.save()

		frappe.db.set_value(
			"Hospital Bed", self.hospital_bed,
			"housekeeping_status", "In Progress",
			update_modified=False,
		)

	@frappe.whitelist()
	def complete_task(self):
		"""Complete the cleaning task and make bed available."""
		self._transition_to("Completed")
		self.completed_on = now_datetime()
		self.completed_by = frappe.session.user
		self._compute_turnaround()
		self.save()

		frappe.db.set_value(
			"Hospital Bed", self.hospital_bed,
			"housekeeping_status", "Clean",
			update_modified=False,
		)

		from alcura_ipd_ext.utils.bed_helpers import (
			recompute_capacity_for_bed,
			sync_hsu_occupancy_from_bed,
		)
		bed_doc = frappe.get_doc("Hospital Bed", self.hospital_bed)
		sync_hsu_occupancy_from_bed(bed_doc)
		recompute_capacity_for_bed(
			bed_doc.hospital_room, bed_doc.hospital_ward
		)

	@frappe.whitelist()
	def cancel_task(self):
		"""Cancel the cleaning task."""
		self._transition_to("Cancelled")
		self.save()

	# ── Private helpers ──────────────────────────────────────────────

	def _transition_to(self, new_status: str):
		allowed = VALID_TRANSITIONS.get(self.status, [])
		if new_status not in allowed:
			frappe.throw(
				_("Cannot transition from {0} to {1}.").format(
					frappe.bold(self.status), frappe.bold(new_status)
				),
				exc=frappe.ValidationError,
			)
		self.status = new_status

	def _validate_no_duplicate_active(self):
		if self.status in ("Completed", "Cancelled"):
			return
		if not self.hospital_bed:
			return
		existing = frappe.db.get_value(
			"Bed Housekeeping Task",
			{
				"hospital_bed": self.hospital_bed,
				"status": ("in", ("Pending", "In Progress")),
				"name": ("!=", self.name or ""),
			},
			"name",
		)
		if existing:
			frappe.throw(
				_("An active housekeeping task {0} already exists for bed {1}.").format(
					frappe.bold(existing), frappe.bold(self.hospital_bed)
				),
				exc=frappe.ValidationError,
			)

	def _compute_turnaround(self):
		if self.created_on and self.completed_on:
			diff = time_diff_in_seconds(self.completed_on, self.created_on)
			self.turnaround_minutes = max(0, int(diff / 60))
