"""Document event hooks for Lab Test (US-F2, US-G3).

Syncs Lab Test submission/cancellation back to the linked IPD Clinical Order
and IPD Lab Sample. Detects critical results and triggers acknowledgment flow.
"""

from __future__ import annotations

import frappe
from frappe.utils import now_datetime


def on_submit(doc: "frappe.Document", method: str) -> None:
	"""When a Lab Test is submitted, update the linked Clinical Order and Lab Sample."""
	_sync_lab_test_to_order(doc, submitted=True)
	_sync_lab_test_to_sample(doc, submitted=True)
	_check_critical_result(doc)


def on_cancel(doc: "frappe.Document", method: str) -> None:
	"""When a Lab Test is cancelled, revert the linked Clinical Order."""
	_sync_lab_test_to_order(doc, submitted=False)
	_sync_lab_test_to_sample(doc, submitted=False)


def _sync_lab_test_to_order(doc: "frappe.Document", submitted: bool) -> None:
	"""Find any Clinical Order linked to this Lab Test and update its status."""
	order_name = frappe.db.get_value(
		"IPD Clinical Order",
		{"linked_lab_test": doc.name, "order_type": "Lab Test"},
	)
	if not order_name:
		return

	if submitted:
		from alcura_ipd_ext.services.clinical_order_service import record_milestone

		record_milestone(order_name, "Result Published")


def _sync_lab_test_to_sample(doc: "frappe.Document", submitted: bool) -> None:
	"""Update linked IPD Lab Sample status when Lab Test is submitted/cancelled."""
	order_name = frappe.db.get_value(
		"IPD Clinical Order",
		{"linked_lab_test": doc.name, "order_type": "Lab Test"},
	)
	if not order_name:
		return

	samples = frappe.get_all(
		"IPD Lab Sample",
		filters={
			"clinical_order": order_name,
			"status": ("not in", ("Completed", "Rejected")),
		},
		pluck="name",
	)
	if not samples:
		return

	for sample_name in samples:
		sample = frappe.get_doc("IPD Lab Sample", sample_name)
		if submitted:
			sample.linked_lab_test = doc.name
			if sample.status in ("Received", "Processing"):
				sample.status = "Completed"
			elif sample.status != "Completed":
				sample.status = "Completed"
			sample.save(ignore_permissions=True)
		else:
			if sample.status == "Completed":
				sample.status = "Processing"
				sample.save(ignore_permissions=True)


def _check_critical_result(doc: "frappe.Document") -> None:
	"""Check if lab test results contain critical values and flag the sample."""
	order_name = frappe.db.get_value(
		"IPD Clinical Order",
		{"linked_lab_test": doc.name, "order_type": "Lab Test"},
	)
	if not order_name:
		return

	is_critical = _has_critical_values(doc)
	if not is_critical:
		return

	samples = frappe.get_all(
		"IPD Lab Sample",
		filters={"clinical_order": order_name},
		pluck="name",
		order_by="creation desc",
		limit=1,
	)
	if not samples:
		return

	sample = frappe.get_doc("IPD Lab Sample", samples[0])
	sample.is_critical_result = 1
	sample.save(ignore_permissions=True)

	from alcura_ipd_ext.services.order_notification_service import notify_critical_result

	notify_critical_result(
		order_name=order_name,
		sample_name=sample.name,
		lab_test_name=doc.name,
	)


def _has_critical_values(doc: "frappe.Document") -> bool:
	"""Check if any test result in the Lab Test exceeds normal ranges.

	Uses the normal_range field from the Lab Test Template child rows.
	Returns True if any value falls outside the normal range.
	"""
	if not hasattr(doc, "normal_test_items"):
		return False

	for item in doc.normal_test_items or []:
		if not item.result_value:
			continue
		try:
			value = float(item.result_value)
		except (ValueError, TypeError):
			continue

		min_val = None
		max_val = None
		if item.get("custom_critical_low"):
			try:
				min_val = float(item.custom_critical_low)
			except (ValueError, TypeError):
				pass
		if item.get("custom_critical_high"):
			try:
				max_val = float(item.custom_critical_high)
			except (ValueError, TypeError):
				pass

		if min_val is not None and value < min_val:
			return True
		if max_val is not None and value > max_val:
			return True

	return False
