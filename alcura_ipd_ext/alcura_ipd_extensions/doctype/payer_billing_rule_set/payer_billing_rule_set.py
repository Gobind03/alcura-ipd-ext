"""Payer Billing Rule Set controller.

Validates rule consistency, date ranges, and payer-type-specific
mandatory fields.
"""

from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate


class PayerBillingRuleSet(Document):
	def validate(self):
		self._validate_date_range()
		self._validate_payer_fields()
		self._validate_rule_items()

	def _validate_date_range(self):
		if self.valid_from and self.valid_to:
			if getdate(self.valid_from) > getdate(self.valid_to):
				frappe.throw(
					_("Valid From ({0}) cannot be after Valid To ({1})").format(
						self.valid_from, self.valid_to
					),
					title=_("Invalid Date Range"),
				)

	def _validate_payer_fields(self):
		if self.payer_type in ("Corporate", "PSU") and not self.payer:
			frappe.throw(
				_("Payer (Customer) is required for {0} payer type").format(self.payer_type),
				title=_("Missing Payer"),
			)
		if self.payer_type == "Insurance TPA" and not self.insurance_payor:
			frappe.throw(
				_("Insurance Payor is required for Insurance TPA payer type"),
				title=_("Missing Insurance Payor"),
			)

	def _validate_rule_items(self):
		for row in self.rules or []:
			if row.applies_to == "Item" and not row.item_code:
				frappe.throw(
					_("Row {0}: Item is required when Applies To is 'Item'").format(row.idx),
					title=_("Missing Item"),
				)
			if row.applies_to == "Item Group" and not row.item_group:
				frappe.throw(
					_("Row {0}: Item Group is required when Applies To is 'Item Group'").format(row.idx),
					title=_("Missing Item Group"),
				)
			if row.applies_to == "Charge Category" and not row.charge_category:
				frappe.throw(
					_("Row {0}: Charge Category is required when Applies To is 'Charge Category'").format(row.idx),
					title=_("Missing Charge Category"),
				)
			if row.rule_type == "Co-Pay Override" and not row.co_pay_percent:
				frappe.throw(
					_("Row {0}: Co-Pay % is required for Co-Pay Override rules").format(row.idx),
					title=_("Missing Co-Pay %"),
				)
			if row.rule_type == "Sub-Limit" and not row.sub_limit_amount:
				frappe.throw(
					_("Row {0}: Sub-Limit Amount is required for Sub-Limit rules").format(row.idx),
					title=_("Missing Sub-Limit Amount"),
				)
			if row.rule_type == "Room Rent Cap" and not row.cap_amount:
				frappe.throw(
					_("Row {0}: Cap Amount is required for Room Rent Cap rules").format(row.idx),
					title=_("Missing Cap Amount"),
				)
