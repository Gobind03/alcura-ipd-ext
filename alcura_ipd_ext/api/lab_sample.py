"""Whitelisted API endpoints for lab sample operations (US-G3)."""

from __future__ import annotations

import frappe
from frappe import _


@frappe.whitelist()
def create_sample(order_name: str) -> dict:
	"""Create an IPD Lab Sample from a clinical order."""
	frappe.has_permission("IPD Lab Sample", "create", throw=True)

	from alcura_ipd_ext.services.lab_sample_service import create_sample as _create

	return _create(order_name)


@frappe.whitelist()
def record_collection(
	sample_name: str,
	collection_site: str = "",
	notes: str = "",
) -> dict:
	"""Record sample collection by nurse/phlebotomist."""
	frappe.has_permission("IPD Lab Sample", "write", doc=sample_name, throw=True)

	from alcura_ipd_ext.services.lab_sample_service import record_collection as _collect

	return _collect(sample_name, collection_site=collection_site, notes=notes)


@frappe.whitelist()
def record_handoff(
	sample_name: str,
	transport_mode: str = "Manual",
) -> dict:
	"""Record sample handoff for transport."""
	frappe.has_permission("IPD Lab Sample", "write", doc=sample_name, throw=True)

	from alcura_ipd_ext.services.lab_sample_service import record_handoff as _handoff

	return _handoff(sample_name, transport_mode=transport_mode)


@frappe.whitelist()
def record_receipt(
	sample_name: str,
	sample_condition: str = "Acceptable",
) -> dict:
	"""Record sample receipt in lab."""
	frappe.has_permission("IPD Lab Sample", "write", doc=sample_name, throw=True)

	from alcura_ipd_ext.services.lab_sample_service import record_receipt as _receipt

	return _receipt(sample_name, sample_condition=sample_condition)


@frappe.whitelist()
def request_recollection(sample_name: str, reason: str) -> dict:
	"""Request recollection of a rejected sample."""
	frappe.has_permission("IPD Lab Sample", "write", doc=sample_name, throw=True)

	from alcura_ipd_ext.services.lab_sample_service import request_recollection as _recollect

	return _recollect(sample_name, reason)


@frappe.whitelist()
def acknowledge_critical_result(sample_name: str) -> dict:
	"""Acknowledge a critical lab result."""
	frappe.has_permission("IPD Lab Sample", "write", doc=sample_name, throw=True)

	from alcura_ipd_ext.services.lab_sample_service import acknowledge_critical_result as _ack

	return _ack(sample_name)


@frappe.whitelist()
def get_collection_queue(ward: str | None = None) -> list[dict]:
	"""Return pending samples for collection."""
	frappe.has_permission("IPD Lab Sample", "read", throw=True)

	from alcura_ipd_ext.services.lab_sample_service import get_collection_queue as _queue

	return _queue(ward)


@frappe.whitelist()
def get_sample_lifecycle(order_name: str) -> list[dict]:
	"""Return full sample lifecycle for a lab order."""
	frappe.has_permission("IPD Clinical Order", "read", doc=order_name, throw=True)

	from alcura_ipd_ext.services.lab_sample_service import get_sample_lifecycle as _lifecycle

	return _lifecycle(order_name)
