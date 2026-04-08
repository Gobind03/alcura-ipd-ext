"""Bed transfer service for IPD patient movement.

Handles transaction-safe patient transfers between beds/wards, including:
- Deadlock-free dual row locking (alphabetical name order)
- Source bed housekeeping per IPD Bed Policy
- Inpatient Occupancy management (mark old as left, add new)
- Bed Movement Log audit trail
- Capacity rollup for both source and destination rooms/wards

All race-sensitive operations use ``SELECT … FOR UPDATE`` row locks.
"""

from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import now_datetime

from alcura_ipd_ext.alcura_ipd_extensions.doctype.ipd_bed_policy.ipd_bed_policy import (
	get_policy,
)
from alcura_ipd_ext.utils.bed_helpers import (
	recompute_capacity_for_bed,
	sync_hsu_occupancy_from_bed,
)


def transfer_patient(
	inpatient_record: str,
	from_bed: str,
	to_bed: str,
	reason: str,
	ordered_by: str | None = None,
	source_bed_action: str | None = None,
) -> dict:
	"""Transfer an admitted patient from one bed to another.

	Args:
		inpatient_record: Name of the Inpatient Record (status must be "Admitted").
		from_bed: Name of the source Hospital Bed (must be the patient's current bed).
		to_bed: Name of the destination Hospital Bed.
		reason: Mandatory reason for the transfer.
		ordered_by: Optional Healthcare Practitioner who ordered the transfer.
		source_bed_action: One of "Mark Dirty", "Mark Vacant", "No Change".
			Defaults to policy-driven value.

	Returns:
		Dict with keys ``inpatient_record``, ``from_bed``, ``to_bed``,
		``bed_movement_log``.

	Raises:
		frappe.ValidationError: If any validation fails.
	"""
	if not reason:
		frappe.throw(
			_("Transfer reason is required."),
			exc=frappe.ValidationError,
		)

	ir_doc = frappe.get_doc("Inpatient Record", inpatient_record)
	_validate_ir_for_transfer(ir_doc, from_bed)

	from_data, to_data = _lock_beds_ordered(from_bed, to_bed)

	_validate_source_bed(from_data, ir_doc)
	_validate_destination_bed(to_data, ir_doc)

	policy = get_policy()
	effective_action = _resolve_source_bed_action(source_bed_action, policy)

	_apply_source_bed_action(from_bed, effective_action)
	_mark_bed_occupied(to_bed)

	_sync_both_hsus(from_bed, to_bed)

	_update_inpatient_occupancies(ir_doc, from_data, to_data)

	_update_ir_custom_fields(ir_doc, to_data)

	bml_name = _create_movement_log(
		ir_doc, from_data, to_data, reason, ordered_by, effective_action,
	)

	recompute_capacity_for_bed(from_data.hospital_room, from_data.hospital_ward)
	if to_data.hospital_room != from_data.hospital_room or to_data.hospital_ward != from_data.hospital_ward:
		recompute_capacity_for_bed(to_data.hospital_room, to_data.hospital_ward)

	_add_timeline_comments(ir_doc, from_data, to_data, reason)

	_swap_monitoring_profile(inpatient_record, from_data.hospital_ward, to_data.hospital_ward)

	return {
		"inpatient_record": inpatient_record,
		"from_bed": from_bed,
		"to_bed": to_bed,
		"bed_movement_log": bml_name,
	}


# ── Validation ───────────────────────────────────────────────────────


def _validate_ir_for_transfer(ir_doc, from_bed: str) -> None:
	if ir_doc.status != "Admitted":
		frappe.throw(
			_("Inpatient Record {0} has status {1}. Transfers are only allowed for Admitted patients.").format(
				frappe.bold(ir_doc.name), frappe.bold(ir_doc.status)
			),
			exc=frappe.ValidationError,
		)

	current_bed = ir_doc.get("custom_current_bed")
	if current_bed and current_bed != from_bed:
		frappe.throw(
			_("Patient's current bed is {0}, not {1}. Cannot transfer from a bed the patient is not in.").format(
				frappe.bold(current_bed), frappe.bold(from_bed)
			),
			exc=frappe.ValidationError,
		)


