"""SLA initialization, milestone advancement, and breach detection for clinical orders."""

from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import add_to_date, now_datetime


def initialize_sla(order: "frappe.Document") -> None:
	"""Look up SLA config for the order's type+urgency and create milestone targets."""
	config_name = frappe.db.get_value(
		"IPD Order SLA Config",
		{"order_type": order.order_type, "urgency": order.urgency, "is_active": 1},
	)
	if not config_name:
		return

	config = frappe.get_doc("IPD Order SLA Config", config_name)
	base_time = order.ordered_at or now_datetime()

	first_target = None
	for target in sorted(config.milestones, key=lambda m: m.sequence or 0):
		target_at = add_to_date(base_time, minutes=target.target_minutes)
		order.append("sla_milestones", {
			"milestone": target.milestone,
			"target_at": target_at,
		})
		if first_target is None:
			first_target = target_at

	if first_target:
		order.current_sla_target_at = first_target

	order.save(ignore_permissions=True)


def advance_sla(order: "frappe.Document", completed_milestone: str) -> None:
	"""After a milestone is met, advance current_sla_target_at to the next pending one."""
	next_target = None
	for row in sorted(order.sla_milestones, key=lambda m: m.idx):
		if not row.actual_at and row.target_at:
			next_target = row.target_at
			break

	order.current_sla_target_at = next_target
	order.save(ignore_permissions=True)


def check_breaches() -> int:
	"""Find orders past their SLA target and mark as breached.

	Called by the scheduler. Returns count of newly breached orders.
	"""
	now = now_datetime()
	terminal = ("Completed", "Cancelled")

	breached_orders = frappe.db.get_all(
		"IPD Clinical Order",
		filters={
			"current_sla_target_at": ("<=", now),
			"status": ("not in", terminal),
			"is_sla_breached": 0,
			"current_sla_target_at": ("is", "set"),
		},
		fields=["name"],
		limit_page_length=200,
	)

	count = 0
	for row in breached_orders:
		doc = frappe.get_doc("IPD Clinical Order", row.name)
		_mark_breached(doc, now)
		count += 1

	if count:
		frappe.db.commit()

	return count


def get_sla_summary(order_name: str) -> list[dict]:
	"""Return milestone list with breach info for a single order."""
	doc = frappe.get_doc("IPD Clinical Order", order_name)
	result = []
	for row in doc.sla_milestones:
		result.append({
			"milestone": row.milestone,
			"target_at": row.target_at,
			"actual_at": row.actual_at,
			"is_breached": row.is_breached,
			"recorded_by": row.recorded_by,
		})
	return result


def get_breach_report(
	from_date: str | None = None,
	to_date: str | None = None,
	order_type: str | None = None,
	urgency: str | None = None,
	ward: str | None = None,
) -> list[dict]:
	"""Return breached orders with details for the SLA Breach Report."""
	filters = {"is_sla_breached": 1}
	if from_date:
		filters["ordered_at"] = (">=", from_date)
	if to_date:
		filters.setdefault("ordered_at", ("<=", to_date))
	if order_type:
		filters["order_type"] = order_type
	if urgency:
		filters["urgency"] = urgency
	if ward:
		filters["ward"] = ward

	return frappe.get_all(
		"IPD Clinical Order",
		filters=filters,
		fields=[
			"name", "patient", "patient_name", "order_type", "urgency", "status",
			"ward", "ordering_practitioner_name",
			"ordered_at", "acknowledged_at", "completed_at",
			"current_sla_target_at", "sla_breach_count",
		],
		order_by="ordered_at desc",
		limit_page_length=500,
	)


# ── Private helpers ──────────────────────────────────────────────────


def _mark_breached(doc: "frappe.Document", now) -> None:
	"""Mark milestone rows as breached and update order-level breach fields."""
	for row in doc.sla_milestones:
		if row.target_at and not row.actual_at and row.target_at <= now:
			row.is_breached = 1

	doc.is_sla_breached = 1
	doc.sla_breach_count = (doc.sla_breach_count or 0) + 1

	# Advance to next un-breached target
	next_target = None
	for row in sorted(doc.sla_milestones, key=lambda m: m.idx):
		if not row.actual_at and row.target_at and row.target_at > now:
			next_target = row.target_at
			break

	doc.current_sla_target_at = next_target
	doc.save(ignore_permissions=True)

	# Fire escalation
	_escalate_breach(doc)


def _escalate_breach(doc: "frappe.Document") -> None:
	"""Look up escalation role for breached milestones and send notifications."""
	config_name = frappe.db.get_value(
		"IPD Order SLA Config",
		{"order_type": doc.order_type, "urgency": doc.urgency, "is_active": 1},
	)
	if not config_name:
		return

	config = frappe.get_doc("IPD Order SLA Config", config_name)

	for milestone_row in doc.sla_milestones:
		if not milestone_row.is_breached or milestone_row.actual_at:
			continue

		# Find the matching config target
		for target in config.milestones:
			if target.milestone == milestone_row.milestone and target.escalation_role:
				from alcura_ipd_ext.services.order_notification_service import notify_sla_breach

				notify_sla_breach(doc, milestone_row.milestone, target.escalation_role)
				break
