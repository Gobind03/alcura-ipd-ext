"""Discharge billing checklist service.

Provides domain logic for creating discharge checklists with standard
items, auto-deriving check statuses from live data, and validating
discharge readiness.
"""

from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import now_datetime

from alcura_ipd_ext.utils.constants import ORDER_ACTIVE_STATUSES

# Standard checklist items applied to every discharge
_STANDARD_CHECKS: list[dict] = [
	{
		"check_name": "Pending Medication Orders",
		"check_category": "Clinical",
		"auto_derived": 1,
	},
	{
		"check_name": "Pending Lab Samples",
		"check_category": "Clinical",
		"auto_derived": 1,
	},
	{
		"check_name": "Unposted Procedures",
		"check_category": "Clinical",
		"auto_derived": 1,
	},
	{
		"check_name": "Room Rent Closed",
		"check_category": "Financial",
		"auto_derived": 1,
	},
	{
		"check_name": "Final Consultant Visit",
		"check_category": "Clinical",
		"auto_derived": 0,
	},
	{
		"check_name": "Discharge Summary Signed",
		"check_category": "Clinical",
		"auto_derived": 1,
	},
	{
		"check_name": "TPA Preauth Status",
		"check_category": "TPA",
		"auto_derived": 1,
	},
	{
		"check_name": "Deposit Adjustment",
		"check_category": "Financial",
		"auto_derived": 0,
	},
]


@frappe.whitelist()
def create_discharge_checklist(inpatient_record: str) -> str:
	"""Create a Discharge Billing Checklist with standard items.

	Returns the name of the created checklist. Raises if one already exists.
	"""
	if frappe.db.exists("Discharge Billing Checklist", {"inpatient_record": inpatient_record}):
		frappe.throw(
			_("A discharge checklist already exists for {0}").format(inpatient_record),
			title=_("Duplicate Checklist"),
		)

	ir = frappe.get_doc("Inpatient Record", inpatient_record)

	doc = frappe.new_doc("Discharge Billing Checklist")
	doc.update({
		"inpatient_record": inpatient_record,
		"patient": ir.patient,
		"company": ir.company,
	})

	payer_type = ir.get("custom_payer_type") or "Cash"
	for check_def in _STANDARD_CHECKS:
		# Skip TPA check for cash patients
		if check_def["check_name"] == "TPA Preauth Status" and payer_type == "Cash":
			continue
		doc.append("items", {
			**check_def,
			"check_status": "Pending",
		})

	doc.insert(ignore_permissions=True)

	# Run initial auto-check
	refresh_auto_checks(doc.name)

	# Link to IR
	frappe.db.set_value(
		"Inpatient Record", inpatient_record,
		"custom_discharge_checklist", doc.name,
		update_modified=False,
	)

	return doc.name


def refresh_auto_checks(checklist_name: str):
	"""Re-evaluate auto-derived checklist items from live data."""
	doc = frappe.get_doc("Discharge Billing Checklist", checklist_name)
	ir_name = doc.inpatient_record

	check_functions = {
		"Pending Medication Orders": _check_pending_meds,
		"Pending Lab Samples": _check_pending_samples,
		"Unposted Procedures": _check_unposted_procedures,
		"Room Rent Closed": _check_room_rent_closed,
		"Discharge Summary Signed": _check_discharge_summary,
		"TPA Preauth Status": _check_tpa_preauth,
	}

	for row in doc.items:
		if not row.auto_derived:
			continue
		if row.check_status in ("Waived", "Not Applicable"):
			continue

		check_fn = check_functions.get(row.check_name)
		if check_fn:
			is_clear, detail = check_fn(ir_name)
			row.detail = detail
			if is_clear:
				row.check_status = "Cleared"
				if not row.cleared_by:
					row.cleared_by = "System"
					row.cleared_on = now_datetime()
			else:
				row.check_status = "Pending"

	doc.save(ignore_permissions=True)


