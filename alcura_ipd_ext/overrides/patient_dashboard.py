"""Dashboard override for the standard Patient doctype.

Adds Patient Payer Profile and Payer Eligibility Check links to the
Patient form dashboard so users can see linked records at a glance.
"""

from __future__ import annotations

from frappe import _


def get_dashboard_data(data):
	"""Extend the Patient dashboard with payer and eligibility links."""
	data.setdefault("transactions", [])
	data.setdefault("non_standard_fieldnames", {})

	data["non_standard_fieldnames"]["Patient Payer Profile"] = "patient"
	data["non_standard_fieldnames"]["Payer Eligibility Check"] = "patient"

	payer_group = {
		"label": _("Payer & Eligibility"),
		"items": ["Patient Payer Profile", "Payer Eligibility Check"],
	}

	data["transactions"].insert(0, payer_group)

	return data
