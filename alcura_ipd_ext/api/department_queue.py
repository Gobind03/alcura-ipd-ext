"""Department queue data endpoints for Pharmacy, Lab, and Nurse Station queues."""

from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import now_datetime, time_diff_in_seconds


_QUEUE_FIELDS = [
	"name", "patient", "patient_name", "inpatient_record",
	"order_type", "urgency", "status",
	"ward", "room", "bed",
	"ordering_practitioner_name", "ordering_department",
	"ordered_at", "acknowledged_at",
	"current_sla_target_at", "is_sla_breached", "sla_breach_count",
	"medication_name", "medication_item", "dose", "route", "frequency", "is_stat", "is_prn",
	"dispense_status", "total_dispensed_qty", "substitution_status",
	"lab_test_name", "sample_type", "is_fasting_required",
	"procedure_name", "is_bedside",
	"clinical_notes",
]

_ACTIONABLE_STATUSES = ("Ordered", "Acknowledged", "In Progress")


@frappe.whitelist()
def get_pharmacy_queue(
	ward: str | None = None,
	consultant: str | None = None,
	urgency: str | None = None,
	status: str | None = None,
) -> list[dict]:
	"""Return medication orders in actionable states for the pharmacy queue."""
	frappe.has_permission("IPD Clinical Order", "read", throw=True)

	filters = {"order_type": "Medication"}
	_apply_common_filters(filters, ward, consultant, urgency, status)

	orders = frappe.get_all(
		"IPD Clinical Order",
		filters=filters,
		fields=_QUEUE_FIELDS,
		order_by="FIELD(urgency, 'Emergency', 'STAT', 'Urgent', 'Routine'), ordered_at ASC",
		limit_page_length=200,
	)
	return _enrich_with_sla(orders)


@frappe.whitelist()
def get_lab_queue(
	ward: str | None = None,
	consultant: str | None = None,
	urgency: str | None = None,
	status: str | None = None,
) -> list[dict]:
	"""Return lab test orders in actionable states for the lab queue."""
	frappe.has_permission("IPD Clinical Order", "read", throw=True)

	filters = {"order_type": "Lab Test"}
	_apply_common_filters(filters, ward, consultant, urgency, status)

	orders = frappe.get_all(
		"IPD Clinical Order",
		filters=filters,
		fields=_QUEUE_FIELDS,
		order_by="FIELD(urgency, 'Emergency', 'STAT', 'Urgent', 'Routine'), ordered_at ASC",
		limit_page_length=200,
	)
	return _enrich_with_sla(orders)


@frappe.whitelist()
def get_nurse_station_queue(
	ward: str | None = None,
	status: str | None = None,
) -> list[dict]:
	"""Return all order types for the nurse station, grouped by patient/bed."""
	frappe.has_permission("IPD Clinical Order", "read", throw=True)

	filters = {}
	if ward:
		filters["ward"] = ward
	if status:
		filters["status"] = status
	else:
		filters["status"] = ("in", _ACTIONABLE_STATUSES)

	orders = frappe.get_all(
		"IPD Clinical Order",
		filters=filters,
		fields=_QUEUE_FIELDS,
		order_by="FIELD(urgency, 'Emergency', 'STAT', 'Urgent', 'Routine'), ordered_at ASC",
		limit_page_length=300,
	)
	return _enrich_with_sla(orders)


# ── Private helpers ──────────────────────────────────────────────────


def _apply_common_filters(
	filters: dict,
	ward: str | None,
	consultant: str | None,
	urgency: str | None,
	status: str | None,
) -> None:
	if ward:
		filters["ward"] = ward
	if consultant:
		filters["ordering_practitioner"] = consultant
	if urgency:
		filters["urgency"] = urgency
	if status:
		filters["status"] = status
	else:
		filters["status"] = ("in", _ACTIONABLE_STATUSES)


def _enrich_with_sla(orders: list[dict]) -> list[dict]:
	"""Add computed SLA fields: elapsed_minutes, sla_remaining_minutes, sla_color."""
	now = now_datetime()
	for order in orders:
		ordered_at = order.get("ordered_at")
		if ordered_at:
			elapsed = time_diff_in_seconds(now, ordered_at) / 60
			order["elapsed_minutes"] = round(elapsed, 1)
		else:
			order["elapsed_minutes"] = 0

		target = order.get("current_sla_target_at")
		if target:
			remaining = time_diff_in_seconds(target, now) / 60
			order["sla_remaining_minutes"] = round(remaining, 1)

			if order.get("is_sla_breached"):
				order["sla_color"] = "red"
			elif remaining <= 0:
				order["sla_color"] = "red"
			elif remaining <= target_threshold(order, 0.2):
				order["sla_color"] = "orange"
			elif remaining <= target_threshold(order, 0.5):
				order["sla_color"] = "yellow"
			else:
				order["sla_color"] = "green"
		else:
			order["sla_remaining_minutes"] = None
			order["sla_color"] = "grey"

	return orders


def target_threshold(order: dict, fraction: float) -> float:
	"""Calculate remaining minutes at a fraction of total SLA window."""
	ordered_at = order.get("ordered_at")
	target = order.get("current_sla_target_at")
	if not ordered_at or not target:
		return 0
	total = time_diff_in_seconds(target, ordered_at) / 60
	return total * fraction
