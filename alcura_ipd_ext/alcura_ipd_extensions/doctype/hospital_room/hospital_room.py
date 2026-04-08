"""Server controller for Hospital Room master."""

import re

import frappe
from frappe import _
from frappe.model.document import Document

ROOM_NUMBER_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9\-]*$")


class HospitalRoom(Document):
	def autoname(self):
		ward_name = self.hospital_ward
		self.name = f"{ward_name}-{self.room_number.strip().upper()}"

	def validate(self):
		self._validate_room_number_format()
		self._validate_room_number_unique()
		self._validate_ward_active()
		self._validate_service_unit_type()
		self._compute_available_beds()

	def before_save(self):
		self.room_number = self.room_number.strip().upper()

	def after_insert(self):
		self._auto_create_hsu_group()

	def on_trash(self):
		self._prevent_delete_with_beds()

	# ── private helpers ──────────────────────────────────────────────

	def _validate_room_number_format(self):
		if not self.room_number:
			return
		code = self.room_number.strip()
		if not ROOM_NUMBER_PATTERN.match(code):
			frappe.throw(
				_(
					"Room Number must contain only letters, digits, and hyphens, "
					"and must start with a letter or digit."
				),
				exc=frappe.ValidationError,
			)

	def _validate_room_number_unique(self):
		if not self.room_number or not self.hospital_ward:
			return

		filters = {
			"room_number": self.room_number.strip().upper(),
			"hospital_ward": self.hospital_ward,
			"name": ("!=", self.name or ""),
		}
		duplicate = frappe.db.get_value("Hospital Room", filters, "name", for_update=True)
		if duplicate:
			frappe.throw(
				_(
					"Room Number {0} already exists in ward {1} (see {2})."
				).format(
					frappe.bold(self.room_number),
					frappe.bold(self.hospital_ward),
					duplicate,
				),
				exc=frappe.ValidationError,
			)

	def _validate_ward_active(self):
		if not self.hospital_ward:
			return
		is_active = frappe.db.get_value("Hospital Ward", self.hospital_ward, "is_active")
		if not is_active:
			frappe.throw(
				_("Hospital Ward {0} is inactive. Cannot add rooms to an inactive ward.").format(
					frappe.bold(self.hospital_ward)
				),
				exc=frappe.ValidationError,
			)

	def _validate_service_unit_type(self):
		if not self.service_unit_type:
			return
		inpatient_occupancy = frappe.db.get_value(
			"Healthcare Service Unit Type", self.service_unit_type, "inpatient_occupancy"
		)
		if not inpatient_occupancy:
			frappe.throw(
				_(
					"Room Type {0} does not have Inpatient Occupancy enabled. "
					"Select a type with Inpatient Occupancy."
				).format(frappe.bold(self.service_unit_type)),
				exc=frappe.ValidationError,
			)

	def _compute_available_beds(self):
		self.available_beds = (self.total_beds or 0) - (self.occupied_beds or 0)

	def _auto_create_hsu_group(self):
		"""Create an HSU group node under the ward's HSU, if the ward has one."""
		if self.healthcare_service_unit:
			return

		ward_hsu = frappe.db.get_value(
			"Hospital Ward", self.hospital_ward, "healthcare_service_unit"
		)
		if not ward_hsu:
			return

		from alcura_ipd_ext.utils.bed_helpers import create_hsu_group_for_room

		hsu_name = create_hsu_group_for_room(
			room_name=self.name,
			room_number=self.room_number,
			ward_hsu=ward_hsu,
			service_unit_type=self.service_unit_type,
			company=self.company,
		)
		frappe.db.set_value("Hospital Room", self.name, "healthcare_service_unit", hsu_name)
		self.healthcare_service_unit = hsu_name

	def _prevent_delete_with_beds(self):
		bed_count = frappe.db.count("Hospital Bed", {"hospital_room": self.name})
		if bed_count:
			frappe.throw(
				_(
					"Cannot delete room {0}: {1} bed(s) are linked. "
					"Deactivate the room instead."
				).format(frappe.bold(self.name), bed_count),
				exc=frappe.LinkExistsError,
			)
