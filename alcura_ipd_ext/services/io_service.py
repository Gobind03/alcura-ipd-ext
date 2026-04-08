"""Service for Intake-Output entry management and fluid balance computation.

Handles:
- I/O entry creation helpers
- Correction entry creation
- Fluid balance computation (hourly, shift-wise, daily)
"""

from __future__ import annotations

from datetime import timedelta

import frappe
from frappe import _
from frappe.utils import get_datetime, getdate, now_datetime


# ── Shift definitions (8-hour blocks) ───────────────────────────────

SHIFT_HOURS = [
	("Morning", 6, 14),
	("Afternoon", 14, 22),
	("Night", 22, 6),
]


# ── Fluid Balance Computation ────────────────────────────────────────


def get_fluid_balance(
	inpatient_record: str,
	date: str | None = None,
) -> dict:
	"""Compute fluid balance for an admission on a given date.

	Returns:
		Dict with total_intake, total_output, balance, and per-category breakdown.
	"""
	target_date = getdate(date) if date else getdate()

	entries = frappe.get_all(
		"IPD IO Entry",
		filters={
			"inpatient_record": inpatient_record,
			"status": "Active",
			"entry_datetime": ("between", [
				f"{target_date} 00:00:00",
				f"{target_date} 23:59:59",
			]),
		},
		fields=["io_type", "fluid_category", "volume_ml", "entry_datetime"],
		order_by="entry_datetime asc",
	)

	total_intake = 0.0
	total_output = 0.0
	intake_breakdown: dict[str, float] = {}
	output_breakdown: dict[str, float] = {}

	for entry in entries:
		vol = entry.volume_ml or 0.0
		if entry.io_type == "Intake":
			total_intake += vol
			intake_breakdown[entry.fluid_category] = (
				intake_breakdown.get(entry.fluid_category, 0.0) + vol
			)
		else:
			total_output += vol
			output_breakdown[entry.fluid_category] = (
				output_breakdown.get(entry.fluid_category, 0.0) + vol
			)

	return {
		"date": str(target_date),
		"total_intake": total_intake,
		"total_output": total_output,
		"balance": total_intake - total_output,
		"intake_breakdown": intake_breakdown,
		"output_breakdown": output_breakdown,
		"entry_count": len(entries),
	}


def get_hourly_balance(
	inpatient_record: str,
	date: str | None = None,
) -> list[dict]:
	"""Compute hourly fluid balance for an admission.

	Returns:
		List of dicts with hour, intake, output, balance.
	"""
	target_date = getdate(date) if date else getdate()

	entries = frappe.get_all(
		"IPD IO Entry",
		filters={
			"inpatient_record": inpatient_record,
			"status": "Active",
			"entry_datetime": ("between", [
				f"{target_date} 00:00:00",
				f"{target_date} 23:59:59",
			]),
		},
		fields=["io_type", "volume_ml", "entry_datetime"],
		order_by="entry_datetime asc",
	)

	hourly: dict[int, dict] = {}
	for h in range(24):
		hourly[h] = {"hour": h, "intake": 0.0, "output": 0.0}

	for entry in entries:
		hour = get_datetime(entry.entry_datetime).hour
		vol = entry.volume_ml or 0.0
		if entry.io_type == "Intake":
			hourly[hour]["intake"] += vol
		else:
			hourly[hour]["output"] += vol

	result = []
	running = 0.0
	for h in range(24):
		row = hourly[h]
		row["net"] = row["intake"] - row["output"]
		running += row["net"]
		row["running_balance"] = running
		result.append(row)

	return result


def get_shift_balance(
	inpatient_record: str,
	date: str | None = None,
) -> list[dict]:
	"""Compute shift-wise fluid balance.

	Uses 8-hour shift blocks: Morning (06-14), Afternoon (14-22), Night (22-06).
	"""
	target_date = getdate(date) if date else getdate()
	hourly = get_hourly_balance(inpatient_record, str(target_date))

	shifts = []
	for shift_name, start_h, end_h in SHIFT_HOURS:
		intake = 0.0
		output = 0.0

		if start_h < end_h:
			hours = range(start_h, end_h)
		else:
			hours = list(range(start_h, 24)) + list(range(0, end_h))

		for h in hours:
			intake += hourly[h]["intake"]
			output += hourly[h]["output"]

		shifts.append({
			"shift": shift_name,
			"start_hour": start_h,
			"end_hour": end_h,
			"intake": intake,
			"output": output,
			"balance": intake - output,
		})

	return shifts


# ── I/O Correction ──────────────────────────────────────────────────


def create_io_correction(original_entry: str, correction_reason: str) -> dict:
	"""Create a correction for an existing I/O entry.

	Returns:
		Dict with ``name`` of the new correction entry.
	"""
	original = frappe.get_doc("IPD IO Entry", original_entry)

	if original.status == "Corrected":
		frappe.throw(_("This entry has already been corrected."))

	new_doc = frappe.get_doc({
		"doctype": "IPD IO Entry",
		"patient": original.patient,
		"inpatient_record": original.inpatient_record,
		"entry_datetime": original.entry_datetime,
		"io_type": original.io_type,
		"fluid_category": original.fluid_category,
		"fluid_name": original.fluid_name,
		"route": original.route,
		"volume_ml": original.volume_ml,
		"is_correction": 1,
		"corrects_entry": original.name,
		"correction_reason": correction_reason,
		"notes": original.notes,
	})
	new_doc.insert(ignore_permissions=True)

	return {"name": new_doc.name}
