"""Whitelisted API endpoints for pharmacy dispense operations (US-G1)."""

from __future__ import annotations

import frappe
from frappe import _


@frappe.whitelist()
def verify_stock(item_code: str, warehouse: str | None = None) -> dict:
	"""Check available stock for a medication item."""
	frappe.has_permission("IPD Clinical Order", "read", throw=True)

	from alcura_ipd_ext.services.pharmacy_dispense_service import verify_stock as _verify

	return _verify(item_code, warehouse)


@frappe.whitelist()
def dispense_medication(
	order_name: str,
	dispensed_qty: float,
	dispense_type: str = "Full",
	batch_no: str | None = None,
	warehouse: str | None = None,
	expiry_date: str | None = None,
	is_substitution: int = 0,
	substitute_item: str | None = None,
	substitution_reason: str | None = None,
	substitution_approved_by: str | None = None,
	notes: str | None = None,
) -> dict:
	"""Create a dispense entry for a medication order."""
	frappe.has_permission("IPD Dispense Entry", "create", throw=True)

	from alcura_ipd_ext.services.pharmacy_dispense_service import dispense_medication as _dispense

	return _dispense(
		order_name=order_name,
		dispensed_qty=float(dispensed_qty),
		dispense_type=dispense_type,
		batch_no=batch_no,
		warehouse=warehouse,
		expiry_date=expiry_date,
		is_substitution=bool(int(is_substitution)),
		substitute_item=substitute_item,
		substitution_reason=substitution_reason,
		substitution_approved_by=substitution_approved_by,
		notes=notes,
	)


@frappe.whitelist()
def request_substitution(order_name: str, substitute_item: str, reason: str) -> dict:
	"""Request substitution of the prescribed medication."""
	frappe.has_permission("IPD Clinical Order", "write", doc=order_name, throw=True)

	from alcura_ipd_ext.services.pharmacy_dispense_service import request_substitution as _req

	return _req(order_name, substitute_item, reason)


@frappe.whitelist()
def approve_substitution(order_name: str) -> dict:
	"""Approve a pending substitution request."""
	frappe.has_permission("IPD Clinical Order", "write", doc=order_name, throw=True)

	from alcura_ipd_ext.services.pharmacy_dispense_service import approve_substitution as _approve

	return _approve(order_name)


@frappe.whitelist()
def reject_substitution(order_name: str, reason: str) -> dict:
	"""Reject a pending substitution request."""
	frappe.has_permission("IPD Clinical Order", "write", doc=order_name, throw=True)

	from alcura_ipd_ext.services.pharmacy_dispense_service import reject_substitution as _reject

	return _reject(order_name, reason)


@frappe.whitelist()
def return_dispense(dispense_entry: str, reason: str) -> dict:
	"""Mark a dispense entry as returned."""
	frappe.has_permission("IPD Dispense Entry", "write", doc=dispense_entry, throw=True)

	from alcura_ipd_ext.services.pharmacy_dispense_service import return_dispense as _return

	return _return(dispense_entry, reason)


@frappe.whitelist()
def get_dispense_history(order_name: str) -> list[dict]:
	"""Get all dispense entries for an order."""
	frappe.has_permission("IPD Clinical Order", "read", doc=order_name, throw=True)

	from alcura_ipd_ext.services.pharmacy_dispense_service import get_dispense_history as _history

	return _history(order_name)
