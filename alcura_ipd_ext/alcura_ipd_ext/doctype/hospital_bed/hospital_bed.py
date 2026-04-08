"""Server controller for Hospital Bed master."""

import re

import frappe
from frappe import _
from frappe.model.document import Document

BED_NUMBER_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9\-]*$")


class HospitalBed(Document):
	def autoname(self):
		self.name = f"{self.hospital_room}-{self.bed_number.strip().upper()}"

	def validate(self):
		self._validate_bed_number_format()
		self._validate_bed_number_unique()
		self._validate_room_active()
		self._prevent_disable_when_occupied()
		self._inherit_ward_and_company()

	def before_save(self):
		self.bed_number = self.bed_number.strip().upper()

	def after_insert(self):
		self._auto_create_hsu_leaf()
		self._trigger_capacity_rollup()

	def on_update(self):
		self._sync_hsu_occupancy()
		self._trigger_capacity_rollup()

	def on_trash(self):
		self._prevent_delete_when_occupied()
		self._prevent_delete_with_inpatient_history()
		self._trigger_capacity_rollup()

	# ── private helpers ──────────────────────────────────────────────

	def _validate_bed_number_format(self):
		if not self.bed_number:
			return
		code = self.bed_number.strip()
		if not BED_NUMBER_PATTERN.match(code):
			frappe.throw(
				_(
					"Bed Number must contain only letters, digits, and hyphens, "
					"and must start with a letter or digit."
				),
				exc=frappe.ValidationError,
			)

	def _validate_bed_number_unique(self):
		if not self.bed_number or not self.hospital_room:
			return

		filters = {
			"bed_number": self.bed_number.strip().upper(),
			"hospital_room": self.hospital_room,
			"name": ("!=", self.name or ""),
		}
		duplicate = frappe.db.get_value("Hospital Bed", filters, "name", for_update=True)
		if duplicate:
			frappe.throw(
				_(
					"Bed Number {0} already exists in room {1} (see {2})."
				).format(
					frappe.bold(self.bed_number),
					frappe.bold(self.hospital_room),
					duplicate,
				),
				exc=frappe.ValidationError,
			)

	def _validate_room_active(self):
		if not self.hospital_room:
			return
		is_active = frappe.db.get_value("Hospital Room", self.hospital_room, "is_active")
		if not is_active:
			frappe.throw(
				_("Hospital Room {0} is inactive. Cannot add beds to an inactive room.").format(
					frappe.bold(self.hospital_room)
				),
				exc=frappe.ValidationError,
			)

	def _prevent_disable_when_occupied(self):
		if not self.is_active and self.occupancy_status in ("Occupied", "Reserved"):
			frappe.throw(
				_("Cannot deactivate bed {0} while it is {1}.").format(
					frappe.bold(self.name),
					self.occupancy_status,
				),
				exc=frappe.ValidationError,
			)

	def _inherit_ward_and_company(self):
		"""Fetch hospital_ward, company, service_unit_type from the room."""
		if self.hospital_room:
			room_data = frappe.db.get_value(
				"Hospital Room",
				self.hospital_room,
				["hospital_ward", "company", "service_unit_type"],
				as_dict=True,
			)
			if room_data:
				self.hospital_ward = room_data.hospital_ward
				self.company = room_data.company
				self.service_unit_type = room_data.service_unit_type

	def _auto_create_hsu_leaf(self):
		"""Create an HSU leaf node under the room's HSU, if the room has one."""
		if self.healthcare_service_unit:
			return

		room_hsu = frappe.db.get_value(
			"Hospital Room", self.hospital_room, "healthcare_service_unit"
		)
		if not room_hsu:
			return

		from alcura_ipd_ext.utils.bed_helpers import create_hsu_leaf_for_bed

		hsu_name = create_hsu_leaf_for_bed(
			bed_number=self.bed_number,
			room_hsu=room_hsu,
			service_unit_type=self.service_unit_type,
			company=self.company,
		)
		frappe.db.set_value("Hospital Bed", self.name, "healthcare_service_unit", hsu_name)
		self.healthcare_service_unit = hsu_name

	def _sync_hsu_occupancy(self):
		from alcura_ipd_ext.utils.bed_helpers import sync_hsu_occupancy_from_bed

		sync_hsu_occupancy_from_bed(self)

	def _trigger_capacity_rollup(self):
		from alcura_ipd_ext.utils.bed_helpers import recompute_capacity_for_bed

		recompute_capacity_for_bed(self.hospital_room, self.hospital_ward)

	def _prevent_delete_when_occupied(self):
		if self.occupancy_status in ("Occupied", "Reserved"):
			frappe.throw(
				_("Cannot delete bed {0} while it is {1}.").format(
					frappe.bold(self.name),
					self.occupancy_status,
				),
				exc=frappe.ValidationError,
			)

	def _prevent_delete_with_inpatient_history(self):
		"""Block deletion if this bed's HSU has been used in any Inpatient Occupancy."""
		if not self.healthcare_service_unit:
			return

		used = frappe.db.exists(
			"Inpatient Occupancy",
			{"service_unit": self.healthcare_service_unit},
		)
		if used:
			frappe.throw(
				_(
					"Cannot delete bed {0}: it has inpatient admission history. "
					"Deactivate the bed instead."
				).format(frappe.bold(self.name)),
				exc=frappe.LinkExistsError,
			)
