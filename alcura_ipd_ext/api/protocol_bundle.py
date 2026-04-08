"""Whitelisted API methods for monitoring protocol bundles (US-H4)."""

from __future__ import annotations

import frappe


@frappe.whitelist()
def activate(inpatient_record: str, protocol_bundle: str) -> dict:
	"""Activate a monitoring protocol bundle for an admission."""
	from alcura_ipd_ext.services.protocol_bundle_service import activate_bundle

	return activate_bundle(inpatient_record, protocol_bundle)


@frappe.whitelist()
def complete_step(
	active_bundle: str,
	step_name: str,
	linked_doc_type: str | None = None,
	linked_doc: str | None = None,
) -> dict:
	"""Mark a protocol step as completed."""
	from alcura_ipd_ext.services.protocol_bundle_service import (
		complete_step as _complete,
	)

	return _complete(active_bundle, step_name, linked_doc_type, linked_doc)


@frappe.whitelist()
def skip_step(active_bundle: str, step_name: str, reason: str) -> dict:
	"""Mark a protocol step as skipped."""
	from alcura_ipd_ext.services.protocol_bundle_service import skip_step as _skip

	return _skip(active_bundle, step_name, reason)


@frappe.whitelist()
def discontinue(active_bundle: str, reason: str) -> dict:
	"""Discontinue an active protocol bundle."""
	from alcura_ipd_ext.services.protocol_bundle_service import (
		discontinue_bundle,
	)

	return discontinue_bundle(active_bundle, reason)


@frappe.whitelist()
def get_bundles_for_ir(inpatient_record: str) -> list[dict]:
	"""Return all protocol bundles for an admission."""
	from alcura_ipd_ext.services.protocol_bundle_service import (
		get_active_bundles_for_ir,
	)

	return get_active_bundles_for_ir(inpatient_record)


@frappe.whitelist()
def get_compliance_report(
	ward: str | None = None,
	from_date: str | None = None,
	to_date: str | None = None,
) -> list[dict]:
	"""Return compliance summary across active bundles with optional filters."""
	filters = {}
	if from_date:
		filters["activated_at"] = (">=", from_date)
	if to_date:
		if "activated_at" in filters:
			filters["activated_at"] = ("between", [from_date, to_date])
		else:
			filters["activated_at"] = ("<=", to_date)

	bundles = frappe.get_all(
		"Active Protocol Bundle",
		filters=filters,
		fields=[
			"name", "protocol_bundle", "patient", "inpatient_record",
			"status", "compliance_score", "activated_at",
		],
	)

	if ward:
		ir_names = {b.inpatient_record for b in bundles}
		ward_map = {}
		for ir_name in ir_names:
			ward_map[ir_name] = frappe.db.get_value(
				"Inpatient Record", ir_name, "custom_current_ward"
			)
		bundles = [b for b in bundles if ward_map.get(b.inpatient_record) == ward]

	return bundles
