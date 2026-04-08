"""Patch: Add diet, elimination, and device lines fields to existing nursing
intake templates created by US-E1.

US-E2 expanded _COMMON_NURSING_FIELDS with new sections. This patch adds
those fields to any existing nursing intake templates that were created
before this version.

Safe to run repeatedly — checks for existing field labels before inserting.
"""

from __future__ import annotations

import frappe

# New fields added in US-E2, grouped by section
_NEW_FIELDS = [
	("Diet & Nutrition", "Current Diet", "Select", "Regular\nSoft\nLiquid\nNPO\nDiabetic\nRenal\nOther", 0, 180),
	("Diet & Nutrition", "Dietary Restrictions", "Small Text", "", 0, 190),
	("Diet & Nutrition", "Swallowing Difficulty", "Check", "", 0, 200),
	("Diet & Nutrition", "Feeding Assistance Required", "Select", "Independent\nPartial\nFull", 0, 210),
	("Elimination", "Bowel Pattern", "Select", "Normal\nConstipation\nDiarrhea\nIncontinence\nOstomy", 0, 220),
	("Elimination", "Last Bowel Movement", "Text", "", 0, 230),
	("Elimination", "Bladder Function", "Select", "Normal\nIncontinence\nRetention\nCatheterized", 0, 240),
	("Elimination", "Urinary Catheter Present", "Check", "", 0, 250),
	("Elimination", "Catheter Details", "Text", "", 0, 260),
	("Device Lines & Access", "IV Access Site/Type", "Text", "", 0, 280),
	("Device Lines & Access", "Central Line Present", "Check", "", 0, 290),
	("Device Lines & Access", "Central Line Details", "Text", "", 0, 300),
	("Device Lines & Access", "Arterial Line Present", "Check", "", 0, 310),
	("Device Lines & Access", "Nasogastric/Feeding Tube", "Check", "", 0, 320),
	("Device Lines & Access", "Drain/Tube Present", "Check", "", 0, 330),
	("Device Lines & Access", "Drain Details", "Text", "", 0, 340),
	("Device Lines & Access", "Other Devices", "Small Text", "", 0, 350),
]

# Templates that use _COMMON_NURSING_FIELDS
_NURSING_TEMPLATES = [
	"General Medicine — Nursing Intake",
	"Surgery — Nursing Intake",
	"ICU — Nursing Intake",
	"Obstetrics — Nursing Intake",
]


def execute():
	for template_name in _NURSING_TEMPLATES:
		if not frappe.db.exists("IPD Intake Assessment Template", template_name):
			continue

		doc = frappe.get_doc("IPD Intake Assessment Template", template_name)
		existing_labels = {
			(f.section_label, f.field_label)
			for f in doc.form_fields
		}

		added = 0
		for section, label, ftype, options, mandatory, order in _NEW_FIELDS:
			if (section, label) in existing_labels:
				continue

			doc.append("form_fields", {
				"section_label": section,
				"field_label": label,
				"field_type": ftype,
				"options": options,
				"is_mandatory": mandatory,
				"display_order": order,
				"role_visibility": "All",
			})
			added += 1

		if added:
			doc.version = (doc.version or 1) + 1
			doc.save(ignore_permissions=True)
			frappe.logger("alcura_ipd_ext").info(
				f"Patch: Added {added} fields to template '{template_name}', "
				f"version bumped to {doc.version}"
			)