def validate_discharge_ready(inpatient_record: str) -> dict:
	"""Check whether all mandatory checks are cleared or overridden.

	Returns dict with:
	- ready (bool)
	- status (str)
	- pending_items (list)
	- checklist_name (str|None)
	"""
	checklist_name = frappe.db.get_value(
		"Discharge Billing Checklist",
		{"inpatient_record": inpatient_record},
		"name",
	)

	if not checklist_name:
		return {
			"ready": False,
			"status": "No Checklist",
			"pending_items": [],
			"checklist_name": None,
			"message": _("No discharge checklist found. Create one first."),
		}

	doc = frappe.get_doc("Discharge Billing Checklist", checklist_name)

	if doc.status in ("Cleared", "Overridden"):
		return {
			"ready": True,
			"status": doc.status,
			"pending_items": [],
			"checklist_name": checklist_name,
			"message": _("Discharge checklist is {0}").format(doc.status),
		}

	pending = [
		{"check_name": r.check_name, "category": r.check_category, "detail": r.detail}
		for r in doc.items
		if r.check_status == "Pending"
	]

	return {
		"ready": False,
		"status": doc.status,
		"pending_items": pending,
		"checklist_name": checklist_name,
		"message": _("{0} pending item(s) on discharge checklist").format(len(pending)),
	}


# ── Auto-check functions ───────────────────────────────────────────


def _check_pending_meds(ir_name: str) -> tuple[bool, str]:
	count = frappe.db.count(
		"IPD Clinical Order",
		filters={
			"inpatient_record": ir_name,
			"order_type": "Medication",
			"status": ("in", ORDER_ACTIVE_STATUSES),
		},
	)
	if count:
		return False, f"{count} active medication order(s)"
	return True, "No pending medication orders"


def _check_pending_samples(ir_name: str) -> tuple[bool, str]:
	count = frappe.db.count(
		"IPD Lab Sample",
		filters={
			"inpatient_record": ir_name,
			"status": ("not in", ("Completed", "Cancelled", "Rejected")),
		},
	)
	if count:
		return False, f"{count} pending lab sample(s)"
	return True, "No pending lab samples"


def _check_unposted_procedures(ir_name: str) -> tuple[bool, str]:
	count = frappe.db.count(
		"IPD Clinical Order",
		filters={
			"inpatient_record": ir_name,
			"order_type": ("in", ("Procedure", "Radiology")),
			"status": ("in", ORDER_ACTIVE_STATUSES),
		},
	)
	if count:
		return False, f"{count} unposted procedure/radiology order(s)"
	return True, "No unposted procedures"


def _check_room_rent_closed(ir_name: str) -> tuple[bool, str]:
	has_discharge_movement = frappe.db.exists(
		"Bed Movement Log",
		{"inpatient_record": ir_name, "movement_type": "Discharge"},
	)
	if has_discharge_movement:
		return True, "Discharge movement recorded"
	return False, "No discharge movement logged"


def _check_discharge_summary(ir_name: str) -> tuple[bool, str]:
	patient = frappe.db.get_value("Inpatient Record", ir_name, "patient")
	if not patient:
		return False, "Patient not found"

	has_summary = frappe.db.exists(
		"Patient Encounter",
		{
			"patient": patient,
			"custom_linked_inpatient_record": ir_name,
			"custom_ipd_note_type": "Discharge Summary",
			"docstatus": 1,
		},
	)
	if has_summary:
		return True, "Discharge summary submitted"
	return False, "Discharge summary not found or not submitted"


def _check_tpa_preauth(ir_name: str) -> tuple[bool, str]:
	preauth = frappe.db.get_value(
		"TPA Preauth Request",
		{"inpatient_record": ir_name},
		["name", "status"],
		as_dict=True,
	)
	if not preauth:
		return True, "No preauth request for this admission"

	if preauth.status in ("Approved", "Partially Approved", "Closed"):
		return True, f"Preauth {preauth.name}: {preauth.status}"
	return False, f"Preauth {preauth.name}: {preauth.status} — not yet approved/closed"
