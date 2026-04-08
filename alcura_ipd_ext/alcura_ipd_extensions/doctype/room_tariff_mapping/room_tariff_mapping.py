"""Server controller for Room Tariff Mapping.

Handles validation of payer rules, date-range consistency, tariff-item
integrity, and overlap prevention across active mappings for the same
room-type / payer combination.
"""

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate


class RoomTariffMapping(Document):
	def validate(self):
		self._validate_room_type_inpatient()
		self._sanitise_payer()
		self._validate_date_range()
		self._validate_tariff_items()
		self._validate_no_duplicate_charge_types()
		self._validate_no_overlap()

	# ── room-type checks ────────────────────────────────────────────

	def _validate_room_type_inpatient(self):
		"""Room type must have Inpatient Occupancy enabled."""
		if not self.room_type:
			return
		inpatient = frappe.db.get_value(
			"Healthcare Service Unit Type",
			self.room_type,
			"inpatient_occupancy",
		)
		if not inpatient:
			frappe.throw(
				_(
					"Room Type {0} does not have Inpatient Occupancy enabled. "
					"Select a room type with Inpatient Occupancy."
				).format(frappe.bold(self.room_type)),
				exc=frappe.ValidationError,
			)

	# ── payer rules ─────────────────────────────────────────────────

	def _sanitise_payer(self):
		"""Clear payer when payer_type is Cash; require it otherwise."""
		if self.payer_type == "Cash":
			self.payer = None
		elif not self.payer:
			frappe.throw(
				_("Payer is required when Payer Type is {0}.").format(
					frappe.bold(self.payer_type)
				),
				exc=frappe.ValidationError,
			)

	# ── date-range checks ──────────────────────────────────────────

	def _validate_date_range(self):
		if self.valid_from and self.valid_to:
			if getdate(self.valid_to) < getdate(self.valid_from):
				frappe.throw(
					_("Valid To ({0}) must be on or after Valid From ({1}).").format(
						frappe.bold(self.valid_to),
						frappe.bold(self.valid_from),
					),
					exc=frappe.ValidationError,
				)

	# ── tariff-item integrity ──────────────────────────────────────

	def _validate_tariff_items(self):
		if not self.tariff_items:
			frappe.throw(
				_("At least one Tariff Item is required."),
				exc=frappe.ValidationError,
			)

	def _validate_no_duplicate_charge_types(self):
		if not self.tariff_items:
			return
		seen = set()
		for row in self.tariff_items:
			if row.charge_type in seen:
				frappe.throw(
					_("Duplicate Charge Type {0} in row {1}. Each charge type must appear only once.").format(
						frappe.bold(row.charge_type), row.idx
					),
					exc=frappe.ValidationError,
				)
			seen.add(row.charge_type)

	# ── overlap prevention ─────────────────────────────────────────

	def _validate_no_overlap(self):
		"""Prevent overlapping active tariff periods for the same
		(room_type, payer_type, payer, company) combination.

		Uses FOR UPDATE to guard against concurrent inserts.
		"""
		if not self.is_active:
			return

		filters = {
			"room_type": self.room_type,
			"payer_type": self.payer_type,
			"company": self.company,
			"is_active": 1,
			"name": ("!=", self.name or ""),
		}
		if self.payer:
			filters["payer"] = self.payer
		else:
			filters["payer"] = ("is", "not set")

		conflicts = frappe.db.get_all(
			"Room Tariff Mapping",
			filters=filters,
			fields=["name", "valid_from", "valid_to"],
			for_update=True,
		)

		for conflict in conflicts:
			if self._ranges_overlap(
				getdate(self.valid_from),
				getdate(self.valid_to) if self.valid_to else None,
				getdate(conflict.valid_from),
				getdate(conflict.valid_to) if conflict.valid_to else None,
			):
				frappe.throw(
					_(
						"Tariff period overlaps with {0} "
						"(Valid From: {1}, Valid To: {2}). "
						"Deactivate or adjust the existing mapping first."
					).format(
						frappe.bold(conflict.name),
						conflict.valid_from,
						conflict.valid_to or _("Open-ended"),
					),
					exc=frappe.ValidationError,
				)

	@staticmethod
	def _ranges_overlap(start_a, end_a, start_b, end_b):
		"""Check whether two date ranges overlap.

		A ``None`` end means the range extends indefinitely into the future.
		Two ranges [S_a, E_a] and [S_b, E_b] overlap when
		S_a <= E_b (or E_b is None) AND S_b <= E_a (or E_a is None).
		"""
		left_ok = end_b is None or start_a <= end_b
		right_ok = end_a is None or start_b <= end_a
		return left_ok and right_ok
