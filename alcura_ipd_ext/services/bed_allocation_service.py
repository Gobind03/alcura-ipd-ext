"""Bed allocation service for IPD admission.

Handles transaction-safe bed allocation during patient admission, including:
- Row-level locking on Hospital Bed to prevent double-allocation
- Inpatient Record status transition (Admission Scheduled → Admitted)
- Inpatient Occupancy child row creation (bridging to standard HSU flow)
- Bed Reservation consumption (when applicable)
- Bed Movement Log audit trail
- Capacity rollup propagation

All race-sensitive operations use ``SELECT … FOR UPDATE`` row locks.
"""

from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import now_datetime

from alcura_ipd_ext.utils.bed_helpers import (
	recompute_capacity_for_bed,
	sync_hsu_occupancy_from_bed,
)


def allocate_bed_on_admission(
	inpatient_record: str,
	hospital_bed: str,
	reservation: str | None = None,
) -> dict:
	"""Allocate a bed to a patient during admission.

	This is the primary entry point for US-B3. It performs the full
	allocation atomically within a single database transaction.

	Args:
		inpatient_record: Name of the Inpatient Record (status must be
			"Admission Scheduled").
		hospital_bed: Name of the Hospital Bed to allocate.
		reservation: Optional Bed Reservation name to consume.

	Returns:
		Dict with keys ``inpatient_record``, ``hospital_bed``,
		``bed_movement_log``, and ``status``.

	Raises:
		frappe.ValidationError: If any validation fails.
	"""
	ir_doc = frappe.get_doc("Inpatient Record", inpatient_record)
	_validate_ir_for_admission(ir_doc)
	_validate_eligibility(ir_doc)

	bed_data = _lock_and_validate_bed(hospital_bed, ir_doc, reservation)

	_mark_bed_occupied(hospital_bed)

	_sync_hsu(hospital_bed)

	_add_inpatient_occupancy(ir_doc, bed_data)

	_update_ir_status(ir_doc, bed_data)

	bml_name = _create_movement_log(ir_doc, bed_data, reservation)

	if reservation:
		_consume_reservation(reservation, inpatient_record)

	recompute_capacity_for_bed(bed_data.hospital_room, bed_data.hospital_ward)

	_add_timeline_comments(ir_doc, bed_data)

	_apply_monitoring_profile(inpatient_record, bed_data.hospital_ward)

	return {
		"inpatient_record": inpatient_record,
		"hospital_bed": hospital_bed,
		"bed_movement_log": bml_name,
		"status": "Admitted",
	}


# ── Validation ───────────────────────────────────────────────────────


def _validate_ir_for_admission(ir_doc) -> None:
	if ir_doc.status != "Admission Scheduled":
		frappe.throw(
			_("Inpatient Record {0} has status {1}. Expected 'Admission Scheduled'.").format(
				frappe.bold(ir_doc.name), frappe.bold(ir_doc.status)
			),
			exc=frappe.ValidationError,
		)


def _validate_eligibility(ir_doc) -> None:
	"""Check payer eligibility according to IPD Bed Policy.

	Strict enforcement blocks the allocation; Advisory is a no-op at the
	server level (the client shows the warning before calling allocate).
	"""
	from alcura_ipd_ext.services.eligibility_service import check_admission_eligibility

	result = check_admission_eligibility(ir_doc.name)
	if not result["eligible"] and result["enforcement"] == "Strict":
		frappe.throw(
			result["message"],
			title=_("Eligibility Verification Required"),
			exc=frappe.ValidationError,
		)


