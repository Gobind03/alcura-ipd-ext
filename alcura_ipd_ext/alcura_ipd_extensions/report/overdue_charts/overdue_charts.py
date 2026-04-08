"""Overdue Charts Report — ward-level view of overdue chart entries."""

from __future__ import annotations

import frappe
from frappe import _


def execute(filters=None):
	filters = filters or {}
	columns = get_columns()
	data = get_data(filters)
	return columns, data


def get_columns():
	return [
		{"fieldname": "name", "label": _("Chart"), "fieldtype": "Link", "options": "IPD Bedside Chart", "width": 120},
		{"fieldname": "patient_name", "label": _("Patient"), "fieldtype": "Data", "width": 150},
		{"fieldname": "chart_type", "label": _("Chart Type"), "fieldtype": "Data", "width": 120},
		{"fieldname": "ward", "label": _("Ward"), "fieldtype": "Link", "options": "Hospital Ward", "width": 120},
		{"fieldname": "bed", "label": _("Bed"), "fieldtype": "Link", "options": "Hospital Bed", "width": 100},
		{"fieldname": "frequency_minutes", "label": _("Frequency (min)"), "fieldtype": "Int", "width": 100},
		{"fieldname": "last_entry_at", "label": _("Last Entry"), "fieldtype": "Datetime", "width": 170},
		{"fieldname": "next_due_at", "label": _("Next Due"), "fieldtype": "Data", "width": 170},
		{"fieldname": "overdue_minutes", "label": _("Overdue (min)"), "fieldtype": "Int", "width": 100},
	]


def get_data(filters):
	from alcura_ipd_ext.services.charting_service import get_overdue_charts

	return get_overdue_charts(
		ward=filters.get("ward"),
		company=filters.get("company"),
		grace_minutes=int(filters.get("grace_minutes", 0)),
	)
