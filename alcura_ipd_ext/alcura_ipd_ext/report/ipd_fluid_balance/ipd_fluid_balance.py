"""IPD Fluid Balance Report — hourly/shift-wise intake vs output."""

from __future__ import annotations

import frappe
from frappe import _


def execute(filters=None):
	filters = filters or {}
	view = filters.get("view", "Hourly")

	if view == "Shift":
		return _shift_view(filters)
	return _hourly_view(filters)


def _hourly_view(filters):
	columns = [
		{"fieldname": "hour", "label": _("Hour"), "fieldtype": "Data", "width": 80},
		{"fieldname": "intake", "label": _("Intake (mL)"), "fieldtype": "Float", "width": 120},
		{"fieldname": "output", "label": _("Output (mL)"), "fieldtype": "Float", "width": 120},
		{"fieldname": "net", "label": _("Net (mL)"), "fieldtype": "Float", "width": 100},
		{"fieldname": "running_balance", "label": _("Running Balance (mL)"), "fieldtype": "Float", "width": 150},
	]

	ir = filters.get("inpatient_record")
	if not ir:
		return columns, [], None, None

	from alcura_ipd_ext.services.io_service import get_hourly_balance

	data = get_hourly_balance(ir, filters.get("date"))
	for row in data:
		row["hour"] = f"{row['hour']:02d}:00"

	chart = {
		"data": {
			"labels": [r["hour"] for r in data],
			"datasets": [
				{"name": _("Intake"), "values": [r["intake"] for r in data]},
				{"name": _("Output"), "values": [r["output"] for r in data]},
			],
		},
		"type": "bar",
	}

	return columns, data, None, chart


def _shift_view(filters):
	columns = [
		{"fieldname": "shift", "label": _("Shift"), "fieldtype": "Data", "width": 120},
		{"fieldname": "start_hour", "label": _("Start"), "fieldtype": "Int", "width": 80},
		{"fieldname": "end_hour", "label": _("End"), "fieldtype": "Int", "width": 80},
		{"fieldname": "intake", "label": _("Intake (mL)"), "fieldtype": "Float", "width": 120},
		{"fieldname": "output", "label": _("Output (mL)"), "fieldtype": "Float", "width": 120},
		{"fieldname": "balance", "label": _("Balance (mL)"), "fieldtype": "Float", "width": 120},
	]

	ir = filters.get("inpatient_record")
	if not ir:
		return columns, [], None, None

	from alcura_ipd_ext.services.io_service import get_shift_balance

	data = get_shift_balance(ir, filters.get("date"))

	return columns, data, None, None
