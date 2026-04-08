"""Interim bill generation service for IPD stays.

Aggregates charges from clinical orders, room tariffs, and applies
payer billing rules to produce a snapshot of the current financial
position during an active admission.
"""

from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import date_diff, flt, getdate, now_datetime, today

from alcura_ipd_ext.services.billing_rule_service import compute_bill_split


def generate_interim_bill(
	inpatient_record: str,
	as_of_date: str | None = None,
) -> dict:
	"""Build a complete interim bill snapshot.

	Returns dict with:
	- patient_info: basic patient and admission details
	- room_charges: list of room charge line items
	- clinical_charges: list of clinical order charge line items
	- bill_summary: aggregated totals with payer splits
	- deposits: advance payments / deposits
	- balance_due: net amount after deposits
	- pending_items: unbilled or incomplete orders
	- generated_at: timestamp of generation
	"""
	as_of = getdate(as_of_date or today())

	ir = frappe.get_doc("Inpatient Record", inpatient_record)
	patient_info = _get_patient_info(ir)
	payer_profile = ir.get("custom_patient_payer_profile")
	preauth_name = ir.get("custom_preauth_request")

	room_charges = _compute_room_charges(ir, as_of)
	clinical_charges = _get_clinical_order_charges(ir.name)
	pending_items = _get_pending_items(ir.name)

	all_line_items = room_charges + clinical_charges

	if payer_profile and payer_profile != "Cash":
		bill_split = compute_bill_split(
			line_items=all_line_items,
			patient_payer_profile=payer_profile,
			company=ir.company,
			preauth_name=preauth_name,
		)
	else:
		bill_split = _cash_split(all_line_items)

	deposits = _get_deposits(ir)
	gross_total = flt(bill_split.get("gross_total", 0))
	patient_total = flt(bill_split.get("patient_total", 0))
	deposit_total = flt(deposits.get("total", 0))

	return {
		"patient_info": patient_info,
		"room_charges": room_charges,
		"clinical_charges": clinical_charges,
		"bill_summary": bill_split,
		"deposits": deposits,
		"balance_due": max(0, (patient_total or gross_total) - deposit_total),
		"pending_items": pending_items,
		"generated_at": str(now_datetime()),
	}


def _get_patient_info(ir) -> dict:
	return {
		"patient": ir.patient,
		"patient_name": ir.patient_name,
		"inpatient_record": ir.name,
		"admission_date": str(ir.get("scheduled_date") or ir.get("admitted_datetime") or ""),
		"ward": ir.get("custom_current_ward") or "",
		"room": ir.get("custom_current_room") or "",
		"bed": ir.get("custom_current_bed") or "",
		"payer_type": ir.get("custom_payer_type") or "Cash",
		"payer_profile": ir.get("custom_patient_payer_profile") or "",
		"company": ir.company,
	}


def _compute_room_charges(ir, as_of_date) -> list[dict]:
	"""Compute room charges from bed movement log entries."""
	movements = frappe.db.get_all(
		"Bed Movement Log",
		filters={
			"inpatient_record": ir.name,
			"movement_type": ("in", ("Admission", "Transfer")),
		},
		fields=["name", "to_bed", "to_room", "to_ward", "movement_datetime"],
		order_by="movement_datetime asc",
	)

	if not movements:
		return []

	charges = []
	for i, movement in enumerate(movements):
		start_date = getdate(movement.movement_datetime)
		if i + 1 < len(movements):
			end_date = getdate(movements[i + 1].movement_datetime)
		else:
			end_date = as_of_date

		days = max(1, date_diff(end_date, start_date))

		room_type = None
		if movement.to_room:
			room_type = frappe.db.get_value("Hospital Room", movement.to_room, "room_type")

		if room_type:
			from alcura_ipd_ext.services.tariff_service import get_tariff_rate

			payer_profile = ir.get("custom_patient_payer_profile")
			payer_type = "Cash"
			payer = None
			if payer_profile:
				profile_data = frappe.db.get_value(
					"Patient Payer Profile", payer_profile,
					["payer_type", "payer"], as_dict=True,
				)
				if profile_data:
					payer_type = profile_data.payer_type
					payer = profile_data.payer

			daily_rate = get_tariff_rate(
				room_type=room_type,
				charge_type="Room Rent",
				payer_type=payer_type,
				payer=payer,
				effective_date=str(start_date),
				company=ir.company,
			)

			if daily_rate:
				charges.append({
					"item_code": None,
					"item_group": None,
					"charge_category": "Room Rent",
					"description": f"Room Rent — {movement.to_room or movement.to_ward}",
					"qty": days,
					"rate": daily_rate,
					"gross_amount": daily_rate * days,
				})

	return charges