def _lock_and_validate_bed(
	hospital_bed: str,
	ir_doc,
	reservation: str | None,
) -> frappe._dict:
	"""Acquire row lock on Hospital Bed and validate availability."""
	bed_data = frappe.db.get_value(
		"Hospital Bed",
		hospital_bed,
		[
			"name",
			"occupancy_status",
			"hospital_room",
			"hospital_ward",
			"company",
			"service_unit_type",
			"healthcare_service_unit",
			"is_active",
			"maintenance_hold",
			"infection_block",
		],
		as_dict=True,
		for_update=True,
	)

	if not bed_data:
		frappe.throw(
			_("Hospital Bed {0} does not exist.").format(frappe.bold(hospital_bed)),
			exc=frappe.ValidationError,
		)

	if not bed_data.is_active:
		frappe.throw(
			_("Hospital Bed {0} is inactive and cannot be allocated.").format(
				frappe.bold(hospital_bed)
			),
			exc=frappe.ValidationError,
		)

	if bed_data.maintenance_hold:
		frappe.throw(
			_("Hospital Bed {0} is under maintenance hold.").format(
				frappe.bold(hospital_bed)
			),
			exc=frappe.ValidationError,
		)

	if bed_data.infection_block:
		frappe.throw(
			_("Hospital Bed {0} is under infection block.").format(
				frappe.bold(hospital_bed)
			),
			exc=frappe.ValidationError,
		)

	allowed_statuses = ["Vacant"]
	if reservation:
		allowed_statuses.append("Reserved")

	if bed_data.occupancy_status not in allowed_statuses:
		frappe.throw(
			_("Hospital Bed {0} is currently {1} and cannot be allocated.").format(
				frappe.bold(hospital_bed),
				frappe.bold(bed_data.occupancy_status),
			),
			exc=frappe.ValidationError,
		)

	if bed_data.occupancy_status == "Reserved" and reservation:
		res_bed = frappe.db.get_value(
			"Bed Reservation", reservation, "hospital_bed"
		)
		if res_bed != hospital_bed:
			frappe.throw(
				_("Reservation {0} is not for bed {1}.").format(
					frappe.bold(reservation), frappe.bold(hospital_bed)
				),
				exc=frappe.ValidationError,
			)

	ir_company = ir_doc.company
	if bed_data.company and ir_company and bed_data.company != ir_company:
		frappe.throw(
			_("Bed company ({0}) does not match Inpatient Record company ({1}).").format(
				frappe.bold(bed_data.company), frappe.bold(ir_company)
			),
			exc=frappe.ValidationError,
		)

	if not bed_data.healthcare_service_unit:
		frappe.throw(
			_("Hospital Bed {0} has no linked Healthcare Service Unit. "
			  "Please configure the bed's HSU linkage first.").format(
				frappe.bold(hospital_bed)
			),
			exc=frappe.ValidationError,
		)

	return bed_data


# ── State mutations ──────────────────────────────────────────────────


def _mark_bed_occupied(hospital_bed: str) -> None:
	frappe.db.set_value(
		"Hospital Bed",
		hospital_bed,
		"occupancy_status",
		"Occupied",
		update_modified=False,
	)


def _sync_hsu(hospital_bed: str) -> None:
	bed_doc = frappe.get_doc("Hospital Bed", hospital_bed)
	sync_hsu_occupancy_from_bed(bed_doc)


def _add_inpatient_occupancy(ir_doc, bed_data: frappe._dict) -> None:
	"""Append an Inpatient Occupancy child row to the IR."""
	ir_doc.append("inpatient_occupancies", {
		"service_unit": bed_data.healthcare_service_unit,
		"check_in": now_datetime(),
	})
	ir_doc.save(ignore_permissions=True)


def _update_ir_status(ir_doc, bed_data: frappe._dict) -> None:
	now = now_datetime()
	ir_doc.db_set({
		"status": "Admitted",
		"admitted_datetime": now,
		"custom_current_bed": bed_data.name,
		"custom_current_room": bed_data.hospital_room,
		"custom_current_ward": bed_data.hospital_ward,
		"custom_admitted_by_user": frappe.session.user,
		"custom_last_movement_on": now,
	})
	ir_doc.reload()


def _create_movement_log(
	ir_doc,
	bed_data: frappe._dict,
	reservation: str | None,
) -> str:
	bml = frappe.get_doc({
		"doctype": "Bed Movement Log",
		"movement_type": "Admission",
		"movement_datetime": now_datetime(),
		"inpatient_record": ir_doc.name,
		"patient": ir_doc.patient,
		"to_bed": bed_data.name,
		"to_room": bed_data.hospital_room,
		"to_ward": bed_data.hospital_ward,
		"to_service_unit": bed_data.healthcare_service_unit,
		"company": ir_doc.company,
		"consumed_reservation": reservation or None,
	})
	bml.flags.ignore_permissions = True
	bml.insert()
	return bml.name


def _consume_reservation(reservation: str, inpatient_record: str) -> None:
	from alcura_ipd_ext.services.bed_reservation_service import consume_reservation

	consume_reservation(reservation, inpatient_record=inpatient_record)


# ── Timeline ─────────────────────────────────────────────────────────


def _add_timeline_comments(ir_doc, bed_data: frappe._dict) -> None:
	msg = _("Patient admitted to bed {0} (Room {1}, Ward {2}) by {3}.").format(
		frappe.bold(bed_data.name),
		frappe.bold(bed_data.hospital_room),
		frappe.bold(bed_data.hospital_ward),
		frappe.session.user,
	)
	ir_doc.add_comment("Info", msg)

	if ir_doc.patient:
		try:
			patient_doc = frappe.get_doc("Patient", ir_doc.patient)
			patient_doc.add_comment("Info", msg)
		except Exception:
			pass


def _apply_monitoring_profile(inpatient_record: str, ward: str) -> None:
	"""Apply ICU monitoring profile charts after admission (best-effort)."""
	try:
		from alcura_ipd_ext.services.monitoring_profile_service import apply_profile_for_ward

		apply_profile_for_ward(inpatient_record, ward)
	except Exception:
		frappe.logger("alcura_ipd_ext").warning(
			f"Failed to apply monitoring profile for IR {inpatient_record}, ward {ward}",
			exc_info=True,
		)
