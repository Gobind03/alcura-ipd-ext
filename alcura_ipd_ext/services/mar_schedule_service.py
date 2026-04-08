"""MAR schedule generation and due medication computation.

Generates Scheduled MAR entries from medication order frequency/duration,
computes due medications for nurse station display, and handles
overdue entry marking.
"""

from __future__ import annotations

from datetime import time as dt_time

import frappe
from frappe import _
from frappe.utils import (
	add_days,
	add_to_date,
	get_datetime,
	getdate,
	now_datetime,
	time_diff_in_seconds,
)


# Frequency -> list of (hour, minute) tuples for daily schedule
FREQUENCY_SCHEDULE: dict[str, list[tuple[int, int]]] = {
	"OD": [(8, 0)],
	"BD": [(8, 0), (20, 0)],
	"TDS": [(6, 0), (14, 0), (22, 0)],
	"QID": [(6, 0), (12, 0), (18, 0), (0, 0)],
	"Q4H": [(0, 0), (4, 0), (8, 0), (12, 0), (16, 0), (20, 0)],
	"Q6H": [(0, 0), (6, 0), (12, 0), (18, 0)],
	"Q8H": [(0, 0), (8, 0), (16, 0)],
	"Q12H": [(8, 0), (20, 0)],
	"Once": [(8, 0)],
}

# Shift boundaries (inclusive start, exclusive end)
SHIFT_BOUNDARIES = {
	"Morning": (dt_time(6, 0), dt_time(14, 0)),
	"Afternoon": (dt_time(14, 0), dt_time(22, 0)),
	"Night": (dt_time(22, 0), dt_time(6, 0)),
}

# Grace period before a scheduled entry is marked missed (minutes)
OVERDUE_GRACE_MINUTES = 60


def generate_mar_entries_for_order(order_name: str) -> list[str]:
	"""Generate Scheduled MAR entries for a medication order.

	Uses order frequency, start_datetime, and duration_days to compute
	scheduled times. STAT orders get a single entry at current time.
	PRN orders get no scheduled entries.

	Returns list of created MAR entry names.
	"""
	order = frappe.get_doc("IPD Clinical Order", order_name)

	if order.order_type != "Medication":
		return []

	frequency = order.frequency or ""
	if frequency == "PRN" or order.is_prn:
		return []

	start = get_datetime(order.start_datetime) if order.start_datetime else now_datetime()
	duration_days = order.duration_days or 1

	if frequency == "STAT":
		return _create_single_mar_entry(order, start)

	if frequency == "Continuous":
		return _create_single_mar_entry(order, start)

	schedule_times = FREQUENCY_SCHEDULE.get(frequency)
	if not schedule_times:
		return _create_single_mar_entry(order, start)

	created = []
	start_date = getdate(start)

	for day_offset in range(duration_days):
		current_date = add_days(start_date, day_offset)
		for hour, minute in schedule_times:
			scheduled_dt = get_datetime(f"{current_date} {hour:02d}:{minute:02d}:00")

			if scheduled_dt < start:
				continue

			if order.end_datetime and scheduled_dt > get_datetime(order.end_datetime):
				continue

			existing = frappe.db.exists("IPD MAR Entry", {
				"clinical_order": order.name,
				"scheduled_time": scheduled_dt,
				"status": "Active",
			})
			if existing:
				continue

			entry = _create_mar_entry(order, scheduled_dt)
			created.append(entry.name)

	return created


