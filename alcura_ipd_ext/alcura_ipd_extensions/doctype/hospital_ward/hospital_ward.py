"""Server controller for Hospital Ward master."""

import re

import frappe
from frappe import _
from frappe.model.document import Document

CRITICAL_CARE_CLASSIFICATIONS = frozenset(
	{"ICU", "CICU", "MICU", "NICU", "PICU", "SICU", "HDU", "Burns"}
)

WARD_CODE_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9\-]*$")


class HospitalWard(Document):
	def autoname(self):
		abbr = frappe.get_cached_value("Company", self.company, "abbr")
		if not abbr:
			frappe.throw(
				_("Company {0} does not have an abbreviation set.").format(self.company)
			)
		self.name = f"{abbr}-{self.ward_code.upper()}"

	def validate(self):
		self._validate_ward_code_format()
		self._validate_ward_code_unique()
		self._set_critical_care_flag()
		self._validate_healthcare_service_unit()
		self._compute_available_beds()

	def before_save(self):
		self.ward_code = self.ward_code.strip().upper()

	def on_trash(self):
		self._prevent_delete_with_linked_records()

	# ── private helpers ──────────────────────────────────────────────

	def _validate_ward_code_format(self):
		if not self.ward_code:
			return
		code = self.ward_code.strip()
		if not WARD_CODE_PATTERN.match(code):
			frappe.throw(
				_("Ward Code must contain only letters, digits, and hyphens, and must start with a letter or digit."),
				exc=frappe.ValidationError,
			)

	def _validate_ward_code_unique(self):
		"""Ensure ward_code is unique per company. Uses select-for-update to guard against races."""
		if not self.ward_code or not self.company:
			return

		filters = {
			"ward_code": self.ward_code.strip().upper(),
			"company": self.company,
			"name": ("!=", self.name or ""),
		}
		duplicate = frappe.db.get_value(
			"Hospital Ward",
			filters,
			"name",
			for_update=True,
		)
		if duplicate:
			frappe.throw(
				_("Ward Code {0} already exists for company {1} (see {2}).").format(
					frappe.bold(self.ward_code), frappe.bold(self.company), duplicate
				),
				exc=frappe.ValidationError,
			)

	def _set_critical_care_flag(self):
		self.is_critical_care = 1 if self.ward_classification in CRITICAL_CARE_CLASSIFICATIONS else 0

	def _validate_healthcare_service_unit(self):
		if not self.healthcare_service_unit:
			return
		is_group = frappe.db.get_value(
			"Healthcare Service Unit", self.healthcare_service_unit, "is_group"
		)
		if not is_group:
			frappe.throw(
				_("Healthcare Service Unit {0} must be a group node (is_group=1) to represent a ward.").format(
					frappe.bold(self.healthcare_service_unit)
				),
				exc=frappe.ValidationError,
			)

	def _compute_available_beds(self):
		self.available_beds = (self.total_beds or 0) - (self.occupied_beds or 0)

	def _prevent_delete_with_linked_records(self):
		"""Prevent deletion when rooms are linked to this ward."""
		room_count = frappe.db.count("Hospital Room", {"hospital_ward": self.name})
		if room_count:
			frappe.throw(
				_("Cannot delete ward {0}: {1} room(s) are linked. Deactivate the ward instead.").format(
					frappe.bold(self.name), room_count
				),
				exc=frappe.LinkExistsError,
			)