def _validate_source_bed(from_data: frappe._dict, ir_doc) -> None:
	if from_data.occupancy_status != "Occupied":
		frappe.throw(
			_("Source bed {0} is {1}, not Occupied. Cannot transfer.").format(
				frappe.bold(from_data.name), frappe.bold(from_data.occupancy_status)
			),
			exc=frappe.ValidationError,
		)


def _validate_destination_bed(to_data: frappe._dict, ir_doc) -> None:
	if not to_data.is_active:
		frappe.throw(
			_("Destination bed {0} is inactive.").format(frappe.bold(to_data.name)),
			exc=frappe.ValidationError,
		)

	if to_data.occupancy_status != "Vacant":
		frappe.throw(
			_("Destination bed {0} is currently {1} and cannot be allocated.").format(
				frappe.bold(to_data.name), frappe.bold(to_data.occupancy_status)
			),
			exc=frappe.ValidationError,
		)

	if to_data.maintenance_hold:
		frappe.throw(
			_("Destination bed {0} is under maintenance hold.").format(
				frappe.bold(to_data.name)
			),
			exc=frappe.ValidationError,
		)

	if to_data.infection_block:
		frappe.throw(
			_("Destination bed {0} is under infection block.").format(
				frappe.bold(to_data.name)
			),
			exc=frappe.ValidationError,
		)

	if not to_data.healthcare_service_unit:
		frappe.throw(
			_("Destination bed {0} has no linked Healthcare Service Unit.").format(
				frappe.bold(to_data.name)
			),
			exc=frappe.ValidationError,
		)

	ir_company = ir_doc.company
	if to_data.company and ir_company and to_data.company != ir_company:
		frappe.throw(
			_("Destination bed company ({0}) does not match Inpatient Record company ({1}).").format(
				frappe.bold(to_data.company), frappe.bold(ir_company)
			),
			exc=frappe.ValidationError,
		)


# ── Locking ──────────────────────────────────────────────────────────


_BED_FIELDS = [
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
	"housekeeping_status",
]


def _lock_beds_ordered(
	from_bed: str, to_bed: str,
) -> tuple[frappe._dict, frappe._dict]:
	"""Lock both beds FOR UPDATE in deterministic name order to prevent deadlocks."""
	if from_bed == to_bed:
		frappe.throw(
			_("Source and destination beds cannot be the same."),
			exc=frappe.ValidationError,
		)

	first_name, second_name = sorted([from_bed, to_bed])

	first_data = frappe.db.get_value(
		"Hospital Bed", first_name, _BED_FIELDS, as_dict=True, for_update=True,
	)
	second_data = frappe.db.get_value(
		"Hospital Bed", second_name, _BED_FIELDS, as_dict=True, for_update=True,
	)

	if not first_data:
		frappe.throw(
			_("Hospital Bed {0} does not exist.").format(frappe.bold(first_name)),
			exc=frappe.ValidationError,
		)
	if not second_data:
		frappe.throw(
			_("Hospital Bed {0} does not exist.").format(frappe.bold(second_name)),
			exc=frappe.ValidationError,
		)

	if first_name == from_bed:
		return first_data, second_data
	return second_data, first_data


# ── State mutations ──────────────────────────────────────────────────


def _resolve_source_bed_action(explicit: str | None, policy: dict) -> str:
	if explicit and explicit in ("Mark Dirty", "Mark Vacant", "No Change"):
		return explicit
	return "Mark Dirty" if policy.get("auto_mark_dirty_on_discharge") else "Mark Vacant"


def _apply_source_bed_action(bed_name: str, action: str) -> None:
	updates: dict = {"occupancy_status": "Vacant"}

	if action == "Mark Dirty":
		updates["housekeeping_status"] = "Dirty"
	elif action == "Mark Vacant":
		updates["housekeeping_status"] = "Clean"

	frappe.db.set_value("Hospital Bed", bed_name, updates, update_modified=False)


