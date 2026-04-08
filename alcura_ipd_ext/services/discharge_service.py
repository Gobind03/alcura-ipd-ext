"""Discharge service — orchestrates the full bed vacate flow.

Coordinates discharge advice validation, bed state transitions,
housekeeping task creation, Inpatient Occupancy close-out, capacity
rollup, HSU synchronization, and movement log creation.

All race-sensitive operations use ``SELECT … FOR UPDATE`` row locks.
"""

from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import now_datetime

from alcura_ipd_ext.alcura_ipd_ext.doctype.ipd_bed_policy.ipd_bed_policy import (
	get_policy,
)
from alcura_ipd_ext.utils.bed_helpers import (
	recompute_capacity_for_bed,
	sync_hsu_occupancy_from_bed,
)


def process_bed_vacate(inpatient_record: str) -> dict:
	"""Process the bed vacate for a patient discharge.

	1. Validate discharge advice is acknowledged/completed
	2. Lock bed FOR UPDATE
	3. Create Discharge movement log
	4. Set bed occupancy_status = Vacant
	5. Apply housekeeping action (from policy)
	6. If dirty: create Bed Housekeeping Task
	7. Mark Inpatient Occupancy left=1, check_out=now
	8. Clear IR custom bed fields
	9. Sync HSU occupancy
	10. Recompute capacity rollup
	11. Add timeline comments
	12. Send notifications

	Returns dict with keys: inpatient_record, bed_movement_log,
	housekeeping_task (if created).
	"""
	ir_doc = frappe.get_doc("Inpatient Record", inpatient_record)
	_validate_ir_for_vacate(ir_doc)

	bed_name = ir_doc.get("custom_current_bed")
	if not bed_name:
		frappe.throw(
			_("No current bed assigned on Inpatient Record {0}.").format(
				frappe.bold(inpatient_record)
			),
			exc=frappe.ValidationError,
		)

	bed_data = _lock_bed(bed_name)
	_validate_bed_for_vacate(bed_data)

	policy = get_policy()
	should_dirty = policy.get("auto_mark_dirty_on_discharge")

	_vacate_bed(bed_name, should_dirty)

	_mark_occupancy_left(ir_doc, bed_data)

	bml_name = _create_discharge_movement_log(ir_doc, bed_data, should_dirty)

	_clear_ir_bed_fields(ir_doc)

	_sync_hsu(bed_name)

	recompute_capacity_for_bed(bed_data.hospital_room, bed_data.hospital_ward)

	housekeeping_task = None
	if should_dirty:
		from alcura_ipd_ext.services.housekeeping_service import (
			create_housekeeping_task,
		)
		housekeeping_task = create_housekeeping_task(
			hospital_bed=bed_name,
			trigger_event="Discharge",
			inpatient_record=inpatient_record,
			movement_log=bml_name,
		)

	_complete_discharge_advice(ir_doc)

	_add_timeline_comments(ir_doc, bed_data)

	_send_vacate_notifications(ir_doc, bed_data)

	return {
		"inpatient_record": inpatient_record,
		"bed_movement_log": bml_name,
		"housekeeping_task": housekeeping_task,
		"bed": bed_name,
	}


# ── Validation ───────────────────────────────────────────────────────


def _validate_ir_for_vacate(ir_doc) -> None:
	if ir_doc.status not in ("Admitted", "Discharge Scheduled"):
		frappe.throw(
			_("Cannot vacate bed: Inpatient Record {0} has status {1}.").format(
				frappe.bold(ir_doc.name), frappe.bold(ir_doc.status)
			),
			exc=frappe.ValidationError,
		)

	advice_name = ir_doc.get("custom_discharge_advice")
	if advice_name:
		advice_status = frappe.db.get_value(
			"IPD Discharge Advice", advice_name, "status"
		)
		if advice_status not in ("Acknowledged", "Completed"):
			frappe.throw(
				_("Discharge advice {0} has status {1}. "
				  "It must be Acknowledged or Completed before vacating.").format(
					frappe.bold(advice_name), frappe.bold(advice_status)
				),
				exc=frappe.ValidationError,
			)


def _validate_bed_for_vacate(bed_data: frappe._dict) -> None:
	if bed_data.occupancy_status != "Occupied":
		frappe.throw(
			_("Bed {0} is {1}, not Occupied. Cannot vacate.").format(
				frappe.bold(bed_data.name), frappe.bold(bed_data.occupancy_status)
			),
			exc=frappe.ValidationError,
		)


