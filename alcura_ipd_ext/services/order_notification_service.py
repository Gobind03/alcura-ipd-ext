"""Notification service for IPD Clinical Orders.

Handles realtime events, Notification Log creation, and deduplication
for order lifecycle events and SLA breach escalations.
"""

from __future__ import annotations

import frappe
from frappe import _


def notify_order_created(order: "frappe.Document") -> None:
	"""Notify target department + nurse station that a new order has been placed."""
	subject = _("{0} order placed for {1} — {2} ({3})").format(
		order.order_type,
		order.patient_name,
		_order_detail_label(order),
		order.urgency,
	)

	recipients = _get_department_recipients(order)
	recipients |= _get_role_users("Nursing User")

	_send_notifications(
		recipients=recipients,
		subject=subject,
		document_type="IPD Clinical Order",
		document_name=order.name,
		ref_key=f"order_created:{order.name}",
	)

	frappe.publish_realtime(
		"ipd_order_notification",
		{
			"action": "created",
			"order": order.name,
			"order_type": order.order_type,
			"patient": order.patient,
			"patient_name": order.patient_name,
			"urgency": order.urgency,
			"ward": order.ward,
		},
	)


def notify_order_acknowledged(order: "frappe.Document") -> None:
	"""Notify ordering practitioner that their order has been acknowledged."""
	if not order.ordering_practitioner:
		return

	practitioner_user = frappe.db.get_value(
		"Healthcare Practitioner", order.ordering_practitioner, "user_id"
	)
	if not practitioner_user:
		return

	subject = _("{0} order acknowledged: {1} for {2}").format(
		order.order_type,
		_order_detail_label(order),
		order.patient_name,
	)

	_send_notifications(
		recipients={practitioner_user},
		subject=subject,
		document_type="IPD Clinical Order",
		document_name=order.name,
		ref_key=f"order_ack:{order.name}",
	)


def notify_order_completed(order: "frappe.Document") -> None:
	"""Notify ordering practitioner + nurse that the order is complete."""
	recipients = _get_role_users("Nursing User")

	if order.ordering_practitioner:
		puser = frappe.db.get_value(
			"Healthcare Practitioner", order.ordering_practitioner, "user_id"
		)
		if puser:
			recipients.add(puser)

	subject = _("{0} order completed: {1} for {2}").format(
		order.order_type,
		_order_detail_label(order),
		order.patient_name,
	)

	_send_notifications(
		recipients=recipients,
		subject=subject,
		document_type="IPD Clinical Order",
		document_name=order.name,
		ref_key=f"order_done:{order.name}",
	)

	frappe.publish_realtime(
		"ipd_order_notification",
		{"action": "completed", "order": order.name, "order_type": order.order_type},
	)


def notify_sla_breach(order: "frappe.Document", milestone: str, escalation_role: str) -> None:
	"""Notify escalation role users about an SLA breach."""
	recipients = _get_role_users(escalation_role)
	if not recipients:
		return

	subject = _("SLA BREACH: {0} order {1} — milestone '{2}' overdue for {3}").format(
		order.order_type,
		order.name,
		milestone,
		order.patient_name,
	)

	_send_notifications(
		recipients=recipients,
		subject=subject,
		document_type="IPD Clinical Order",
		document_name=order.name,
		ref_key=f"sla_breach:{order.name}:{milestone}",
		alert_type="Alert",
	)

	frappe.publish_realtime(
		"ipd_sla_breach",
		{
			"order": order.name,
			"order_type": order.order_type,
			"milestone": milestone,
			"patient": order.patient,
			"patient_name": order.patient_name,
		},
	)


def notify_critical_result(order: "frappe.Document") -> None:
	"""Urgent notification for critical lab/radiology results."""
	recipients = _get_role_users("Nursing User")

	if order.ordering_practitioner:
		puser = frappe.db.get_value(
			"Healthcare Practitioner", order.ordering_practitioner, "user_id"
		)
		if puser:
			recipients.add(puser)

	subject = _("CRITICAL RESULT: {0} for {1} — immediate attention required").format(
		_order_detail_label(order),
		order.patient_name,
	)

	_send_notifications(
		recipients=recipients,
		subject=subject,
		document_type="IPD Clinical Order",
		document_name=order.name,
		ref_key=f"critical_result:{order.name}",
		alert_type="Alert",
	)

	frappe.publish_realtime(
		"ipd_critical_result",
		{"order": order.name, "patient": order.patient, "patient_name": order.patient_name},
	)