def generate_daily_mar_entries(inpatient_record: str, date: str | None = None) -> list[str]:
	"""Generate MAR entries for all active medication orders for a patient for a given date."""
	target_date = getdate(date) if date else getdate()

	active_orders = frappe.get_all(
		"IPD Clinical Order",
		filters={
			"inpatient_record": inpatient_record,
			"order_type": "Medication",
			"status": ("in", ("Ordered", "Acknowledged", "In Progress")),
		},
		fields=["name"],
	)

	created = []
	for order_row in active_orders:
		order = frappe.get_doc("IPD Clinical Order", order_row.name)
		frequency = order.frequency or ""

		if frequency in ("PRN", "STAT", "Continuous", "Once") or order.is_prn:
			continue

		schedule_times = FREQUENCY_SCHEDULE.get(frequency, [])
		for hour, minute in schedule_times:
			scheduled_dt = get_datetime(f"{target_date} {hour:02d}:{minute:02d}:00")

			if order.start_datetime and scheduled_dt < get_datetime(order.start_datetime):
				continue
			if order.end_datetime and scheduled_dt > get_datetime(order.end_datetime):
				continue

			existing = frappe.db.exists("IPD MAR Entry", {
				"clinical_order": order.name,
				"scheduled_time": scheduled_dt,
				"status": "Active",
			})
			if existing:
				continue

			entry = _create_mar_entry(order, scheduled_dt)
			created.append(entry.name)

	return created


def get_due_medications(
	inpatient_record: str,
	from_time: str | None = None,
	to_time: str | None = None,
) -> list[dict]:
	"""Return MAR entries due in a time window, grouped by time slot."""
	now = now_datetime()
	start = get_datetime(from_time) if from_time else add_to_date(now, hours=-2)
	end = get_datetime(to_time) if to_time else add_to_date(now, hours=4)

	entries = frappe.get_all(
		"IPD MAR Entry",
		filters={
			"inpatient_record": inpatient_record,
			"status": "Active",
			"scheduled_time": ("between", [str(start), str(end)]),
		},
		fields=[
			"name", "medication_name", "medication_item", "dose", "dose_uom",
			"route", "scheduled_time", "administered_at", "administration_status",
			"administered_by", "ward", "bed", "clinical_order", "shift",
		],
		order_by="scheduled_time asc",
	)

	return entries


def get_ward_mar_board(
	ward: str,
	date: str | None = None,
	shift: str | None = None,
) -> dict:
	"""Return all patients' due meds for a ward/shift, grouped by patient."""
	target_date = getdate(date) if date else getdate()

	if shift and shift in SHIFT_BOUNDARIES:
		start_time, end_time = SHIFT_BOUNDARIES[shift]
		from_dt = get_datetime(f"{target_date} {start_time.strftime('%H:%M:%S')}")
		if shift == "Night":
			to_dt = get_datetime(f"{add_days(target_date, 1)} {end_time.strftime('%H:%M:%S')}")
		else:
			to_dt = get_datetime(f"{target_date} {end_time.strftime('%H:%M:%S')}")
	else:
		from_dt = get_datetime(f"{target_date} 00:00:00")
		to_dt = get_datetime(f"{target_date} 23:59:59")

	entries = frappe.get_all(
		"IPD MAR Entry",
		filters={
			"ward": ward,
			"status": "Active",
			"scheduled_time": ("between", [str(from_dt), str(to_dt)]),
		},
		fields=[
			"name", "patient", "inpatient_record",
			"medication_name", "dose", "dose_uom", "route",
			"scheduled_time", "administered_at", "administration_status",
			"administered_by", "bed", "clinical_order", "shift",
		],
		order_by="bed asc, scheduled_time asc",
	)

	# Batch-fetch patient names
	patient_ids = list({e.patient for e in entries if e.patient})
	patient_name_map: dict[str, str] = {}
	if patient_ids:
		for p in frappe.get_all("Patient", filters={"name": ("in", patient_ids)}, fields=["name", "patient_name"]):
			patient_name_map[p.name] = p.patient_name

	for entry in entries:
		entry["patient_name"] = patient_name_map.get(entry.patient, entry.patient)

	patients: dict[str, dict] = {}
	for entry in entries:
		key = entry.patient
		if key not in patients:
			patients[key] = {
				"patient": entry.patient,
				"patient_name": entry.get("patient_name") or entry.patient,
				"inpatient_record": entry.inpatient_record,
				"bed": entry.bed,
				"entries": [],
			}
		patients[key]["entries"].append(entry)

	status_counts = {}
	for entry in entries:
		st = entry.administration_status
		status_counts[st] = status_counts.get(st, 0) + 1

	return {
		"ward": ward,
		"date": str(target_date),
		"shift": shift,
		"total": len(entries),
		"status_counts": status_counts,
		"patients": list(patients.values()),
	}


