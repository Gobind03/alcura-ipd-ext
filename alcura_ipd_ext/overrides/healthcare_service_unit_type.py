"""Server-side validation hook for Healthcare Service Unit Type.

Registered via ``doc_events`` in hooks.py. Adds IPD-specific business rules
on top of the standard Healthcare Service Unit Type form without modifying
the core doctype.
"""

import frappe
from frappe import _

CRITICAL_CARE_CATEGORIES = frozenset(
	{"ICU", "CICU", "MICU", "NICU", "PICU", "SICU", "HDU", "Burns"}
)


def validate(doc, method=None):
	"""Entry point called by Frappe's doc_events dispatcher."""
	if not doc.get("inpatient_occupancy"):
		return

	_require_room_category(doc)
	_set_critical_care_flag(doc)
	_auto_set_isolation_flag(doc)
	_suggest_nursing_intensity(doc)
	_warn_intensity_mismatch(doc)


def _require_room_category(doc):
	"""IPD Room Category is mandatory for inpatient service-unit types."""
	if not doc.get("ipd_room_category"):
		frappe.throw(
			_("IPD Room Category is required when Inpatient Occupancy is enabled."),
			exc=frappe.ValidationError,
		)


def _set_critical_care_flag(doc):
	"""Auto-set is_critical_care_unit based on ipd_room_category."""
	doc.is_critical_care_unit = 1 if doc.get("ipd_room_category") in CRITICAL_CARE_CATEGORIES else 0


def _auto_set_isolation_flag(doc):
	"""Auto-set supports_isolation = 1 when category is Isolation.

	Does not reset to 0 for other categories -- a room type may manually
	support isolation even if its primary category is not Isolation.
	"""
	if doc.get("ipd_room_category") == "Isolation":
		doc.supports_isolation = 1


def _suggest_nursing_intensity(doc):
	"""Default nursing_intensity to Critical for critical-care types when unset."""
	if doc.get("is_critical_care_unit") and not doc.get("nursing_intensity"):
		doc.nursing_intensity = "Critical"


def _warn_intensity_mismatch(doc):
	"""Warn (but do not block) if a critical-care type has Standard nursing intensity."""
	if (
		doc.get("is_critical_care_unit")
		and doc.get("nursing_intensity") == "Standard"
	):
		frappe.msgprint(
			_("Nursing Intensity is set to <b>Standard</b> for a critical-care room type ({0}). "
			  "Consider setting it to <b>High</b> or <b>Critical</b>.").format(
				doc.get("ipd_room_category")
			),
			indicator="orange",
			alert=True,
		)
