"""Dashboard override for the standard Inpatient Record doctype.

Adds Patient Encounter (consultation notes), bedside charting doctypes,
IPD Problem List Item, TPA/billing doctypes to the IR form dashboard
so count badges and quick links appear.
"""

from __future__ import annotations

from frappe import _


def get_dashboard_data(data):
	"""Extend the Inpatient Record dashboard with IPD clinical, charting,
	and TPA/billing doctypes."""
	data.setdefault("transactions", [])
	data.setdefault("non_standard_fieldnames", {})

	data["non_standard_fieldnames"]["Patient Encounter"] = "custom_linked_inpatient_record"

	clinical_group = {
		"label": _("Clinical Notes"),
		"items": ["Patient Encounter", "IPD Problem List Item"],
	}
	data["transactions"].insert(0, clinical_group)

	charting_group = {
		"label": _("Bedside Charts"),
		"items": [
			"IPD Bedside Chart",
			"IPD Chart Entry",
			"IPD IO Entry",
			"IPD Nursing Note",
			"IPD MAR Entry",
		],
	}
	data["transactions"].append(charting_group)

	tpa_billing_group = {
		"label": _("TPA & Billing"),
		"items": [
			"TPA Preauth Request",
			"Discharge Billing Checklist",
			"TPA Claim Pack",
		],
	}
	data["transactions"].append(tpa_billing_group)

	return data
