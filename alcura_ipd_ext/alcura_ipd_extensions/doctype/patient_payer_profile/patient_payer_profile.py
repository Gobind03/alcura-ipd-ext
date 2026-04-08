"""Patient Payer Profile controller.

Manages the lifecycle of payer profiles attached to a Patient. Handles
validation of payer-type-specific mandatory fields, date ranges, and
cross-references to Marley Health insurance doctypes.
"""

from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate, today

from alcura_ipd_ext.utils.constants import (
	PAYER_TYPES_REQUIRING_CUSTOMER,
	PAYER_TYPES_REQUIRING_INSURANCE_PAYOR,
)


class PatientPayerProfile(Document):
	def validate(self):
		self._validate_date_range()
		self._validate_payer_fields_by_type()
		self._validate_insurance_policy_ownership()
		self._warn_expired_profile()
		self._check_duplicate_active_profile()
		self._add_patient_comment_on_change()

	def _validate_date_range(self):
		if self.valid_from and self.valid_to:
			if getdate(self.valid_from) > getdate(self.valid_to):
				frappe.throw(
					_("Valid From ({0}) cannot be after Valid To ({1})").format(
						self.valid_from, self.valid_to
					),
					title=_("Invalid Date Range"),
				)

	def _validate_payer_fields_by_type(self):
		if self.payer_type in PAYER_TYPES_REQUIRING_CUSTOMER and not self.payer:
			frappe.throw(
				_("Payer (Customer) is required for {0} payer type").format(self.payer_type),
				title=_("Missing Payer"),
			)

		if self.payer_type in PAYER_TYPES_REQUIRING_INSURANCE_PAYOR and not self.insurance_payor:
			frappe.throw(
				_("Insurance Payor is required for {0} payer type").format(self.payer_type),
				title=_("Missing Insurance Payor"),
			)

	def _validate_insurance_policy_ownership(self):
		"""If an insurance policy is linked, verify it belongs to the same patient
		and the same insurance payor."""
		if not self.insurance_policy:
			return

		policy = frappe.db.get_value(
			"Patient Insurance Policy",
			self.insurance_policy,
			["patient", "insurance_payor"],
			as_dict=True,
		)
		if not policy:
			frappe.throw(
				_("Insurance Policy {0} not found").format(self.insurance_policy),
				title=_("Invalid Insurance Policy"),
			)

		if policy.patient != self.patient:
			frappe.throw(
				_("Insurance Policy {0} belongs to Patient {1}, not {2}").format(
					self.insurance_policy, policy.patient, self.patient
				),
				title=_("Patient Mismatch"),
			)

		if self.insurance_payor and policy.insurance_payor != self.insurance_payor:
			frappe.throw(
				_("Insurance Policy {0} is with payor {1}, not {2}").format(
					self.insurance_policy, policy.insurance_payor, self.insurance_payor
				),
				title=_("Payor Mismatch"),
			)

	def _warn_expired_profile(self):
		"""Warn (not block) when saving an active profile whose validity has passed."""
		if not self.is_active or not self.valid_to:
			return

		if getdate(self.valid_to) < getdate(today()):
			frappe.msgprint(
				_("This payer profile expired on {0}. Consider deactivating it.").format(
					self.valid_to
				),
				title=_("Expired Profile"),
				indicator="orange",
			)

	def _check_duplicate_active_profile(self):
		"""Warn if there is already an active profile for the same patient, payer_type,
		and payer/insurance_payor combination."""
		if not self.is_active:
			return

		filters = {
			"patient": self.patient,
			"payer_type": self.payer_type,
			"is_active": 1,
			"name": ("!=", self.name),
		}

		if self.payer_type in PAYER_TYPES_REQUIRING_CUSTOMER and self.payer:
			filters["payer"] = self.payer
		elif self.payer_type in PAYER_TYPES_REQUIRING_INSURANCE_PAYOR and self.insurance_payor:
			filters["insurance_payor"] = self.insurance_payor

		existing = frappe.db.get_value("Patient Payer Profile", filters, "name")
		if existing:
			frappe.msgprint(
				_("An active {0} profile ({1}) already exists for this patient. "
				  "Please verify if this is intentional.").format(self.payer_type, existing),
				title=_("Duplicate Active Profile"),
				indicator="orange",
			)

	def _add_patient_comment_on_change(self):
		"""Add a timeline comment on the linked Patient when a profile is
		created or significantly modified."""
		if self.is_new():
			action = _("created")
		elif self.has_value_changed("is_active"):
			action = _("activated") if self.is_active else _("deactivated")
		elif self.has_value_changed("payer_type") or self.has_value_changed("valid_to"):
			action = _("updated")
		else:
			return

		comment_text = _("Payer profile {0} ({1}) {2}").format(
			self.name or _("new"), self.payer_type, action
		)

		if not self.is_new():
			frappe.get_doc("Patient", self.patient).add_comment(
				"Info", comment_text
			)
