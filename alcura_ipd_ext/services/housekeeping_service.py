"""Housekeeping service for bed cleaning lifecycle.

Manages Bed Housekeeping Task creation, state transitions, SLA
computation, and bed status synchronization. Integrates with
IPD Bed Policy for SLA targets and cleaning type determination.
"""

from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import now_datetime, time_diff_in_seconds

from alcura_ipd_ext.alcura_ipd_ext.doctype.ipd_bed_policy.ipd_bed_policy import (
	get_policy,
)


def create_housekeeping_task(
	hospital_bed: str,
	trigger_event: str = "Discharge",
	inpatient_record: str | None = None,
	movement_log: str | None = None,
) -> str:
	"""Create a housekeeping task for a vacated bed.

	Determines cleaning type from bed attributes and ward flags.
	Sets SLA target from policy with type-specific multipliers.

	Returns the name of the created Bed Housekeeping Task.
	"""
	bed_data = frappe.db.get_value(
		"Hospital Bed",
		hospital_bed,
		["name", "hospital_room", "hospital_ward", "company",
		 "infection_block"],
		as_dict=True,
	)
	if not bed_data:
		frappe.throw(
			_("Hospital Bed {0} does not exist.").format(frappe.bold(hospital_bed)),
			exc=frappe.ValidationError,
		)

	cleaning_type, requires_deep = _determine_cleaning_type(bed_data)
	sla_minutes = _compute_sla_target(cleaning_type)

	doc = frappe.new_doc("Bed Housekeeping Task")
	doc.update({
		"hospital_bed": hospital_bed,
		"hospital_room": bed_data.hospital_room,
		"hospital_ward": bed_data.hospital_ward,
		"company": bed_data.company,
		"trigger_event": trigger_event,
		"inpatient_record": inpatient_record,
		"movement_log": movement_log,
		"cleaning_type": cleaning_type,
		"requires_deep_clean": requires_deep,
		"sla_target_minutes": sla_minutes,
		"created_on": now_datetime(),
	})
	doc.insert(ignore_permissions=True)
	return doc.name


def start_cleaning(task_name: str) -> None:
	"""Start the cleaning task and update bed housekeeping status."""
	doc = frappe.get_doc("Bed Housekeeping Task", task_name)
	doc.start_task()


def complete_cleaning(task_name: str) -> dict:
	"""Complete the cleaning and return bed to available status."""
	doc = frappe.get_doc("Bed Housekeeping Task", task_name)
	doc.complete_task()
	doc.reload()
	return {
		"status": "Completed",
		"turnaround_minutes": doc.turnaround_minutes,
		"hospital_bed": doc.hospital_bed,
	}


def cancel_task(task_name: str) -> None:
	"""Cancel a housekeeping task."""
	doc = frappe.get_doc("Bed Housekeeping Task", task_name)
	doc.cancel_task()


def check_sla_breaches() -> int:
	"""Check for housekeeping SLA breaches and send notifications.

	Called by scheduler every 15 minutes. Returns count of newly breached tasks.
	"""
	now = now_datetime()
	breached_count = 0

	tasks = frappe.get_all(
		"Bed Housekeeping Task",
		filters={
			"status": ("in", ("Pending", "In Progress")),
			"sla_breached": 0,
			"sla_target_minutes": (">", 0),
		},
		fields=["name", "created_on", "sla_target_minutes",
				"hospital_bed", "hospital_ward"],
	)

	for task in tasks:
		elapsed = time_diff_in_seconds(now, task.created_on)
		elapsed_minutes = elapsed / 60

		if elapsed_minutes > task.sla_target_minutes:
			frappe.db.set_value(
				"Bed Housekeeping Task", task.name,
				"sla_breached", 1,
				update_modified=False,
			)

			try:
				from alcura_ipd_ext.services.discharge_notification_service import (
					notify_housekeeping_sla_breach,
				)
				notify_housekeeping_sla_breach(
					task.name, task.hospital_bed, task.hospital_ward
				)
			except Exception:
				frappe.logger("alcura_ipd_ext").warning(
					f"Failed to send SLA breach notification for {task.name}",
					exc_info=True,
				)

			breached_count += 1

	return breached_count


# ── Private helpers ──────────────────────────────────────────────────


def _determine_cleaning_type(
	bed_data: frappe._dict,
) -> tuple[str, bool]:
	"""Determine cleaning type from bed and ward attributes."""
	if bed_data.infection_block:
		return "Isolation Clean", True

	ward_isolation = frappe.db.get_value(
		"Hospital Ward", bed_data.hospital_ward, "supports_isolation"
	)
	if ward_isolation:
		return "Isolation Clean", True

	return "Standard", False


def _compute_sla_target(cleaning_type: str) -> int:
	"""Compute SLA target in minutes based on cleaning type and policy."""
	policy = get_policy()
	base_sla = policy.get("cleaning_turnaround_sla_minutes") or 60

	multiplier_map = {
		"Standard": 1.0,
		"Deep Clean": float(policy.get("deep_clean_sla_multiplier") or 2.0),
		"Isolation Clean": float(policy.get("isolation_clean_sla_multiplier") or 3.0),
		"Terminal Clean": float(policy.get("deep_clean_sla_multiplier") or 2.0),
	}
	multiplier = multiplier_map.get(cleaning_type, 1.0)

	return int(base_sla * multiplier)
