"""Lab sample lifecycle management.

Handles sample creation, collection, handoff, receipt, recollection,
and critical result acknowledgment for IPD lab orders.
"""

from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import now_datetime


def create_sample(order_name: str) -> dict:
	"""Create an IPD Lab Sample from a clinical order.

	Returns dict with name and barcode of the new sample.
	"""
	order = frappe.get_doc("IPD Clinical Order", order_name)

	if order.order_type != "Lab Test":
		frappe.throw(_("Samples can only be created for Lab Test orders."))

	if order.status in ("Cancelled", "Draft"):
		frappe.throw(_("Cannot create sample for a {0} order.").format(order.status))

	sample = frappe.get_doc({
		"doctype": "IPD Lab Sample",
		"clinical_order": order_name,
		"patient": order.patient,
		"inpatient_record": order.inpatient_record,
		"lab_test_name": order.lab_test_name,
		"sample_type": order.sample_type,
		"is_fasting_sample": order.is_fasting_required,
		"ward": order.ward,
		"bed": order.bed,
	})
	sample.insert(ignore_permissions=True)

	return {"name": sample.name, "barcode": sample.barcode}


def record_collection(
	sample_name: str,
	collected_by: str | None = None,
	collection_site: str = "",
	notes: str = "",
) -> dict:
	"""Record sample collection by nurse/phlebotomist."""
	sample = frappe.get_doc("IPD Lab Sample", sample_name)
	acting_user = collected_by or frappe.session.user

	sample.transition_to("Collected")
	sample.collection_status = "Collected"
	sample.collected_by = acting_user
	sample.collected_at = now_datetime()
	sample.collection_site = collection_site
	sample.collection_notes = notes
	sample.save(ignore_permissions=True)

	# Record SLA milestone on the order
	_record_order_milestone(sample.clinical_order, "Sample Collected", acting_user)

	frappe.publish_realtime(
		"lab_sample_collected",
		{
			"sample": sample.name,
			"order": sample.clinical_order,
			"patient": sample.patient,
			"lab_test": sample.lab_test_name,
		},
	)

	return {"name": sample.name, "status": sample.status}


def record_handoff(
	sample_name: str,
	handed_off_by: str | None = None,
	transport_mode: str = "Manual",
) -> dict:
	"""Record sample handoff for transport to lab."""
	sample = frappe.get_doc("IPD Lab Sample", sample_name)
	acting_user = handed_off_by or frappe.session.user

	sample.transition_to("In Transit")
	sample.handed_off_by = acting_user
	sample.handed_off_at = now_datetime()
	sample.transport_mode = transport_mode
	sample.save(ignore_permissions=True)

	_record_order_milestone(sample.clinical_order, "Sample Handed Off", acting_user)

	return {"name": sample.name, "status": sample.status}


def record_receipt(
	sample_name: str,
	received_by: str | None = None,
	sample_condition: str = "Acceptable",
) -> dict:
	"""Record sample receipt in lab. Triggers recollection if condition is bad."""
	sample = frappe.get_doc("IPD Lab Sample", sample_name)
	acting_user = received_by or frappe.session.user

	sample.transition_to("Received")
	sample.received_by = acting_user
	sample.received_at = now_datetime()
	sample.sample_condition = sample_condition
	sample.save(ignore_permissions=True)

	_record_order_milestone(sample.clinical_order, "Sample Received", acting_user)

	if sample_condition != "Acceptable":
		request_recollection(
			sample.name,
			reason=f"Sample condition: {sample_condition}",
		)

	return {"name": sample.name, "status": sample.status, "needs_recollection": sample_condition != "Acceptable"}


def request_recollection(sample_name: str, reason: str) -> dict:
	"""Mark sample as needing recollection and create a new sample."""
	sample = frappe.get_doc("IPD Lab Sample", sample_name)

	sample.collection_status = "Recollection Needed"
	sample.recollection_reason = reason
	sample.recollection_requested_by = frappe.session.user
	sample.recollection_requested_at = now_datetime()
	sample.status = "Rejected"
	sample.save(ignore_permissions=True)

	new_sample = frappe.get_doc({
		"doctype": "IPD Lab Sample",
		"clinical_order": sample.clinical_order,
		"patient": sample.patient,
		"inpatient_record": sample.inpatient_record,
		"lab_test_name": sample.lab_test_name,
		"sample_type": sample.sample_type,
		"is_fasting_sample": sample.is_fasting_sample,
		"ward": sample.ward,
		"bed": sample.bed,
		"parent_sample": sample.name,
	})
	new_sample.insert(ignore_permissions=True)

	# Notify nursing about recollection
	from alcura_ipd_ext.services.order_notification_service import _send_notifications, _get_role_users

	recipients = _get_role_users("Nursing User")
	_send_notifications(
		recipients=recipients,
		subject=_(
			"Recollection needed for {0} ({1}) — {2}"
		).format(sample.lab_test_name, sample.patient_name, reason),
		document_type="IPD Lab Sample",
		document_name=new_sample.name,
		ref_key=f"recollect:{sample.clinical_order}:{new_sample.name}",
		alert_type="Alert",
	)

	return {"original_sample": sample.name, "new_sample": new_sample.name, "new_barcode": new_sample.barcode}


def acknowledge_critical_result(sample_name: str, user: str | None = None) -> dict:
	"""Record acknowledgment of a critical lab result."""
	sample = frappe.get_doc("IPD Lab Sample", sample_name)

	if not sample.is_critical_result:
		frappe.throw(_("This sample does not have a critical result."))

	if sample.critical_result_acknowledged_by:
		frappe.throw(_("Critical result has already been acknowledged."))

	acting_user = user or frappe.session.user
	sample.critical_result_acknowledged_by = acting_user
	sample.critical_result_acknowledged_at = now_datetime()
	sample.save(ignore_permissions=True)

	return {"name": sample.name, "acknowledged_by": acting_user}


def get_collection_queue(ward: str | None = None) -> list[dict]:
	"""Return pending samples for collection, optionally filtered by ward."""
	filters = {
		"collection_status": "Pending",
		"status": "Pending",
	}
	if ward:
		filters["ward"] = ward

	return frappe.get_all(
		"IPD Lab Sample",
		filters=filters,
		fields=[
			"name", "clinical_order", "patient", "patient_name",
			"inpatient_record", "lab_test_name", "sample_type",
			"barcode", "is_fasting_sample", "ward", "bed",
			"creation",
		],
		order_by="creation asc",
	)


def get_sample_lifecycle(order_name: str) -> list[dict]:
	"""Return full timeline for a lab order's samples."""
	return frappe.get_all(
		"IPD Lab Sample",
		filters={"clinical_order": order_name},
		fields=[
			"name", "status", "collection_status", "barcode",
			"collected_by", "collected_at", "collection_site",
			"handed_off_by", "handed_off_at", "transport_mode",
			"received_by", "received_at", "sample_condition",
			"is_critical_result", "critical_result_acknowledged_by",
			"critical_result_acknowledged_at",
			"parent_sample", "recollection_reason",
			"creation", "modified",
		],
		order_by="creation asc",
	)


# ── Private helpers ──────────────────────────────────────────────────


def _record_order_milestone(order_name: str, milestone: str, user: str) -> None:
	"""Record a milestone on the linked clinical order."""
	if not order_name:
		return
	from alcura_ipd_ext.services.clinical_order_service import record_milestone

	record_milestone(order_name, milestone, user)
