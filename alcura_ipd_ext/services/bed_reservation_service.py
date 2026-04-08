"""Bed Reservation business logic.

All race-sensitive operations (activate, cancel, expire, consume) use
``SELECT … FOR UPDATE`` row locks on both the reservation and (for
Specific Bed reservations) the Hospital Bed row to prevent double-booking.
"""

from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import now_datetime, add_to_date, get_datetime

from alcura_ipd_ext.alcura_ipd_ext.doctype.ipd_bed_policy.ipd_bed_policy import (
	get_policy,
)
from alcura_ipd_ext.utils.bed_helpers import recompute_capacity_for_bed

# Valid status transitions: {from_status: [allowed_to_statuses]}
VALID_TRANSITIONS: dict[str, list[str]] = {
	"Draft": ["Active", "Cancelled"],
	"Active": ["Expired", "Cancelled", "Consumed"],
}


def validate_transition(current: str, target: str) -> None:
	allowed = VALID_TRANSITIONS.get(current, [])
	if target not in allowed:
		frappe.throw(
			_("Cannot transition Bed Reservation from {0} to {1}.").format(
				frappe.bold(current), frappe.bold(target)
			),
			exc=frappe.ValidationError,
		)


def compute_reservation_end(start: str, timeout_minutes: int) -> str:
	"""Return reservation_end as datetime string."""
	return str(add_to_date(get_datetime(start), minutes=timeout_minutes))


def get_default_timeout() -> int:
	return get_policy().get("reservation_timeout_minutes", 120)


# ── Activate ────────────────────────────────────────────────────────


def activate_reservation(reservation_name: str) -> None:
	"""Transition a Draft reservation to Active with race-safe bed locking.

	For Specific Bed reservations, acquires a row lock on the Hospital Bed
	to prevent concurrent double-booking.
	"""
	doc = frappe.get_doc("Bed Reservation", reservation_name)
	validate_transition(doc.status, "Active")

	if doc.reservation_type == "Specific Bed":
		_activate_specific_bed(doc)
	else:
		_activate_room_type_hold(doc)

	doc.db_set({
		"status": "Active",
		"reserved_by": frappe.session.user,
		"reserved_on": now_datetime(),
	})
	doc.reload()
	doc.add_comment("Info", _("Reservation activated by {0}.").format(frappe.session.user))
	_notify_patient_timeline(doc, _("Bed reservation {0} activated.").format(doc.name))


def _activate_specific_bed(doc) -> None:
	"""Lock the bed row and verify it is Vacant with no conflicting reservation."""
	if not doc.hospital_bed:
		frappe.throw(
			_("Hospital Bed is required for Specific Bed reservations."),
			exc=frappe.ValidationError,
		)

	bed_data = frappe.db.get_value(
		"Hospital Bed",
		doc.hospital_bed,
		["occupancy_status", "company", "hospital_room", "hospital_ward"],
		as_dict=True,
		for_update=True,
	)
	if not bed_data:
		frappe.throw(
			_("Hospital Bed {0} does not exist.").format(frappe.bold(doc.hospital_bed)),
			exc=frappe.ValidationError,
		)

	if bed_data.company != doc.company:
		frappe.throw(
			_("Bed company ({0}) does not match reservation company ({1}).").format(
				bed_data.company, doc.company
			),
			exc=frappe.ValidationError,
		)

	if bed_data.occupancy_status != "Vacant":
		frappe.throw(
			_("Bed {0} is currently {1} and cannot be reserved.").format(
				frappe.bold(doc.hospital_bed),
				frappe.bold(bed_data.occupancy_status),
			),
			exc=frappe.ValidationError,
		)

	existing = frappe.db.get_value(
		"Bed Reservation",
		{"hospital_bed": doc.hospital_bed, "status": "Active", "name": ("!=", doc.name)},
		"name",
		for_update=True,
	)
	if existing:
		frappe.throw(
			_("Bed {0} already has an active reservation ({1}).").format(
				frappe.bold(doc.hospital_bed),
				frappe.bold(existing),
			),
			exc=frappe.ValidationError,
		)

	frappe.db.set_value(
		"Hospital Bed", doc.hospital_bed, "occupancy_status", "Reserved", update_modified=False
	)
	recompute_capacity_for_bed(bed_data.hospital_room, bed_data.hospital_ward)


def _activate_room_type_hold(doc) -> None:
	"""Validate that at least one bed of the requested type is available."""
	if not doc.service_unit_type:
		frappe.throw(
			_("Room Type is required for Room Type Hold reservations."),
			exc=frappe.ValidationError,
		)

	filters = {
		"is_active": 1,
		"occupancy_status": "Vacant",
		"service_unit_type": doc.service_unit_type,
	}
	if doc.hospital_ward:
		filters["hospital_ward"] = doc.hospital_ward
	if doc.company:
		filters["company"] = doc.company

	vacant_count = frappe.db.count("Hospital Bed", filters)

	active_holds = frappe.db.count(
		"Bed Reservation",
		{
			"reservation_type": "Room Type Hold",
			"status": "Active",
			"service_unit_type": doc.service_unit_type,
			"company": doc.company,
			"name": ("!=", doc.name),
		},
	)

	effective_available = vacant_count - active_holds
	if effective_available <= 0:
		frappe.throw(
			_("No available beds of type {0}. Vacant: {1}, already held: {2}.").format(
				frappe.bold(doc.service_unit_type), vacant_count, active_holds
			),
			exc=frappe.ValidationError,
		)


# ── Cancel ──────────────────────────────────────────────────────────


