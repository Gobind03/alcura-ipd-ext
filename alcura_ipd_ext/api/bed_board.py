"""Whitelisted API endpoints for the Live Bed Board.

Usage from client:
	frappe.call("alcura_ipd_ext.api.bed_board.get_bed_board", filters={...})
	frappe.call("alcura_ipd_ext.api.bed_board.get_bed_board_summary", filters={...})
"""

from __future__ import annotations

import json

import frappe

from alcura_ipd_ext.services.bed_availability_service import (
	get_available_beds,
)
from alcura_ipd_ext.services.bed_availability_service import (
	get_bed_board_summary as _get_summary,
)


@frappe.whitelist()
def get_bed_board(filters: str | dict | None = None) -> list[dict]:
	"""Return available beds matching the given filters.

	Requires read permission on Hospital Bed.
	"""
	frappe.has_permission("Hospital Bed", "read", throw=True)

	if isinstance(filters, str):
		filters = json.loads(filters)

	return get_available_beds(filters)


@frappe.whitelist()
def get_bed_board_summary(filters: str | dict | None = None) -> dict:
	"""Return aggregate bed counts (total, available, occupied, blocked).

	Requires read permission on Hospital Bed.
	"""
	frappe.has_permission("Hospital Bed", "read", throw=True)

	if isinstance(filters, str):
		filters = json.loads(filters)

	return _get_summary(filters)
