"""Whitelisted API endpoints for IPD Clinical Order operations."""

from __future__ import annotations

import frappe
from frappe import _


@frappe.whitelist()
def create_medication_order(
	patient: str,
	inpatient_record: str,
	medication_name: str,
	company: str | None = None,
	medication_item: str | None = None,
	dose: str | None = None,
	dose_uom: str | None = None,
	route: str | None = None,
	frequency: str | None = None,
	urgency: str = "Routine",
	is_stat: int = 0,
	is_prn: int = 0,
	prn_reason: str | None = None,
	start_datetime: str | None = None,
	end_datetime: str | None = None,
	duration_days: int | None = None,
	indication: str | None = None,
	schedule_instructions: str | None = None,
	ordering_practitioner: str | None = None,
	clinical_notes: str | None = None,
) -> dict:
	frappe.has_permission("IPD Clinical Order", "create", throw=True)

	if not company:
		company = frappe.db.get_value("Inpatient Record", inpatient_record, "company")

	from alcura_ipd_ext.services.clinical_order_service import create_order

	doc = create_order(
		order_type="Medication",
		patient=patient,
		inpatient_record=inpatient_record,
		company=company,
		urgency=urgency,
		ordering_practitioner=ordering_practitioner,
		medication_item=medication_item,
		medication_name=medication_name,
		dose=dose,
		dose_uom=dose_uom,
		route=route,
		frequency=frequency,
		is_stat=int(is_stat),
		is_prn=int(is_prn),
		prn_reason=prn_reason,
		start_datetime=start_datetime,
		end_datetime=end_datetime,
		duration_days=duration_days,
		indication=indication,
		schedule_instructions=schedule_instructions,
		clinical_notes=clinical_notes,
	)
	return {"order": doc.name, "status": doc.status}


@frappe.whitelist()
def create_lab_order(
	patient: str,
	inpatient_record: str,
	lab_test_name: str,
	company: str | None = None,
	lab_test_template: str | None = None,
	sample_type: str | None = None,
	is_fasting_required: int = 0,
	collection_instructions: str | None = None,
	urgency: str = "Routine",
	ordering_practitioner: str | None = None,
	clinical_notes: str | None = None,
) -> dict:
	frappe.has_permission("IPD Clinical Order", "create", throw=True)

	if not company:
		company = frappe.db.get_value("Inpatient Record", inpatient_record, "company")

	from alcura_ipd_ext.services.clinical_order_service import create_order

	doc = create_order(
		order_type="Lab Test",
		patient=patient,
		inpatient_record=inpatient_record,
		company=company,
		urgency=urgency,
		ordering_practitioner=ordering_practitioner,
		lab_test_template=lab_test_template,
		lab_test_name=lab_test_name,
		sample_type=sample_type,
		is_fasting_required=int(is_fasting_required),
		collection_instructions=collection_instructions,
		clinical_notes=clinical_notes,
	)
	return {"order": doc.name, "status": doc.status}


@frappe.whitelist()
def create_procedure_order(
	patient: str,
	inpatient_record: str,
	procedure_name: str,
	order_type: str = "Procedure",
	company: str | None = None,
	procedure_template: str | None = None,
	body_site: str | None = None,
	is_bedside: int = 0,
	prep_instructions: str | None = None,
	urgency: str = "Routine",
	ordering_practitioner: str | None = None,
	clinical_notes: str | None = None,
) -> dict:
	frappe.has_permission("IPD Clinical Order", "create", throw=True)

	if order_type not in ("Radiology", "Procedure"):
		order_type = "Procedure"

	if not company:
		company = frappe.db.get_value("Inpatient Record", inpatient_record, "company")

	from alcura_ipd_ext.services.clinical_order_service import create_order

	doc = create_order(
		order_type=order_type,
		patient=patient,
		inpatient_record=inpatient_record,
		company=company,
		urgency=urgency,
		ordering_practitioner=ordering_practitioner,
		procedure_template=procedure_template,
		procedure_name=procedure_name,
		body_site=body_site,
		is_bedside=int(is_bedside),
		prep_instructions=prep_instructions,
		clinical_notes=clinical_notes,
	)
	return {"order": doc.name, "status": doc.status}


@frappe.whitelist()
def transition_order(order: str, new_status: str) -> dict:
	frappe.has_permission("IPD Clinical Order", "write", doc=order, throw=True)

	from alcura_ipd_ext.services.clinical_order_service import (
		acknowledge_order,
		complete_order,
		place_order,
		start_order,
	)

	action_map = {
		"Ordered": place_order,
		"Acknowledged": acknowledge_order,
		"In Progress": start_order,
		"Completed": complete_order,
	}

	fn = action_map.get(new_status)
	if fn:
		fn(order)
	else:
		frappe.throw(_("Use dedicated endpoints for Cancel/Hold/Resume."))

	doc = frappe.get_doc("IPD Clinical Order", order)
	return {"order": doc.name, "status": doc.status}


@frappe.whitelist()
def cancel_order(order: str, reason: str) -> dict:
	frappe.has_permission("IPD Clinical Order", "write", doc=order, throw=True)

	from alcura_ipd_ext.services.clinical_order_service import cancel_order as _cancel

	_cancel(order, reason)
	doc = frappe.get_doc("IPD Clinical Order", order)
	return {"order": doc.name, "status": doc.status}


@frappe.whitelist()
def hold_order(order: str, reason: str) -> dict:
	frappe.has_permission("IPD Clinical Order", "write", doc=order, throw=True)

	from alcura_ipd_ext.services.clinical_order_service import hold_order as _hold

	_hold(order, reason)
	doc = frappe.get_doc("IPD Clinical Order", order)
	return {"order": doc.name, "status": doc.status}


@frappe.whitelist()
def resume_order(order: str) -> dict:
	frappe.has_permission("IPD Clinical Order", "write", doc=order, throw=True)

	from alcura_ipd_ext.services.clinical_order_service import resume_order as _resume

	_resume(order)
	doc = frappe.get_doc("IPD Clinical Order", order)
	return {"order": doc.name, "status": doc.status}


@frappe.whitelist()
def record_milestone(order: str, milestone: str) -> dict:
	frappe.has_permission("IPD Clinical Order", "write", doc=order, throw=True)

	from alcura_ipd_ext.services.clinical_order_service import record_milestone as _record

	_record(order, milestone)
	doc = frappe.get_doc("IPD Clinical Order", order)
	return {"order": doc.name, "milestones": len(doc.sla_milestones)}


@frappe.whitelist()
def get_orders_for_ir(
	inpatient_record: str,
	order_type: str | None = None,
	status: str | None = None,
) -> list[dict]:
	frappe.has_permission("Inpatient Record", "read", doc=inpatient_record, throw=True)

	from alcura_ipd_ext.services.clinical_order_service import get_orders_for_ir as _get

	return _get(inpatient_record, order_type=order_type, status=status)


@frappe.whitelist()
def get_order_detail(order: str) -> dict:
	frappe.has_permission("IPD Clinical Order", "read", doc=order, throw=True)
	doc = frappe.get_doc("IPD Clinical Order", order)
	result = doc.as_dict()
	result["sla_milestones"] = [
		{
			"milestone": m.milestone,
			"target_at": m.target_at,
			"actual_at": m.actual_at,
			"is_breached": m.is_breached,
			"recorded_by": m.recorded_by,
		}
		for m in doc.sla_milestones
	]
	return result
