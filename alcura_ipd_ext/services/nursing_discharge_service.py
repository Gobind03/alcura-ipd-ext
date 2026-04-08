"""Nursing discharge checklist service.

Provides domain logic for creating nursing discharge checklists with
standard items, managing item completion, and signoff/verification.
"""

from __future__ import annotations

import frappe
from frappe import _

_STANDARD_ITEMS: list[dict] = [
	{
		"item_name": "IV line / cannula removed",
		"item_category": "Line Removal",
		"is_mandatory": 1,
	},
	{
		"item_name": "Urinary catheter removed (if applicable)",
		"item_category": "Line Removal",
		"is_mandatory": 0,
	},
	{
		"item_name": "Drain / tube removed (if applicable)",
		"item_category": "Line Removal",
		"is_mandatory": 0,
	},
	{
		"item_name": "Medication counseling completed",
		"item_category": "Medication",
		"is_mandatory": 1,
	},
	{
		"item_name": "Discharge medications received from pharmacy",
		"item_category": "Medication",
		"is_mandatory": 1,
	},
	{
		"item_name": "Home-care instructions provided",
		"item_category": "Patient Education",
		"is_mandatory": 1,
	},
	{
		"item_name": "Warning signs explained to patient/family",
		"item_category": "Patient Education",
		"is_mandatory": 1,
	},
	{
		"item_name": "Diet instructions given",
		"item_category": "Patient Education",
		"is_mandatory": 0,
	},
	{
		"item_name": "Follow-up appointment communicated",
		"item_category": "Patient Education",
		"is_mandatory": 0,
	},
	{
		"item_name": "Patient belongings returned",
		"item_category": "Belongings",
		"is_mandatory": 1,
	},
	{
		"item_name": "Valuables checked and signed",
		"item_category": "Belongings",
		"is_mandatory": 0,
	},
	{
		"item_name": "Final vitals recorded",
		"item_category": "Documentation",
		"is_mandatory": 1,
	},
	{
		"item_name": "Wristband removed",
		"item_category": "Safety",
		"is_mandatory": 1,
	},
	{
		"item_name": "Discharge papers signed by patient/NOK",
		"item_category": "Documentation",
		"is_mandatory": 1,
	},
	{
		"item_name": "Escort / transport arranged",
		"item_category": "Safety",
		"is_mandatory": 0,
	},
]


def create_nursing_checklist(
	inpatient_record: str,
	discharge_advice: str | None = None,
) -> str:
	"""Create a Nursing Discharge Checklist with standard items.

	Returns the name of the created checklist. Raises if one already exists.
	"""
	if frappe.db.exists("Nursing Discharge Checklist", {"inpatient_record": inpatient_record}):
		frappe.throw(
			_("A nursing discharge checklist already exists for {0}.").format(
				frappe.bold(inpatient_record)
			),
			title=_("Duplicate Checklist"),
		)

	ir = frappe.get_doc("Inpatient Record", inpatient_record)

	doc = frappe.new_doc("Nursing Discharge Checklist")
	doc.update({
		"inpatient_record": inpatient_record,
		"patient": ir.patient,
		"company": ir.company,
		"discharge_advice": discharge_advice,
	})

	for item_def in _STANDARD_ITEMS:
		doc.append("items", {
			**item_def,
			"item_status": "Pending",
		})

	doc.insert(ignore_permissions=True)

	frappe.db.set_value(
		"Inpatient Record",
		inpatient_record,
		"custom_nursing_discharge_checklist",
		doc.name,
		update_modified=False,
	)

	return doc.name