# ── Private helpers ──────────────────────────────────────────────────


def _send_notifications(
	recipients: set[str],
	subject: str,
	document_type: str,
	document_name: str,
	ref_key: str,
	alert_type: str = "Mention",
) -> int:
	"""Create Notification Log entries with deduplication."""
	sent = 0
	for user in recipients:
		if user in ("Administrator", "Guest"):
			continue
		# Dedup: skip if unread notification with same ref exists
		existing = frappe.db.exists(
			"Notification Log",
			{
				"for_user": user,
				"document_type": document_type,
				"document_name": document_name,
				"read": 0,
				"subject": ("like", f"%{ref_key}%"),
			},
		)
		if existing:
			continue

		notification = frappe.new_doc("Notification Log")
		notification.update({
			"for_user": user,
			"from_user": frappe.session.user,
			"type": alert_type,
			"document_type": document_type,
			"document_name": document_name,
			"subject": f"{subject} [ref:{ref_key}]",
		})
		notification.insert(ignore_permissions=True)
		sent += 1

	return sent


def _get_department_recipients(order: "frappe.Document") -> set[str]:
	"""Get users for the target department based on order type."""
	role_map = {
		"Medication": "Pharmacy User",
		"Lab Test": "Laboratory User",
		"Radiology": "Physician",
		"Procedure": "Physician",
	}
	role = role_map.get(order.order_type, "Healthcare Administrator")
	return _get_role_users(role)


def _get_role_users(role: str) -> set[str]:
	"""Return active users with the given role."""
	users = set()
	role_users = frappe.db.get_all(
		"Has Role",
		filters={"role": role, "parenttype": "User"},
		fields=["parent"],
	)
	users.update(u.parent for u in role_users)
	users.discard("Administrator")
	users.discard("Guest")
	return users


def notify_dispense_completed(order_name: str, dispense_name: str) -> None:
	"""Notify nursing and ordering practitioner that medication was dispensed."""
	order = frappe.get_doc("IPD Clinical Order", order_name)
	recipients = _get_role_users("Nursing User")

	if order.ordering_practitioner:
		practitioner_user = frappe.db.get_value(
			"Healthcare Practitioner", order.ordering_practitioner, "user_id"
		)
		if practitioner_user:
			recipients.add(practitioner_user)

	_send_notifications(
		recipients=recipients,
		subject=_("Medication dispensed: {0} for {1}").format(
			order.medication_name, order.patient_name
		),
		document_type="IPD Clinical Order",
		document_name=order.name,
		ref_key=f"dispensed:{order.name}:{dispense_name}",
	)

	frappe.publish_realtime(
		"ipd_order_notification",
		{
			"order": order.name,
			"event": "dispensed",
			"patient": order.patient,
			"medication": order.medication_name,
		},
	)


def notify_critical_result(
	order_name: str,
	sample_name: str,
	lab_test_name: str,
) -> None:
	"""Alert ordering practitioner and nursing about critical lab results."""
	order = frappe.get_doc("IPD Clinical Order", order_name)
	recipients = _get_role_users("Nursing User")

	if order.ordering_practitioner:
		practitioner_user = frappe.db.get_value(
			"Healthcare Practitioner", order.ordering_practitioner, "user_id"
		)
		if practitioner_user:
			recipients.add(practitioner_user)

	recipients |= _get_role_users("Physician")

	_send_notifications(
		recipients=recipients,
		subject=_("CRITICAL RESULT: {0} for {1} — immediate acknowledgment required").format(
			order.lab_test_name, order.patient_name
		),
		document_type="IPD Lab Sample",
		document_name=sample_name,
		ref_key=f"critical:{order.name}:{sample_name}",
		alert_type="Alert",
	)

	frappe.publish_realtime(
		"ipd_critical_result",
		{
			"order": order.name,
			"sample": sample_name,
			"lab_test": lab_test_name,
			"patient": order.patient,
			"test_name": order.lab_test_name,
		},
	)


def _order_detail_label(order: "frappe.Document") -> str:
	"""Return the primary detail label for the order (drug name, test name, etc.)."""
	if order.order_type == "Medication":
		return order.medication_name or ""
	if order.order_type == "Lab Test":
		return order.lab_test_name or ""
	return order.procedure_name or ""