def cancel_reservation(
	reservation_name: str,
	reason: str,
	is_override: bool = False,
	override_reason: str = "",
) -> None:
	"""Cancel an Active (or Draft) reservation, releasing the bed if held."""
	if not reason:
		frappe.throw(
			_("Cancellation reason is required."),
			exc=frappe.ValidationError,
		)

	doc = frappe.get_doc("Bed Reservation", reservation_name, for_update=True)
	validate_transition(doc.status, "Cancelled")

	if is_override:
		if "Healthcare Administrator" not in frappe.get_roles(frappe.session.user):
			frappe.throw(
				_("Only Healthcare Administrators can override reservations."),
				exc=frappe.PermissionError,
			)
		if not override_reason:
			frappe.throw(
				_("Override reason is required."),
				exc=frappe.ValidationError,
			)

	if doc.status == "Active" and doc.reservation_type == "Specific Bed" and doc.hospital_bed:
		_release_bed(doc.hospital_bed)

	update_fields = {
		"status": "Cancelled",
		"cancelled_by": frappe.session.user,
		"cancelled_on": now_datetime(),
		"cancellation_reason": reason,
	}
	if is_override:
		update_fields.update({
			"is_override": 1,
			"override_authorized_by": frappe.session.user,
			"override_reason": override_reason,
		})

	doc.db_set(update_fields)
	doc.reload()
	doc.add_comment("Info", _("Reservation cancelled: {0}").format(reason))
	_notify_patient_timeline(doc, _("Bed reservation {0} cancelled.").format(doc.name))


# ── Expire ──────────────────────────────────────────────────────────


def expire_overdue_reservations() -> int:
	"""Expire all Active reservations past their reservation_end. Returns count."""
	overdue = frappe.db.get_all(
		"Bed Reservation",
		filters={
			"status": "Active",
			"reservation_end": ("<", now_datetime()),
		},
		pluck="name",
	)

	count = 0
	for name in overdue:
		try:
			_expire_single(name)
			count += 1
		except Exception:
			frappe.log_error(
				title=f"Bed Reservation Expiry Failed: {name}",
				message=frappe.get_traceback(),
			)

	if count:
		frappe.db.commit()

	return count


def _expire_single(reservation_name: str) -> None:
	"""Expire a single reservation with row lock."""
	doc = frappe.get_doc("Bed Reservation", reservation_name, for_update=True)

	if doc.status != "Active":
		return

	if doc.reservation_type == "Specific Bed" and doc.hospital_bed:
		_release_bed(doc.hospital_bed)

	doc.db_set({
		"status": "Expired",
		"expired_on": now_datetime(),
	})
	doc.reload()
	doc.add_comment("Info", _("Reservation auto-expired."))

	if doc.reserved_by:
		_send_expiry_notification(doc)


# ── Consume ─────────────────────────────────────────────────────────


def consume_reservation(reservation_name: str, inpatient_record: str) -> None:
	"""Mark a reservation as Consumed when the patient is admitted."""
	if not inpatient_record:
		frappe.throw(
			_("Inpatient Record is required to consume a reservation."),
			exc=frappe.ValidationError,
		)

	doc = frappe.get_doc("Bed Reservation", reservation_name, for_update=True)
	validate_transition(doc.status, "Consumed")

	doc.db_set({
		"status": "Consumed",
		"consumed_on": now_datetime(),
		"consumed_by_inpatient_record": inpatient_record,
	})
	doc.reload()
	doc.add_comment(
		"Info",
		_("Reservation consumed by admission {0}.").format(
			frappe.bold(inpatient_record)
		),
	)
	_notify_patient_timeline(
		doc, _("Bed reservation {0} consumed for admission {1}.").format(doc.name, inpatient_record)
	)


# ── Helpers ─────────────────────────────────────────────────────────


def _release_bed(bed_name: str) -> None:
	"""Reset a Hospital Bed from Reserved back to Vacant."""
	current = frappe.db.get_value(
		"Hospital Bed", bed_name, "occupancy_status", for_update=True
	)
	if current != "Reserved":
		return

	frappe.db.set_value(
		"Hospital Bed", bed_name, "occupancy_status", "Vacant", update_modified=False
	)
	room, ward = frappe.db.get_value(
		"Hospital Bed", bed_name, ["hospital_room", "hospital_ward"]
	)
	recompute_capacity_for_bed(room, ward)


def _notify_patient_timeline(doc, message: str) -> None:
	"""Add a comment on the Patient record for traceability."""
	if not doc.patient:
		return
	try:
		patient_doc = frappe.get_doc("Patient", doc.patient)
		patient_doc.add_comment("Info", message)
	except Exception:
		pass


def _send_expiry_notification(doc) -> None:
	"""Send an in-app notification to the user who created the reservation."""
	frappe.publish_realtime(
		"bed_reservation_expired",
		{"reservation": doc.name, "bed": doc.hospital_bed or ""},
		user=doc.reserved_by,
	)


def has_active_reservation(bed_name: str) -> str | None:
	"""Return the active reservation name for a bed, or None."""
	return frappe.db.get_value(
		"Bed Reservation",
		{"hospital_bed": bed_name, "status": "Active"},
		"name",
	)


def get_active_holds_by_room_type(
	service_unit_type: str, company: str | None = None
) -> int:
	"""Count active Room Type Hold reservations for a given room type."""
	filters: dict = {
		"reservation_type": "Room Type Hold",
		"status": "Active",
		"service_unit_type": service_unit_type,
	}
	if company:
		filters["company"] = company
	return frappe.db.count("Bed Reservation", filters)
