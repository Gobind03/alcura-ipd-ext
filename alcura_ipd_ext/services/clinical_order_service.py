"""Clinical order creation, status transitions, and lifecycle management.

Central service for all IPD Clinical Order operations across
Medication, Lab Test, Radiology, and Procedure order types.
"""

from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import now_datetime


_ACTIVE_STATUSES = ("Draft", "Ordered", "Acknowledged", "In Progress", "On Hold")


def create_order(
	order_type: str,
	patient: str,
	inpatient_record: str,
	company: str,
	*,
	ordering_practitioner: str | None = None,
	source_encounter: str | None = None,
	urgency: str = "Routine",
	target_department: str | None = None,
	auto_place: bool = True,
	**kwargs,
) -> "frappe.Document":
	"""Create an IPD Clinical Order and optionally transition to Ordered."""
	ir_status = frappe.db.get_value("Inpatient Record", inpatient_record, "status")
	if ir_status not in ("Admitted", "Admission Scheduled"):
		frappe.throw(
			_("Cannot place orders: Inpatient Record is {0}.").format(ir_status),
			exc=frappe.ValidationError,
		)

	doc = frappe.new_doc("IPD Clinical Order")
	doc.update({
		"order_type": order_type,
		"patient": patient,
		"inpatient_record": inpatient_record,
		"company": company,
		"urgency": urgency,
		"ordering_practitioner": ordering_practitioner,
		"source_encounter": source_encounter,
		"target_department": target_department,
	})
	doc.update(kwargs)

	if auto_place:
		doc.status = "Draft"
		doc.insert(ignore_permissions=True)
		place_order(doc.name)
		doc.reload()
	else:
		doc.insert(ignore_permissions=True)

	return doc


def place_order(order_name: str) -> None:
	"""Transition Draft -> Ordered, set timestamps, initialise SLA, fire notifications."""
	doc = frappe.get_doc("IPD Clinical Order", order_name)
	doc.transition_to("Ordered")
	doc.save(ignore_permissions=True)

	from alcura_ipd_ext.services.order_sla_service import initialize_sla

	initialize_sla(doc)

	from alcura_ipd_ext.services.order_notification_service import notify_order_created

	notify_order_created(doc)

	# Auto-generate MAR schedule for medication orders
	if doc.order_type == "Medication" and not doc.is_prn:
		from alcura_ipd_ext.services.mar_schedule_service import generate_mar_entries_for_order

		generate_mar_entries_for_order(doc.name)

	# Auto-create lab sample for lab test orders
	if doc.order_type == "Lab Test":
		from alcura_ipd_ext.services.lab_sample_service import create_sample

		create_sample(doc.name)

	frappe.publish_realtime(
		"ipd_order_placed",
		{"order": doc.name, "order_type": doc.order_type, "patient": doc.patient},
	)


def acknowledge_order(order_name: str, user: str | None = None) -> None:
	doc = frappe.get_doc("IPD Clinical Order", order_name)
	doc.transition_to("Acknowledged", user=user)
	doc.save(ignore_permissions=True)
	_record_milestone(doc, "Acknowledged", user)

	from alcura_ipd_ext.services.order_notification_service import notify_order_acknowledged

	notify_order_acknowledged(doc)


def start_order(order_name: str, user: str | None = None) -> None:
	doc = frappe.get_doc("IPD Clinical Order", order_name)
	doc.transition_to("In Progress", user=user)
	doc.save(ignore_permissions=True)
	_record_milestone(doc, "In Progress", user)


def complete_order(order_name: str, user: str | None = None, **kwargs) -> None:
	doc = frappe.get_doc("IPD Clinical Order", order_name)
	if kwargs:
		doc.update(kwargs)
	doc.transition_to("Completed", user=user)
	doc.save(ignore_permissions=True)
	_record_milestone(doc, "Completed", user)

	from alcura_ipd_ext.services.order_notification_service import notify_order_completed

	notify_order_completed(doc)


def cancel_order(order_name: str, reason: str, user: str | None = None) -> None:
	doc = frappe.get_doc("IPD Clinical Order", order_name)
	doc.cancellation_reason = reason
	doc.transition_to("Cancelled", user=user)
	doc.save(ignore_permissions=True)
	_record_milestone(doc, "Cancelled", user)

	if doc.order_type == "Medication":
		from alcura_ipd_ext.services.mar_schedule_service import cancel_pending_mar_entries

		cancel_pending_mar_entries(order_name)


def hold_order(order_name: str, reason: str, user: str | None = None) -> None:
	doc = frappe.get_doc("IPD Clinical Order", order_name)
	doc.hold_reason = reason
	doc.transition_to("On Hold", user=user)
	doc.save(ignore_permissions=True)
	_record_milestone(doc, "On Hold", user)

	if doc.order_type == "Medication":
		from alcura_ipd_ext.services.mar_schedule_service import cancel_pending_mar_entries

		cancel_pending_mar_entries(order_name)


def resume_order(order_name: str, user: str | None = None) -> None:
	doc = frappe.get_doc("IPD Clinical Order", order_name)
	# Resume to last valid non-hold status
	target = "Acknowledged" if doc.acknowledged_at else "Ordered"
	doc.hold_reason = ""
	doc.transition_to(target, user=user)
	doc.save(ignore_permissions=True)
	_record_milestone(doc, "Resumed", user)


def record_milestone(order_name: str, milestone: str, user: str | None = None) -> None:
	"""Record an arbitrary milestone (e.g. 'Dispensed', 'Sample Collected')."""
	doc = frappe.get_doc("IPD Clinical Order", order_name)
	_record_milestone(doc, milestone, user)

	from alcura_ipd_ext.services.order_sla_service import advance_sla

	advance_sla(doc, milestone)


