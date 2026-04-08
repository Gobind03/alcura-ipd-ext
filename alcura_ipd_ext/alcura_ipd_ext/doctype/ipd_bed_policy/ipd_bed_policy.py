"""Server controller for IPD Bed Policy (Single settings DocType)."""

from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document

# Fields that must not be negative
_NON_NEGATIVE_INT_FIELDS = (
	"cleaning_turnaround_sla_minutes",
	"reservation_timeout_minutes",
	"min_buffer_beds_per_ward",
)


class IPDBedPolicy(Document):
	def validate(self):
		self._validate_non_negative_integers()

	def _validate_non_negative_integers(self):
		for fieldname in _NON_NEGATIVE_INT_FIELDS:
			value = self.get(fieldname)
			if value is not None and int(value) < 0:
				label = self.meta.get_label(fieldname)
				frappe.throw(
					_("{0} must be zero or a positive number.").format(frappe.bold(label)),
					exc=frappe.ValidationError,
				)


def get_policy() -> dict:
	"""Return the current IPD Bed Policy as a dict with sensible defaults.

	Uses ``frappe.get_cached_doc`` for performance.  If the Single has
	never been saved the defaults from the DocType schema apply.
	"""
	try:
		doc = frappe.get_cached_doc("IPD Bed Policy")
		return {
			"exclude_dirty_beds": bool(doc.exclude_dirty_beds),
			"exclude_cleaning_beds": bool(doc.exclude_cleaning_beds),
			"exclude_maintenance_beds": bool(doc.exclude_maintenance_beds),
			"exclude_infection_blocked": bool(doc.exclude_infection_blocked),
			"gender_enforcement": doc.gender_enforcement or "Strict",
			"cleaning_turnaround_sla_minutes": int(doc.cleaning_turnaround_sla_minutes or 60),
			"auto_mark_dirty_on_discharge": bool(doc.auto_mark_dirty_on_discharge),
			"reservation_timeout_minutes": int(doc.reservation_timeout_minutes or 120),
			"enforce_payer_eligibility": doc.enforce_payer_eligibility or "Advisory",
			"enforce_eligibility_verification": doc.enforce_eligibility_verification or "Advisory",
			"min_buffer_beds_per_ward": int(doc.min_buffer_beds_per_ward or 0),
		}
	except frappe.DoesNotExistError:
		return _defaults()


def _defaults() -> dict:
	"""Fallback defaults when the Single doc has never been saved."""
	return {
		"exclude_dirty_beds": True,
		"exclude_cleaning_beds": True,
		"exclude_maintenance_beds": True,
		"exclude_infection_blocked": True,
		"gender_enforcement": "Strict",
		"cleaning_turnaround_sla_minutes": 60,
		"auto_mark_dirty_on_discharge": True,
		"reservation_timeout_minutes": 120,
		"enforce_payer_eligibility": "Advisory",
		"enforce_eligibility_verification": "Advisory",
		"min_buffer_beds_per_ward": 0,
	}
