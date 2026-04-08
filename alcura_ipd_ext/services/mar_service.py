"""Service for Medication Administration Record (MAR) operations.

Handles:
- MAR entry creation
- Correction entry creation
- MAR summary queries
"""

from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import getdate


# ── MAR Correction ──────────────────────────────────────────────────


def create_mar_correction(original_entry: str, correction_reason: str) -> dict:
	"""Create a correction for an existing MAR entry.

	Returns:
		Dict with ``name`` of the new correction entry.
	"""
	original = frappe.get_doc("IPD MAR Entry", original_entry)

	if original.status == "Corrected":
		frappe.throw(_("This entry has already been corrected."))

	new_doc = frappe.get_doc({
		"doctype": "IPD MAR Entry",
		"patient": original.patient,
		"inpatient_record": original.inpatient_record,
		"medication_name": original.medication_name,
		"medication_item": original.medication_item,
		"dose": original.dose,
		"dose_uom": original.dose_uom,
		"route": original.route,
		"scheduled_time": original.scheduled_time,
		"administered_at": original.administered_at,
		"administration_status": original.administration_status,
		"administered_by": original.administered_by,
		"site": original.site,
		"is_correction": 1,
		"corrects_entry": original.name,
		"correction_reason": correction_reason,
		"notes": original.notes,
	})
	new_doc.insert(ignore_permissions=True)

	return {"name": new_doc.name}


# ── MAR Summary ─────────────────────────────────────────────────────


def get_mar_summary(
	inpatient_record: str,
	date: str | None = None,
) -> dict:
	"""Return MAR summary for an admission on a given date.

	Returns:
		Dict with status counts and entries list.
	"""
	target_date = getdate(date) if date else getdate()

	entries = frappe.get_all(
		"IPD MAR Entry",
		filters={
			"inpatient_record": inpatient_record,
			"status": "Active",
			"scheduled_time": ("between", [
				f"{target_date} 00:00:00",
				f"{target_date} 23:59:59",
			]),
		},
		fields=[
			"name", "medication_name", "dose", "route",
			"scheduled_time", "administered_at", "administration_status",
			"administered_by", "notes",
		],
		order_by="scheduled_time asc",
	)

	status_counts: dict[str, int] = {}
	for entry in entries:
		st = entry.administration_status
		status_counts[st] = status_counts.get(st, 0) + 1

	return {
		"date": str(target_date),
		"total": len(entries),
		"status_counts": status_counts,
		"entries": entries,
	}
