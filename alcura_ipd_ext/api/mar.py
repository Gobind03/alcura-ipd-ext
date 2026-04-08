"""Whitelisted API endpoints for MAR operations (US-G2)."""

from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import now_datetime


@frappe.whitelist()
def get_due_medications(
	inpatient_record: str,
	from_time: str | None = None,
	to_time: str | None = None,
) -> list[dict]:
	"""Return MAR entries due in a time window for a patient."""
	frappe.has_permission("IPD MAR Entry", "read", throw=True)

	from alcura_ipd_ext.services.mar_schedule_service import get_due_medications as _get

	return _get(inpatient_record, from_time, to_time)


@frappe.whitelist()
def get_ward_mar_board(
	ward: str,
	date: str | None = None,
	shift: str | None = None,
) -> dict:
	"""Return all patients' due meds for a ward/shift."""
	frappe.has_permission("IPD MAR Entry", "read", throw=True)

	from alcura_ipd_ext.services.mar_schedule_service import get_ward_mar_board as _board

	return _board(ward, date, shift)


@frappe.whitelist()
def get_shift_summary(ward: str, date: str | None = None, shift: str | None = None) -> dict:
	"""Return shift-level MAR summary for handoff."""
	frappe.has_permission("IPD MAR Entry", "read", throw=True)

	from alcura_ipd_ext.services.mar_schedule_service import get_shift_mar_summary as _summary

	return _summary(ward, date or str(frappe.utils.today()), shift or "Morning")


@frappe.whitelist()
def administer_medication(
	mar_entry: str,
	administration_status: str,
	hold_reason: str | None = None,
	refusal_reason: str | None = None,
	delay_reason: str | None = None,
	delay_minutes: int | None = None,
	site: str | None = None,
	witness: str | None = None,
	notes: str | None = None,
) -> dict:
	"""Record a medication administration action."""
	frappe.has_permission("IPD MAR Entry", "write", doc=mar_entry, throw=True)

	doc = frappe.get_doc("IPD MAR Entry", mar_entry)

	if doc.administration_status not in ("Scheduled", "Delayed"):
		frappe.throw(_("This entry has already been actioned ({0}).").format(doc.administration_status))

	valid_statuses = ("Given", "Held", "Refused", "Delayed", "Self-Administered")
	if administration_status not in valid_statuses:
		frappe.throw(_("Invalid administration status: {0}").format(administration_status))

	doc.administration_status = administration_status

	if administration_status in ("Given", "Self-Administered"):
		doc.administered_at = now_datetime()
		doc.administered_by = frappe.session.user
		if site:
			doc.site = site
		if witness:
			doc.witness = witness

	if administration_status == "Held":
		if not hold_reason:
			frappe.throw(_("Hold reason is required."))
		doc.hold_reason = hold_reason

	if administration_status == "Refused":
		if not refusal_reason:
			frappe.throw(_("Refusal reason is required."))
		doc.refusal_reason = refusal_reason

	if administration_status == "Delayed":
		if not delay_reason:
			frappe.throw(_("Delay reason is required."))
		doc.delay_reason = delay_reason
		if delay_minutes:
			doc.delay_minutes = int(delay_minutes)

	if notes:
		doc.notes = notes

	doc.save(ignore_permissions=True)

	return {"name": doc.name, "administration_status": doc.administration_status}


@frappe.whitelist()
def create_prn_mar_entry(order_name: str) -> dict:
	"""Create an on-demand MAR entry for a PRN medication order."""
	frappe.has_permission("IPD MAR Entry", "create", throw=True)

	order = frappe.get_doc("IPD Clinical Order", order_name)

	if order.order_type != "Medication":
		frappe.throw(_("PRN entries can only be created for Medication orders."))

	if not order.is_prn and order.frequency != "PRN":
		frappe.throw(_("This order is not a PRN order."))

	entry = frappe.get_doc({
		"doctype": "IPD MAR Entry",
		"patient": order.patient,
		"inpatient_record": order.inpatient_record,
		"medication_name": order.medication_name,
		"medication_item": order.medication_item,
		"dose": order.dose,
		"dose_uom": order.dose_uom,
		"route": order.route,
		"scheduled_time": now_datetime(),
		"administration_status": "Scheduled",
		"clinical_order": order.name,
	})
	entry.insert(ignore_permissions=True)

	return {"name": entry.name}


@frappe.whitelist()
def generate_daily_entries(inpatient_record: str, date: str | None = None) -> dict:
	"""Generate MAR entries for all active medication orders for a patient."""
	frappe.has_permission("IPD MAR Entry", "create", throw=True)

	from alcura_ipd_ext.services.mar_schedule_service import generate_daily_mar_entries

	created = generate_daily_mar_entries(inpatient_record, date)
	return {"created": len(created), "entries": created}
