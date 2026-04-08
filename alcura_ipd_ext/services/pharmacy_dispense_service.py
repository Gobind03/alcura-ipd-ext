"""Pharmacy dispense operations: stock verification, dispensing, substitution.

Handles the full dispense lifecycle for IPD medication orders including
partial dispensing, substitution requests/approvals, and returns.
"""

from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import flt, now_datetime


def verify_stock(item_code: str, warehouse: str | None = None) -> dict:
	"""Check available stock for an item in the given warehouse.

	Returns dict with actual_qty, reserved_qty, and available_qty.
	"""
	if not item_code:
		frappe.throw(_("Item code is required for stock verification."))

	filters = {"item_code": item_code}
	if warehouse:
		filters["warehouse"] = warehouse

	bins = frappe.get_all(
		"Bin",
		filters=filters,
		fields=["warehouse", "actual_qty", "reserved_qty", "projected_qty"],
	)

	if not bins:
		return {
			"item_code": item_code,
			"warehouse": warehouse,
			"actual_qty": 0,
			"reserved_qty": 0,
			"available_qty": 0,
			"warehouses": [],
		}

	total_actual = sum(flt(b.actual_qty) for b in bins)
	total_reserved = sum(flt(b.reserved_qty) for b in bins)

	return {
		"item_code": item_code,
		"warehouse": warehouse,
		"actual_qty": total_actual,
		"reserved_qty": total_reserved,
		"available_qty": total_actual - total_reserved,
		"warehouses": [
			{
				"warehouse": b.warehouse,
				"actual_qty": flt(b.actual_qty),
				"reserved_qty": flt(b.reserved_qty),
				"available_qty": flt(b.actual_qty) - flt(b.reserved_qty),
			}
			for b in bins
		],
	}


def dispense_medication(
	order_name: str,
	dispensed_qty: float,
	*,
	dispense_type: str = "Full",
	batch_no: str | None = None,
	warehouse: str | None = None,
	expiry_date: str | None = None,
	is_substitution: bool = False,
	substitute_item: str | None = None,
	substitution_reason: str | None = None,
	substitution_approved_by: str | None = None,
	notes: str | None = None,
) -> dict:
	"""Create a dispense entry for a medication order.

	Returns dict with name of the new IPD Dispense Entry.
	"""
	order = frappe.get_doc("IPD Clinical Order", order_name)

	if order.order_type != "Medication":
		frappe.throw(_("Dispense is only applicable for Medication orders."))

	if order.status in ("Cancelled", "Draft"):
		frappe.throw(_("Cannot dispense against a {0} order.").format(order.status))

	dispense_doc = frappe.new_doc("IPD Dispense Entry")
	dispense_doc.update({
		"clinical_order": order_name,
		"patient": order.patient,
		"inpatient_record": order.inpatient_record,
		"medication_item": substitute_item or order.medication_item,
		"medication_name": order.medication_name,
		"dose": order.dose,
		"dose_uom": order.dose_uom,
		"dispensed_qty": dispensed_qty,
		"dispense_type": dispense_type,
		"batch_no": batch_no,
		"expiry_date": expiry_date,
		"warehouse": warehouse,
		"ward": order.ward,
		"bed": order.bed,
		"notes": notes,
	})

	if is_substitution:
		dispense_doc.is_substitution = 1
		dispense_doc.original_item = order.medication_item
		dispense_doc.substitution_reason = substitution_reason
		dispense_doc.substitution_approved_by = substitution_approved_by or frappe.session.user
		dispense_doc.substitution_approved_at = now_datetime()

	dispense_doc.insert(ignore_permissions=True)

	# Transition order to In Progress if still Acknowledged/Ordered
	if order.status in ("Ordered", "Acknowledged"):
		from alcura_ipd_ext.services.clinical_order_service import start_order

		start_order(order_name)

	from alcura_ipd_ext.services.clinical_order_service import record_milestone

	record_milestone(order_name, "Dispensed")

	return {"name": dispense_doc.name, "dispense_status": _get_dispense_status(order_name)}


def request_substitution(
	order_name: str,
	substitute_item: str,
	reason: str,
) -> dict:
	"""Request substitution of the prescribed medication.

	Puts the order on hold and notifies the ordering practitioner.
	"""
	order = frappe.get_doc("IPD Clinical Order", order_name)

	if order.order_type != "Medication":
		frappe.throw(_("Substitution is only applicable for Medication orders."))

	frappe.db.set_value("IPD Clinical Order", order_name, {
		"substitution_status": "Requested",
	}, update_modified=False)

	from alcura_ipd_ext.services.clinical_order_service import hold_order

	hold_order(order_name, f"Substitution requested: {reason}")

	from alcura_ipd_ext.services.order_notification_service import _send_notifications, _get_role_users

	practitioner_user = None
	if order.ordering_practitioner:
		practitioner_user = frappe.db.get_value(
			"Healthcare Practitioner", order.ordering_practitioner, "user_id"
		)

	recipients = set()
	if practitioner_user:
		recipients.add(practitioner_user)
	recipients |= _get_role_users("Physician")

	_send_notifications(
		recipients=recipients,
		subject=_(
			"Substitution requested for {0} ({1}) — {2}"
		).format(order.medication_name, order.name, reason),
		document_type="IPD Clinical Order",
		document_name=order.name,
		ref_key=f"subst_req:{order.name}",
		alert_type="Alert",
	)

	frappe.publish_realtime(
		"ipd_substitution_requested",
		{"order": order.name, "substitute_item": substitute_item, "reason": reason},
	)

	return {"order": order.name, "substitution_status": "Requested"}