def _mark_bed_occupied(bed_name: str) -> None:
	frappe.db.set_value(
		"Hospital Bed", bed_name, "occupancy_status", "Occupied", update_modified=False,
	)


def _sync_both_hsus(from_bed: str, to_bed: str) -> None:
	for bed_name in (from_bed, to_bed):
		bed_doc = frappe.get_doc("Hospital Bed", bed_name)
		sync_hsu_occupancy_from_bed(bed_doc)


def _update_inpatient_occupancies(
	ir_doc, from_data: frappe._dict, to_data: frappe._dict,
) -> None:
	"""Mark the current occupancy as left and add a new one."""
	now = now_datetime()

	for occ in reversed(ir_doc.inpatient_occupancies):
		if (
			occ.service_unit == from_data.healthcare_service_unit
			and not occ.left
		):
			occ.left = 1
			occ.check_out = now
			break

	ir_doc.append("inpatient_occupancies", {
		"service_unit": to_data.healthcare_service_unit,
		"check_in": now,
	})
	ir_doc.save(ignore_permissions=True)


def _update_ir_custom_fields(ir_doc, to_data: frappe._dict) -> None:
	ir_doc.db_set({
		"custom_current_bed": to_data.name,
		"custom_current_room": to_data.hospital_room,
		"custom_current_ward": to_data.hospital_ward,
		"custom_last_movement_on": now_datetime(),
	})
	ir_doc.reload()


def _create_movement_log(
	ir_doc,
	from_data: frappe._dict,
	to_data: frappe._dict,
	reason: str,
	ordered_by: str | None,
	source_bed_action: str,
) -> str:
	bml = frappe.get_doc({
		"doctype": "Bed Movement Log",
		"movement_type": "Transfer",
		"movement_datetime": now_datetime(),
		"inpatient_record": ir_doc.name,
		"patient": ir_doc.patient,
		"from_bed": from_data.name,
		"from_room": from_data.hospital_room,
		"from_ward": from_data.hospital_ward,
		"from_service_unit": from_data.healthcare_service_unit,
		"to_bed": to_data.name,
		"to_room": to_data.hospital_room,
		"to_ward": to_data.hospital_ward,
		"to_service_unit": to_data.healthcare_service_unit,
		"reason": reason,
		"ordered_by_practitioner": ordered_by,
		"source_bed_action": source_bed_action,
		"company": ir_doc.company,
	})
	bml.flags.ignore_permissions = True
	bml.insert()
	return bml.name


# ── Timeline ─────────────────────────────────────────────────────────


def _add_timeline_comments(
	ir_doc, from_data: frappe._dict, to_data: frappe._dict, reason: str,
) -> None:
	msg = _("Patient transferred from bed {0} (Ward {1}) to bed {2} (Ward {3}). Reason: {4}").format(
		frappe.bold(from_data.name),
		frappe.bold(from_data.hospital_ward),
		frappe.bold(to_data.name),
		frappe.bold(to_data.hospital_ward),
		reason,
	)
	ir_doc.add_comment("Info", msg)

	if ir_doc.patient:
		try:
			patient_doc = frappe.get_doc("Patient", ir_doc.patient)
			patient_doc.add_comment("Info", msg)
		except Exception:
			pass


def _swap_monitoring_profile(
	inpatient_record: str, old_ward: str, new_ward: str,
) -> None:
	"""Swap monitoring profile charts when ward classification changes (best-effort)."""
	try:
		from alcura_ipd_ext.services.monitoring_profile_service import swap_profile_on_transfer

		swap_profile_on_transfer(inpatient_record, old_ward, new_ward)
	except Exception:
		frappe.logger("alcura_ipd_ext").warning(
			f"Failed to swap monitoring profile for IR {inpatient_record}",
			exc_info=True,
		)