def _get_clinical_order_charges(inpatient_record: str) -> list[dict]:
	"""Get charges from completed/in-progress clinical orders."""
	orders = frappe.db.get_all(
		"IPD Clinical Order",
		filters={
			"inpatient_record": inpatient_record,
			"status": ("in", ("Completed", "In Progress", "Acknowledged", "Ordered")),
		},
		fields=[
			"name", "order_type", "medication_item", "medication_name",
			"lab_test_name", "procedure_name", "dose", "ordered_qty",
			"status",
		],
	)

	charges = []
	category_map = {
		"Medication": "Pharmacy",
		"Lab Test": "Investigation",
		"Radiology": "Investigation",
		"Procedure": "Procedure",
	}

	for order in orders:
		item_code = order.medication_item or None
		description = (
			order.medication_name or order.lab_test_name
			or order.procedure_name or order.order_type
		)
		charge_category = category_map.get(order.order_type, "Other")

		rate = 0
		qty = flt(order.ordered_qty) or 1
		if item_code:
			rate = _get_item_rate(item_code)

		if rate:
			charges.append({
				"item_code": item_code,
				"item_group": _get_item_group(item_code) if item_code else None,
				"charge_category": charge_category,
				"description": description,
				"qty": qty,
				"rate": rate,
				"gross_amount": rate * qty,
				"order_ref": order.name,
				"order_status": order.status,
			})

	return charges


def _get_pending_items(inpatient_record: str) -> list[dict]:
	"""Get orders that are not yet completed or billed."""
	return frappe.db.get_all(
		"IPD Clinical Order",
		filters={
			"inpatient_record": inpatient_record,
			"status": ("in", ("Draft", "Ordered", "Acknowledged", "In Progress", "On Hold")),
		},
		fields=["name", "order_type", "medication_name", "lab_test_name",
				"procedure_name", "status", "urgency"],
		order_by="creation desc",
	)


def _get_deposits(ir) -> dict:
	"""Get advance payments from Payment Entry and Sales Invoice."""
	patient_customer = frappe.db.get_value("Patient", ir.patient, "customer")
	if not patient_customer:
		return {"total": 0, "entries": []}

	advances = frappe.db.get_all(
		"Payment Entry",
		filters={
			"party_type": "Customer",
			"party": patient_customer,
			"company": ir.company,
			"docstatus": 1,
			"payment_type": "Receive",
		},
		fields=["name", "paid_amount", "posting_date", "mode_of_payment"],
		order_by="posting_date desc",
	)

	total = sum(flt(a.paid_amount) for a in advances)
	return {
		"total": total,
		"entries": advances,
	}


def _cash_split(line_items: list[dict]) -> dict:
	"""Simple split for cash patients — everything is patient liability."""
	gross_total = sum(flt(item.get("gross_amount", 0)) for item in line_items)
	lines = []
	for item in line_items:
		amt = flt(item.get("gross_amount", 0))
		lines.append({
			**item,
			"payer_amount": 0,
			"patient_amount": amt,
			"excluded_amount": 0,
			"rule_applied": "Cash",
		})
	return {
		"lines": lines,
		"gross_total": gross_total,
		"payer_total": 0,
		"patient_total": gross_total,
		"excluded_total": 0,
		"deductible_applied": 0,
		"preauth_approved_amount": 0,
		"preauth_overshoot": 0,
	}


def _get_item_rate(item_code: str) -> float:
	"""Get standard selling rate for an item."""
	rate = frappe.db.get_value("Item Price", {
		"item_code": item_code,
		"selling": 1,
	}, "price_list_rate")
	return flt(rate)


def _get_item_group(item_code: str) -> str | None:
	return frappe.db.get_value("Item", item_code, "item_group")