def approve_substitution(order_name: str, user: str | None = None) -> dict:
	"""Approve a pending substitution request."""
	order = frappe.get_doc("IPD Clinical Order", order_name)

	if order.substitution_status != "Requested":
		frappe.throw(_("No pending substitution request for this order."))

	acting_user = user or frappe.session.user
	frappe.db.set_value("IPD Clinical Order", order_name, {
		"substitution_status": "Approved",
	}, update_modified=False)

	from alcura_ipd_ext.services.clinical_order_service import resume_order

	resume_order(order_name, user=acting_user)

	_notify_pharmacy_substitution_result(order, "approved")

	return {"order": order.name, "substitution_status": "Approved"}


def reject_substitution(order_name: str, reason: str, user: str | None = None) -> dict:
	"""Reject a pending substitution request."""
	order = frappe.get_doc("IPD Clinical Order", order_name)

	if order.substitution_status != "Requested":
		frappe.throw(_("No pending substitution request for this order."))

	frappe.db.set_value("IPD Clinical Order", order_name, {
		"substitution_status": "Rejected",
	}, update_modified=False)

	from alcura_ipd_ext.services.clinical_order_service import resume_order

	acting_user = user or frappe.session.user
	resume_order(order_name, user=acting_user)

	_notify_pharmacy_substitution_result(order, "rejected", reason)

	return {"order": order.name, "substitution_status": "Rejected"}


def return_dispense(dispense_entry: str, reason: str) -> dict:
	"""Mark a dispense entry as returned."""
	doc = frappe.get_doc("IPD Dispense Entry", dispense_entry)

	if doc.status == "Returned":
		frappe.throw(_("This dispense has already been returned."))

	doc.status = "Returned"
	doc.notes = f"{doc.notes or ''}\nReturn reason: {reason}".strip()
	doc.save(ignore_permissions=True)

	update_order_dispense_status(doc.clinical_order)

	return {"name": doc.name, "status": "Returned"}


def get_dispense_history(order_name: str) -> list[dict]:
	"""Return all dispense entries for an order."""
	return frappe.get_all(
		"IPD Dispense Entry",
		filters={"clinical_order": order_name},
		fields=[
			"name", "medication_name", "medication_item",
			"dispensed_qty", "dispense_type", "status",
			"batch_no", "warehouse", "is_substitution",
			"dispensed_by", "dispensed_at", "notes",
		],
		order_by="dispensed_at desc",
	)


def update_order_dispense_status(order_name: str) -> None:
	"""Recompute dispense_status and total_dispensed_qty on the clinical order."""
	total = frappe.db.sql(
		"""
		SELECT COALESCE(SUM(dispensed_qty), 0)
		FROM `tabIPD Dispense Entry`
		WHERE clinical_order = %s AND status = 'Dispensed'
		""",
		order_name,
	)[0][0]

	total = flt(total)
	if total <= 0:
		status = "Pending"
	else:
		order_qty = flt(
			frappe.db.get_value("IPD Clinical Order", order_name, "ordered_qty")
		)
		if order_qty and total >= order_qty:
			status = "Fully Dispensed"
		else:
			status = "Partially Dispensed"

	frappe.db.set_value(
		"IPD Clinical Order",
		order_name,
		{"dispense_status": status, "total_dispensed_qty": total},
		update_modified=False,
	)


# ── Private helpers ──────────────────────────────────────────────────


def _get_dispense_status(order_name: str) -> str:
	return frappe.db.get_value("IPD Clinical Order", order_name, "dispense_status") or "Pending"


def _notify_pharmacy_substitution_result(order, result: str, reason: str = "") -> None:
	from alcura_ipd_ext.services.order_notification_service import _send_notifications, _get_role_users

	recipients = _get_role_users("Pharmacy User")
	suffix = f" — {reason}" if reason else ""
	_send_notifications(
		recipients=recipients,
		subject=_(
			"Substitution {0} for {1} ({2}){3}"
		).format(result, order.medication_name, order.name, suffix),
		document_type="IPD Clinical Order",
		document_name=order.name,
		ref_key=f"subst_{result}:{order.name}",
	)
