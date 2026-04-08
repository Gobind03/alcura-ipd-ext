"""Notification service for discharge journey events.

Sends in-app notifications and realtime events to downstream departments
when discharge advice is raised, acknowledged, or completed.
"""

from __future__ import annotations

import frappe
from frappe import _


def notify_discharge_advised(advice: "frappe.Document") -> None:
	"""Notify all relevant departments that discharge has been advised."""
	subject = _("Discharge advised for {0} ({1}) — Expected: {2}").format(
		advice.patient_name,
		advice.inpatient_record,
		frappe.utils.format_datetime(advice.expected_discharge_datetime)
		if advice.expected_discharge_datetime else _("Not specified"),
	)

	recipients = set()
	recipients |= _get_role_users("Nursing User")
	recipients |= _get_role_users("IPD Billing User")
	recipients |= _get_role_users("Pharmacy User")

	payer_type = frappe.db.get_value(
		"Inpatient Record", advice.inpatient_record, "custom_payer_type"
	)
	if payer_type and payer_type != "Cash":
		recipients |= _get_role_users("TPA Desk User")

	_send_notifications(
		recipients=recipients,
		subject=subject,
		document_type="IPD Discharge Advice",
		document_name=advice.name,
		ref_key=f"discharge_advised:{advice.name}",
	)

	frappe.publish_realtime(
		"ipd_discharge_notification",
		{
			"action": "advised",
			"advice": advice.name,
			"patient": advice.patient,
			"patient_name": advice.patient_name,
			"inpatient_record": advice.inpatient_record,
			"expected_discharge_datetime": str(advice.expected_discharge_datetime)
			if advice.expected_discharge_datetime else None,
			"ward": frappe.db.get_value(
				"Inpatient Record", advice.inpatient_record, "custom_current_ward"
			),
		},
	)


def notify_discharge_acknowledged(advice: "frappe.Document") -> None:
	"""Notify the advising consultant that discharge was acknowledged."""
	if not advice.consultant:
		return

	practitioner_user = frappe.db.get_value(
		"Healthcare Practitioner", advice.consultant, "user_id"
	)
	if not practitioner_user:
		return

	_send_notifications(
		recipients={practitioner_user},
		subject=_("Discharge acknowledged for {0} ({1})").format(
			advice.patient_name, advice.inpatient_record
		),
		document_type="IPD Discharge Advice",
		document_name=advice.name,
		ref_key=f"discharge_ack:{advice.name}",
	)


def notify_bed_vacated(
	inpatient_record: str,
	patient_name: str,
	ward: str,
	bed: str,
) -> None:
	"""Notify admission officers and nursing that a bed has been vacated."""
	recipients = _get_role_users("IPD Admission Officer")
	recipients |= _get_role_users("Nursing User")

	_send_notifications(
		recipients=recipients,
		subject=_("Bed {0} vacated in ward {1} — patient {2} discharged").format(
			bed, ward, patient_name
		),
		document_type="Inpatient Record",
		document_name=inpatient_record,
		ref_key=f"bed_vacated:{inpatient_record}:{bed}",
	)

	frappe.publish_realtime(
		"ipd_discharge_notification",
		{
			"action": "bed_vacated",
			"inpatient_record": inpatient_record,
			"bed": bed,
			"ward": ward,
		},
	)


def notify_housekeeping_sla_breach(task_name: str, bed: str, ward: str) -> None:
	"""Notify administrators about a housekeeping SLA breach."""
	recipients = _get_role_users("Healthcare Administrator")
	recipients |= _get_role_users("Nursing User")

	_send_notifications(
		recipients=recipients,
		subject=_("HOUSEKEEPING SLA BREACH: Bed {0} (Ward {1}) — cleaning overdue").format(
			bed, ward
		),
		document_type="Bed Housekeeping Task",
		document_name=task_name,
		ref_key=f"hk_sla_breach:{task_name}",
		alert_type="Alert",
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