# ── Locking ──────────────────────────────────────────────────────────

_BED_FIELDS = [
	"name", "occupancy_status", "hospital_room", "hospital_ward",
	"company", "healthcare_service_unit", "infection_block",
	"housekeeping_status",
]


def _lock_bed(bed_name: str) -> frappe._dict:
	bed_data = frappe.db.get_value(
		"Hospital Bed", bed_name, _BED_FIELDS, as_dict=True, for_update=True,
	)
	if not bed_data:
		frappe.throw(
			_("Hospital Bed {0} does not exist.").format(frappe.bold(bed_name)),
			exc=frappe.ValidationError,
		)
	return bed_data


# ── State mutations ──────────────────────────────────────────────────


def _vacate_bed(bed_name: str, should_dirty: bool) -> None:
	updates = {"occupancy_status": "Vacant"}
	if should_dirty:
		updates["housekeeping_status"] = "Dirty"
	else:
		updates["housekeeping_status"] = "Clean"
	frappe.db.set_value("Hospital Bed", bed_name, updates, update_modified=False)


def _mark_occupancy_left(ir_doc, bed_data: frappe._dict) -> None:
	now = now_datetime()
	for occ in reversed(ir_doc.inpatient_occupancies):
		if (
			occ.service_unit == bed_data.healthcare_service_unit
			and not occ.left
		):
			occ.left = 1
			occ.check_out = now
			break
	ir_doc.save(ignore_permissions=True)


def _clear_ir_bed_fields(ir_doc) -> None:
	ir_doc.db_set({
		"custom_current_bed": None,
		"custom_current_room": None,
		"custom_current_ward": None,
		"custom_last_movement_on": now_datetime(),
	})


def _sync_hsu(bed_name: str) -> None:
	bed_doc = frappe.get_doc("Hospital Bed", bed_name)
	sync_hsu_occupancy_from_bed(bed_doc)


def _create_discharge_movement_log(
	ir_doc, bed_data: frappe._dict, should_dirty: bool,
) -> str:
	bml = frappe.get_doc({
		"doctype": "Bed Movement Log",
		"movement_type": "Discharge",
		"movement_datetime": now_datetime(),
		"inpatient_record": ir_doc.name,
		"patient": ir_doc.patient,
		"from_bed": bed_data.name,
		"from_room": bed_data.hospital_room,
		"from_ward": bed_data.hospital_ward,
		"from_service_unit": bed_data.healthcare_service_unit,
		"source_bed_action": "Mark Dirty" if should_dirty else "Mark Vacant",
		"company": ir_doc.company,
	})
	bml.flags.ignore_permissions = True
	bml.insert()
	return bml.name


def _complete_discharge_advice(ir_doc) -> None:
	"""Mark the discharge advice as completed if it exists and is acknowledged."""
	advice_name = ir_doc.get("custom_discharge_advice")
	if not advice_name:
		return

	advice_status = frappe.db.get_value(
		"IPD Discharge Advice", advice_name, "status"
	)
	if advice_status == "Acknowledged":
		try:
			from alcura_ipd_ext.services.discharge_advice_service import complete_advice
			complete_advice(advice_name)
		except Exception:
			frappe.logger("alcura_ipd_ext").warning(
				f"Failed to complete discharge advice {advice_name}",
				exc_info=True,
			)


# ── Timeline ─────────────────────────────────────────────────────────


def _add_timeline_comments(ir_doc, bed_data: frappe._dict) -> None:
	msg = _("Patient discharged from bed {0} (Ward {1}) by {2}.").format(
		frappe.bold(bed_data.name),
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


def _send_vacate_notifications(ir_doc, bed_data: frappe._dict) -> None:
	try:
		from alcura_ipd_ext.services.discharge_notification_service import (
			notify_bed_vacated,
		)
		patient_name = frappe.db.get_value("Patient", ir_doc.patient, "patient_name") or ""
		notify_bed_vacated(
			inpatient_record=ir_doc.name,
			patient_name=patient_name,
			ward=bed_data.hospital_ward,
			bed=bed_data.name,
		)
	except Exception:
		frappe.logger("alcura_ipd_ext").warning(
			f"Failed to send bed vacate notifications for IR {ir_doc.name}",
			exc_info=True,
		)