def create_orders_from_encounter(encounter_name: str) -> list[str]:
	"""Auto-create Clinical Orders from a submitted Patient Encounter's
	prescription child tables (drug, lab test, procedure)."""
	enc = frappe.get_doc("Patient Encounter", encounter_name)
	ir = enc.get("custom_linked_inpatient_record")
	if not ir:
		return []

	ir_status = frappe.db.get_value("Inpatient Record", ir, "status")
	if ir_status not in ("Admitted", "Admission Scheduled"):
		return []

	created = []

	# Medication orders from drug_prescription
	for row in enc.get("drug_prescription") or []:
		order = create_order(
			order_type="Medication",
			patient=enc.patient,
			inpatient_record=ir,
			company=enc.company,
			ordering_practitioner=enc.practitioner,
			source_encounter=enc.name,
			medication_item=row.get("drug_code"),
			medication_name=row.get("drug_name") or row.get("drug_code"),
			dose=row.get("dosage"),
			dose_uom=row.get("dosage_form"),
			frequency=_map_pe_interval(row),
			duration_days=row.get("period"),
			indication=row.get("comment"),
		)
		created.append(order.name)

	# Lab orders from lab_test_prescription
	for row in enc.get("lab_test_prescription") or []:
		order = create_order(
			order_type="Lab Test",
			patient=enc.patient,
			inpatient_record=ir,
			company=enc.company,
			ordering_practitioner=enc.practitioner,
			source_encounter=enc.name,
			lab_test_template=row.get("lab_test_code"),
			lab_test_name=row.get("lab_test_name") or row.get("lab_test_code"),
		)
		created.append(order.name)

	# Procedure orders from procedure_prescription
	for row in enc.get("procedure_prescription") or []:
		order = create_order(
			order_type="Procedure",
			patient=enc.patient,
			inpatient_record=ir,
			company=enc.company,
			ordering_practitioner=enc.practitioner,
			source_encounter=enc.name,
			procedure_template=row.get("procedure"),
			procedure_name=row.get("procedure_name") or row.get("procedure"),
			clinical_notes=row.get("comments"),
		)
		created.append(order.name)

	if created:
		frappe.db.set_value("Patient Encounter", encounter_name, "custom_has_ipd_orders", 1)
		frappe.msgprint(
			_("{0} clinical order(s) created from encounter {1}.").format(
				len(created), encounter_name
			),
			alert=True,
		)

	return created


def update_ir_order_counts(inpatient_record: str) -> None:
	"""Refresh aggregate order counts on the Inpatient Record."""
	counts = frappe.db.sql(
		"""
		SELECT
			COALESCE(SUM(order_type = 'Medication' AND status IN %(active)s), 0) AS med,
			COALESCE(SUM(order_type = 'Lab Test' AND status IN %(active)s), 0) AS lab,
			COALESCE(SUM(order_type IN ('Radiology', 'Procedure') AND status IN %(active)s), 0) AS proc,
			COALESCE(SUM(status IN ('Ordered', 'Acknowledged')), 0) AS pending
		FROM `tabIPD Clinical Order`
		WHERE inpatient_record = %(ir)s
		""",
		{"ir": inpatient_record, "active": _ACTIVE_STATUSES},
		as_dict=True,
	)

	if counts:
		row = counts[0]
		frappe.db.set_value(
			"Inpatient Record",
			inpatient_record,
			{
				"custom_active_medication_orders": row.med,
				"custom_active_lab_orders": row.lab,
				"custom_active_procedure_orders": row.proc,
				"custom_pending_orders_count": row.pending,
			},
			update_modified=False,
		)


def get_orders_for_ir(
	inpatient_record: str,
	order_type: str | None = None,
	status: str | None = None,
	limit: int = 50,
) -> list[dict]:
	"""Retrieve orders for an Inpatient Record with optional filters."""
	filters = {"inpatient_record": inpatient_record}
	if order_type:
		filters["order_type"] = order_type
	if status:
		filters["status"] = status

	return frappe.get_all(
		"IPD Clinical Order",
		filters=filters,
		fields=[
			"name", "order_type", "urgency", "status",
			"patient_name", "ordering_practitioner_name",
			"medication_name", "lab_test_name", "procedure_name",
			"ordered_at", "current_sla_target_at", "is_sla_breached",
		],
		order_by="ordered_at desc",
		limit_page_length=limit,
	)


# ── Private helpers ──────────────────────────────────────────────────


def _record_milestone(doc: "frappe.Document", milestone: str, user: str | None) -> None:
	"""Append a milestone row to the order's SLA milestones child table."""
	now = now_datetime()
	acting_user = user or frappe.session.user

	# Check if there's a target for this milestone
	target_at = None
	for row in doc.sla_milestones:
		if row.milestone == milestone and row.target_at and not row.actual_at:
			target_at = row.target_at
			row.actual_at = now
			row.recorded_by = acting_user
			row.is_breached = 1 if now > row.target_at else 0
			doc.save(ignore_permissions=True)
			return

	# No existing row — append new
	doc.append("sla_milestones", {
		"milestone": milestone,
		"actual_at": now,
		"recorded_by": acting_user,
	})
	doc.save(ignore_permissions=True)


def _map_pe_interval(row) -> str:
	"""Best-effort mapping from PE Drug Prescription interval to frequency code."""
	interval = row.get("interval")
	uom = (row.get("interval_uom") or "").lower()
	if not interval:
		return ""

	interval = int(interval) if interval else 0
	if uom == "hour":
		hour_map = {4: "Q4H", 6: "Q6H", 8: "Q8H", 12: "Q12H", 24: "OD"}
		return hour_map.get(interval, "")
	if uom == "day":
		day_map = {1: "OD", 0: "STAT"}
		return day_map.get(interval, "")
	return ""
