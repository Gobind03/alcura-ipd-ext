"""Document event hooks for the standard Patient doctype.

Registered in hooks.py under doc_events -> Patient -> validate.
"""

from __future__ import annotations

import frappe
from frappe.utils import now_datetime


def validate(doc, method=None):
	"""Server-side validate hook for Patient."""
	_validate_indian_ids(doc)
	_validate_emergency_contact_phone(doc)
	_handle_consent_timestamp(doc)
	_validate_mr_number_unique(doc)


def _validate_indian_ids(doc):
	"""Run format/checksum validation on Indian statutory IDs."""
	from alcura_ipd_ext.utils.indian_id_validators import (
		validate_aadhaar,
		validate_abha_address,
		validate_abha_number,
		validate_pan,
	)

	validators = [
		("custom_aadhaar_number", validate_aadhaar, "Aadhaar Number"),
		("custom_pan_number", validate_pan, "PAN Number"),
		("custom_abha_number", validate_abha_number, "ABHA Number"),
		("custom_abha_address", validate_abha_address, "ABHA Address"),
	]

	for fieldname, validator_fn, label in validators:
		value = doc.get(fieldname)
		if not value:
			continue
		is_valid, error_msg = validator_fn(value)
		if not is_valid:
			frappe.throw(
				frappe._("{0}: {1}").format(label, error_msg),
				title=frappe._("Invalid {0}").format(label),
			)

	_normalise_pan(doc)


def _normalise_pan(doc):
	"""Store PAN in uppercase."""
	pan = doc.get("custom_pan_number")
	if pan:
		doc.custom_pan_number = pan.strip().upper()


def _validate_emergency_contact_phone(doc):
	"""Validate emergency contact phone if provided."""
	phone = doc.get("custom_emergency_contact_phone")
	if not phone:
		return

	from alcura_ipd_ext.utils.indian_id_validators import validate_indian_mobile

	is_valid, error_msg = validate_indian_mobile(phone)
	if not is_valid:
		frappe.throw(
			frappe._("Emergency Contact Phone: {0}").format(error_msg),
			title=frappe._("Invalid Phone Number"),
		)


def _handle_consent_timestamp(doc):
	"""Auto-set consent datetime when consent is collected, clear when unchecked."""
	if doc.get("custom_consent_collected"):
		if not doc.get("custom_consent_datetime"):
			doc.custom_consent_datetime = now_datetime()
	else:
		doc.custom_consent_datetime = None


def _validate_mr_number_unique(doc):
	"""Ensure MR number is unique across all patients (if provided).

	The custom field has unique=1, but we add an explicit check with
	a user-friendly error message rather than relying on the DB constraint.
	"""
	mr = doc.get("custom_mr_number")
	if not mr:
		return

	existing = frappe.db.get_value(
		"Patient",
		{"custom_mr_number": mr.strip(), "name": ("!=", doc.name)},
		"name",
	)
	if existing:
		frappe.throw(
			frappe._("MR Number {0} is already assigned to Patient {1}").format(mr, existing),
			title=frappe._("Duplicate MR Number"),
		)
