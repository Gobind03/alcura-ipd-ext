"""Whitelisted API endpoints for IPD admission and transfer workflows.

Usage from client:
	frappe.call("alcura_ipd_ext.api.admission.order_ipd_admission", {
		encounter: "ENC-00001", admission_priority: "Urgent",
		requested_ward: "WRD-01", expected_los_days: 5
	})
	frappe.call("alcura_ipd_ext.api.admission.allocate_bed", {
		inpatient_record: "IP-00001", hospital_bed: "WRD-R1-B1"
	})
	frappe.call("alcura_ipd_ext.api.admission.transfer_patient", {
		inpatient_record: "IP-00001", to_bed: "WRD-R2-B1", reason: "..."
	})
	frappe.call("alcura_ipd_ext.api.admission.get_available_beds_for_admission", {
		filters: {ward: "WRD-01"}
	})
	frappe.call("alcura_ipd_ext.api.admission.create_admission_checklist", {
		inpatient_record: "IP-00001"
	})
"""

from __future__ import annotations

import json

import frappe

from alcura_ipd_ext.services.bed_allocation_service import allocate_bed_on_admission
from alcura_ipd_ext.services.bed_availability_service import get_available_beds
from alcura_ipd_ext.services.bed_transfer_service import transfer_patient as _transfer
from alcura_ipd_ext.services.eligibility_service import check_admission_eligibility


# ── US-D1: Admission Order ───────────────────────────────────────────


@frappe.whitelist()
def order_ipd_admission(
	encounter: str,
	admission_priority: str = "Routine",
	requested_ward: str | None = None,
	expected_los_days: int | str | None = None,
	admission_notes: str | None = None,
) -> dict:
	"""Order IPD admission from a submitted Patient Encounter.

	Creates an Inpatient Record with custom admission order fields and
	links it back to the encounter.
	"""
	frappe.has_permission("Patient Encounter", "read", throw=True)
	frappe.has_permission("Inpatient Record", "create", throw=True)

	from alcura_ipd_ext.services.admission_order_service import (
		create_admission_from_encounter,
	)

	los = int(expected_los_days) if expected_los_days else None

	return create_admission_from_encounter(
		encounter,
		admission_priority=admission_priority or "Routine",
		requested_ward=requested_ward or None,
		expected_los_days=los,
		admission_notes=admission_notes or None,
	)


# ── US-D2: Admission Checklist ──────────────────────────────────────


@frappe.whitelist()
def create_admission_checklist(inpatient_record: str) -> dict:
	"""Create an Admission Checklist for an Inpatient Record from a template."""
	frappe.has_permission("Inpatient Record", "read", throw=True)
	frappe.has_permission("Admission Checklist", "create", throw=True)

	from alcura_ipd_ext.services.admission_checklist_service import (
		create_checklist_for_admission,
	)

	return create_checklist_for_admission(inpatient_record)


@frappe.whitelist()
def complete_checklist_item(checklist: str, row_idx: int | str) -> dict:
	"""Mark an Admission Checklist entry as Completed."""
	frappe.has_permission("Admission Checklist", "write", throw=True)

	from alcura_ipd_ext.services.admission_checklist_service import complete_item

	return complete_item(checklist, int(row_idx))


@frappe.whitelist()
def waive_checklist_item(
	checklist: str,
	row_idx: int | str,
	reason: str,
) -> dict:
	"""Waive a mandatory Admission Checklist entry (requires Healthcare Administrator)."""
	frappe.has_permission("Admission Checklist", "write", throw=True)

	from alcura_ipd_ext.services.admission_checklist_service import waive_item

	return waive_item(checklist, int(row_idx), reason)


@frappe.whitelist()
def get_checklist_for_admission(inpatient_record: str) -> dict | None:
	"""Return the Admission Checklist for an Inpatient Record, if one exists."""
	frappe.has_permission("Inpatient Record", "read", throw=True)

	name = frappe.db.get_value(
		"Admission Checklist", {"inpatient_record": inpatient_record}, "name"
	)
	if not name:
		return None

	doc = frappe.get_doc("Admission Checklist", name)
	return doc.as_dict()


# ── US-B3/B4: Bed Allocation & Transfer ─────────────────────────────


@frappe.whitelist()
def allocate_bed(
	inpatient_record: str,
	hospital_bed: str,
	reservation: str | None = None,
) -> dict:
	"""Allocate a bed during admission.

	Requires write permission on Inpatient Record and read on Hospital Bed.
	"""
	frappe.has_permission("Inpatient Record", "write", throw=True)
	frappe.has_permission("Hospital Bed", "read", throw=True)

	return allocate_bed_on_admission(
		inpatient_record=inpatient_record,
		hospital_bed=hospital_bed,
		reservation=reservation or None,
	)


@frappe.whitelist()
def transfer_patient(
	inpatient_record: str,
	to_bed: str,
	reason: str,
	ordered_by: str | None = None,
	source_bed_action: str | None = None,
) -> dict:
	"""Transfer a patient to a different bed.

	The source bed is derived from the Inpatient Record's current bed.
	Requires write permission on Inpatient Record and read on Hospital Bed.
	"""
	frappe.has_permission("Inpatient Record", "write", throw=True)
	frappe.has_permission("Hospital Bed", "read", throw=True)

	from_bed = frappe.db.get_value(
		"Inpatient Record", inpatient_record, "custom_current_bed",
	)
	if not from_bed:
		frappe.throw(
			frappe._("No current bed found for Inpatient Record {0}.").format(
				frappe.bold(inpatient_record)
			),
			exc=frappe.ValidationError,
		)

	return _transfer(
		inpatient_record=inpatient_record,
		from_bed=from_bed,
		to_bed=to_bed,
		reason=reason,
		ordered_by=ordered_by or None,
		source_bed_action=source_bed_action or None,
	)


@frappe.whitelist()
def get_available_beds_for_admission(
	filters: str | dict | None = None,
) -> list[dict]:
	"""Return available beds, suitable for the bed-picker dialog.

	Wraps ``bed_availability_service.get_available_beds()`` and ensures
	only vacant beds are returned (excludes occupied/reserved).
	"""
	frappe.has_permission("Hospital Bed", "read", throw=True)

	if isinstance(filters, str):
		filters = json.loads(filters)

	filters = filters or {}
	filters.setdefault("show_unavailable", False)

	return get_available_beds(filters)


@frappe.whitelist()
def check_eligibility_for_admission(inpatient_record: str) -> dict:
	"""Pre-flight eligibility check before bed allocation.

	Called by the client script to show warnings or block the allocation
	dialog based on the current IPD Bed Policy enforcement level.
	"""
	frappe.has_permission("Inpatient Record", "read", throw=True)
	return check_admission_eligibility(inpatient_record)


@frappe.whitelist()
def get_active_reservation_for_patient(
	patient: str,
	company: str | None = None,
) -> dict | None:
	"""Return the active Bed Reservation for a patient, if any.

	Used by the client script to auto-populate the reservation field
	in the allocation dialog.
	"""
	frappe.has_permission("Bed Reservation", "read", throw=True)

	filters = {"patient": patient, "status": "Active"}
	if company:
		filters["company"] = company

	reservation = frappe.db.get_value(
		"Bed Reservation",
		filters,
		["name", "hospital_bed", "reservation_type", "service_unit_type", "hospital_ward"],
		as_dict=True,
	)
	return reservation
