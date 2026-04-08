"""Scheduled background tasks for Alcura IPD Extensions."""

from __future__ import annotations

import frappe
from frappe.utils import add_days, today

from alcura_ipd_ext.services.bed_reservation_service import expire_overdue_reservations

# ── US-E4: Overdue charts grace period (minutes) before alerting ────
_OVERDUE_GRACE_MINUTES = 15


def expire_bed_reservations():
	"""Expire overdue bed reservations. Runs via scheduler every 5 minutes."""
	count = expire_overdue_reservations()
	if count:
		frappe.logger("alcura_ipd_ext").info(
			f"Expired {count} overdue bed reservation(s)."
		)


def notify_expiring_payer_profiles():
	"""Send in-app notifications for payer profiles expiring within 7 days.

	Runs daily. Targets users with the TPA Desk User or Healthcare Administrator role.
	"""
	expiry_horizon = add_days(today(), 7)

	expiring = frappe.db.get_all(
		"Patient Payer Profile",
		filters={
			"is_active": 1,
			"valid_to": ("<=", expiry_horizon),
			"valid_to": (">=", today()),
		},
		fields=["name", "patient", "patient_name", "payer_type", "valid_to"],
	)

	if not expiring:
		return

	recipients = _get_notification_recipients()
	if not recipients:
		return

	for profile in expiring:
		for user in recipients:
			notification = frappe.new_doc("Notification Log")
			notification.update(
				{
					"for_user": user,
					"from_user": frappe.session.user,
					"type": "Alert",
					"document_type": "Patient Payer Profile",
					"document_name": profile.name,
					"subject": (
						f"Payer profile {profile.name} for {profile.patient_name} "
						f"({profile.payer_type}) expires on {profile.valid_to}"
					),
				}
			)
			notification.insert(ignore_permissions=True)

	frappe.logger("alcura_ipd_ext").info(
		f"Sent expiry notifications for {len(expiring)} payer profile(s)."
	)


def check_overdue_charts():
	"""Send in-app notifications for charts that are overdue beyond the grace period.

	Runs via scheduler every 15 minutes. Classifies severity by how many
	intervals have been missed and updates the missed_count on each chart.
	ICU charts (frequency <= 60 min) use a 5-minute grace; others use the default.
	"""
	from alcura_ipd_ext.services.charting_service import get_overdue_charts
	from alcura_ipd_ext.services.observation_trend_service import classify_overdue_severity

	overdue = get_overdue_charts(grace_minutes=0)
	if not overdue:
		return

	recipients = _get_nursing_recipients()

	sent = 0
	for chart in overdue:
		freq = chart.get("frequency_minutes") or 60
		grace = 5 if freq <= 60 else _OVERDUE_GRACE_MINUTES
		if chart["overdue_minutes"] < grace:
			continue

		severity = classify_overdue_severity(chart["overdue_minutes"], freq)
		severity_prefix = severity.upper() if severity else "OVERDUE"

		_update_missed_count(chart["name"])

		if not recipients:
			continue

		for user in recipients:
			existing = frappe.db.exists(
				"Notification Log",
				{
					"for_user": user,
					"document_type": "IPD Bedside Chart",
					"document_name": chart["name"],
					"read": 0,
				},
			)
			if existing:
				continue

			notification = frappe.new_doc("Notification Log")
			notification.update({
				"for_user": user,
				"from_user": frappe.session.user,
				"type": "Alert",
				"document_type": "IPD Bedside Chart",
				"document_name": chart["name"],
				"subject": (
					f"{severity_prefix}: {chart['chart_type']} chart for "
					f"{chart['patient_name']} — {chart['overdue_minutes']} min overdue"
				),
			})
			notification.insert(ignore_permissions=True)
			sent += 1

	if sent:
		frappe.logger("alcura_ipd_ext").info(
			f"Sent {sent} overdue chart notification(s) for {len(overdue)} chart(s)."
		)


def _update_missed_count(chart_name: str) -> None:
	"""Increment the missed observation count on a bedside chart."""
	current = frappe.db.get_value("IPD Bedside Chart", chart_name, "missed_count") or 0
	frappe.db.set_value(
		"IPD Bedside Chart",
		chart_name,
		"missed_count",
		current + 1,
		update_modified=False,
	)


def check_order_sla_breaches():
	"""Check for clinical orders that have breached their SLA targets.

	Runs via scheduler every 5 minutes. Marks breached orders and sends
	escalation notifications to configured roles.
	"""
	from alcura_ipd_ext.services.order_sla_service import check_breaches

	count = check_breaches()
	if count:
		frappe.logger("alcura_ipd_ext").info(
			f"Detected {count} SLA breach(es) in clinical orders."
		)


def mark_overdue_mar_entries():
	"""Mark past-due Scheduled MAR entries as Missed. Runs every 15 minutes."""
	from alcura_ipd_ext.services.mar_schedule_service import mark_overdue_scheduled_entries

	count = mark_overdue_scheduled_entries()
	if count:
		frappe.logger("alcura_ipd_ext").info(
			f"Marked {count} MAR entr(ies) as Missed."
		)


def check_protocol_compliance():
	"""Check all active protocol bundles for overdue steps.

	Runs via scheduler every 15 minutes. Marks overdue steps as Missed,
	recomputes compliance scores, and sends notifications.
	"""
	from alcura_ipd_ext.services.protocol_bundle_service import check_all_active_bundles

	count = check_all_active_bundles()
	if count:
		frappe.logger("alcura_ipd_ext").info(
			f"Marked {count} protocol step(s) as Missed."
		)


def _get_nursing_recipients() -> list[str]:
	"""Return users with Nursing User role for overdue chart notifications."""
	users = set()
	role_users = frappe.db.get_all(
		"Has Role",
		filters={"role": "Nursing User", "parenttype": "User"},
		fields=["parent"],
	)
	users.update(u.parent for u in role_users)
	users.discard("Administrator")
	users.discard("Guest")
	return list(users)


def _get_notification_recipients() -> list[str]:
	"""Return users with TPA Desk User or Healthcare Administrator roles."""
	users = set()
	for role in ("TPA Desk User", "Healthcare Administrator"):
		role_users = frappe.db.get_all(
			"Has Role",
			filters={"role": role, "parenttype": "User"},
			fields=["parent"],
		)
		users.update(u.parent for u in role_users)

	users.discard("Administrator")
	users.discard("Guest")
	return list(users)