def get_shift_mar_summary(ward: str, shift_date: str, shift: str) -> dict:
	"""Ward-level MAR summary for shift handoff."""
	board = get_ward_mar_board(ward, shift_date, shift)
	return {
		"ward": ward,
		"date": board["date"],
		"shift": shift,
		"total": board["total"],
		"status_counts": board["status_counts"],
		"patient_count": len(board["patients"]),
	}


def mark_overdue_scheduled_entries() -> int:
	"""Mark past-due Scheduled MAR entries as Missed.

	Called by scheduler. Returns count of entries marked.
	"""
	now = now_datetime()
	cutoff = add_to_date(now, minutes=-OVERDUE_GRACE_MINUTES)

	overdue = frappe.get_all(
		"IPD MAR Entry",
		filters={
			"administration_status": "Scheduled",
			"status": "Active",
			"scheduled_time": ("<=", str(cutoff)),
		},
		fields=["name", "patient", "inpatient_record", "medication_name", "ward"],
		limit_page_length=500,
	)

	for entry_data in overdue:
		frappe.db.set_value("IPD MAR Entry", entry_data.name, {
			"administration_status": "Missed",
		}, update_modified=False)

	if overdue:
		frappe.db.commit()
		for entry_data in overdue:
			frappe.publish_realtime(
				"mar_missed_alert",
				{
					"entry": entry_data.name,
					"patient": entry_data.patient,
					"inpatient_record": entry_data.inpatient_record,
					"medication": entry_data.medication_name,
					"ward": entry_data.ward,
				},
				after_commit=True,
			)

	return len(overdue)


def cancel_pending_mar_entries(order_name: str) -> int:
	"""Cancel all pending Scheduled MAR entries for a cancelled/held order."""
	pending = frappe.get_all(
		"IPD MAR Entry",
		filters={
			"clinical_order": order_name,
			"administration_status": "Scheduled",
			"status": "Active",
		},
		pluck="name",
	)

	for entry_name in pending:
		frappe.db.set_value("IPD MAR Entry", entry_name, {
			"administration_status": "Missed",
			"notes": "Order cancelled or put on hold",
		}, update_modified=False)

	if pending:
		frappe.db.commit()

	return len(pending)


def compute_shift(scheduled_time) -> str:
	"""Determine shift from a scheduled time."""
	if not scheduled_time:
		return ""
	dt = get_datetime(scheduled_time)
	t = dt.time()
	if dt_time(6, 0) <= t < dt_time(14, 0):
		return "Morning"
	elif dt_time(14, 0) <= t < dt_time(22, 0):
		return "Afternoon"
	else:
		return "Night"


# ── Private helpers ──────────────────────────────────────────────────


def _create_mar_entry(order, scheduled_dt) -> "frappe.Document":
	shift = compute_shift(scheduled_dt)
	entry = frappe.get_doc({
		"doctype": "IPD MAR Entry",
		"patient": order.patient,
		"inpatient_record": order.inpatient_record,
		"medication_name": order.medication_name,
		"medication_item": order.medication_item,
		"dose": order.dose,
		"dose_uom": order.dose_uom,
		"route": order.route,
		"scheduled_time": scheduled_dt,
		"administration_status": "Scheduled",
		"clinical_order": order.name,
		"shift": shift,
	})
	entry.insert(ignore_permissions=True)
	return entry


def _create_single_mar_entry(order, dt) -> list[str]:
	entry = _create_mar_entry(order, dt)
	return [entry.name]
