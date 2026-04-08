"""Protocol bundle service (US-H4).

Handles:
- Activating care protocol bundles for an admission
- Generating step trackers with computed due times
- Tracking step completion and compliance scoring
- Marking overdue steps as missed
- Protocol lifecycle management (complete/discontinue/expire)
"""

from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import add_to_date, get_datetime, now_datetime


def activate_bundle(
	inpatient_record: str,
	protocol_bundle: str,
) -> dict:
	"""Activate a monitoring protocol bundle for an admission.

	Creates an Active Protocol Bundle with step trackers pre-populated
	from the protocol definition. Auto-starts observation charts and
	creates clinical orders where applicable.

	Returns dict with ``active_bundle``, ``steps_created``, ``charts_started``.
	"""
	ir = frappe.db.get_value(
		"Inpatient Record",
		inpatient_record,
		["patient", "status"],
		as_dict=True,
	)
	if not ir:
		frappe.throw(_("Inpatient Record {0} not found.").format(inpatient_record))

	if ir.status not in ("Admitted", "Admission Scheduled"):
		frappe.throw(
			_("Cannot activate protocol for patient with status '{0}'.").format(ir.status)
		)

	bundle = frappe.get_doc("Monitoring Protocol Bundle", protocol_bundle)
	if not bundle.is_active:
		frappe.throw(_("Protocol bundle '{0}' is not active.").format(protocol_bundle))

	_check_duplicate_bundle(inpatient_record, protocol_bundle)

	now = now_datetime()

	doc = frappe.get_doc({
		"doctype": "Active Protocol Bundle",
		"protocol_bundle": protocol_bundle,
		"patient": ir.patient,
		"inpatient_record": inpatient_record,
		"status": "Active",
		"activated_at": now,
		"activated_by": frappe.session.user,
		"compliance_score": 0,
	})

	charts_started = []
	for step in sorted(bundle.steps, key=lambda s: s.sequence):
		due_at = add_to_date(now, minutes=step.due_within_minutes or 0)
		doc.append("step_trackers", {
			"step_name": step.step_name,
			"step_type": step.step_type,
			"sequence": step.sequence,
			"is_mandatory": step.is_mandatory,
			"status": "Due" if step.due_within_minutes == 0 else "Pending",
			"due_at": due_at,
		})

		if step.step_type == "Observation" and step.chart_template:
			chart_name = _auto_start_chart(
				inpatient_record, step.chart_template
			)
			if chart_name:
				charts_started.append(chart_name)

	doc.insert(ignore_permissions=True)

	ir_doc = frappe.get_doc("Inpatient Record", inpatient_record)
	ir_doc.add_comment(
		"Info",
		_("Protocol bundle {0} activated with {1} steps.").format(
			frappe.bold(protocol_bundle), len(bundle.steps)
		),
	)

	return {
		"active_bundle": doc.name,
		"steps_created": len(doc.step_trackers),
		"charts_started": charts_started,
	}


def complete_step(
	active_bundle: str,
	step_name: str,
	linked_doc_type: str | None = None,
	linked_doc: str | None = None,
) -> dict:
	"""Mark a protocol step as completed and update compliance score."""
	doc = frappe.get_doc("Active Protocol Bundle", active_bundle)
	_ensure_active(doc)

	step = _find_step(doc, step_name)
	if step.status == "Completed":
		frappe.throw(_("Step '{0}' is already completed.").format(step_name))

	step.status = "Completed"
	step.completed_at = now_datetime()
	step.completed_by = frappe.session.user
	if linked_doc_type:
		step.linked_document_type = linked_doc_type
	if linked_doc:
		step.linked_document = linked_doc

	doc.compliance_score = compute_compliance(doc)
	doc.save(ignore_permissions=True)

	_check_bundle_completion(doc)

	return {
		"step_name": step_name,
		"status": "Completed",
		"compliance_score": doc.compliance_score,
	}


def skip_step(
	active_bundle: str,
	step_name: str,
	reason: str,
) -> dict:
	"""Mark a protocol step as skipped with a reason."""
	if not reason:
		frappe.throw(_("A reason is required to skip a step."))

	doc = frappe.get_doc("Active Protocol Bundle", active_bundle)
	_ensure_active(doc)

	step = _find_step(doc, step_name)
	if step.status in ("Completed", "Skipped"):
		frappe.throw(_("Step '{0}' cannot be skipped (status: {1}).").format(
			step_name, step.status
		))

	step.status = "Skipped"
	step.notes = reason
	step.completed_at = now_datetime()
	step.completed_by = frappe.session.user

	doc.compliance_score = compute_compliance(doc)
	doc.save(ignore_permissions=True)

	_check_bundle_completion(doc)

	return {
		"step_name": step_name,
		"status": "Skipped",
		"compliance_score": doc.compliance_score,
	}


def check_overdue_steps(active_bundle: str) -> int:
	"""Mark overdue pending/due steps as Missed. Returns count of newly missed steps."""
	doc = frappe.get_doc("Active Protocol Bundle", active_bundle)
	if doc.status != "Active":
		return 0

	now = now_datetime()
	missed_count = 0

	for step in doc.step_trackers:
		if step.status in ("Pending", "Due") and step.due_at:
			if get_datetime(step.due_at) < now:
				step.status = "Missed"
				missed_count += 1

	if missed_count:
		doc.compliance_score = compute_compliance(doc)
		doc.save(ignore_permissions=True)

	return missed_count


def compute_compliance(doc: "frappe.Document") -> float:
	"""Compute weighted compliance percentage for an active protocol bundle.

	Completed steps contribute their full weight. Skipped non-mandatory
	steps contribute their weight. Everything else contributes zero.
	"""
	total_weight = 0.0
	achieved_weight = 0.0

	for step in doc.step_trackers:
		weight = 1.0
		bundle = frappe.get_cached_doc(
			"Monitoring Protocol Bundle", doc.protocol_bundle
		)
		for bundle_step in bundle.steps:
			if bundle_step.step_name == step.step_name:
				weight = bundle_step.compliance_weight or 1.0
				break

		total_weight += weight

		if step.status == "Completed":
			achieved_weight += weight
		elif step.status == "Skipped" and not step.is_mandatory:
			achieved_weight += weight

	if total_weight == 0:
		return 100.0

	return round((achieved_weight / total_weight) * 100, 1)


def discontinue_bundle(active_bundle: str, reason: str) -> dict:
	"""Discontinue an active protocol bundle."""
	if not reason:
		frappe.throw(_("A reason is required to discontinue a bundle."))

	doc = frappe.get_doc("Active Protocol Bundle", active_bundle)
	_ensure_active(doc)

	doc.status = "Discontinued"
	doc.discontinued_at = now_datetime()
	doc.discontinued_by = frappe.session.user
	doc.discontinuation_reason = reason
	doc.save(ignore_permissions=True)

	ir_doc = frappe.get_doc("Inpatient Record", doc.inpatient_record)
	ir_doc.add_comment(
		"Info",
		_("Protocol bundle {0} discontinued. Reason: {1}").format(
			frappe.bold(doc.protocol_bundle), reason
		),
	)

	return {"status": "Discontinued", "active_bundle": active_bundle}


def get_active_bundles_for_ir(inpatient_record: str) -> list[dict]:
	"""Return all active/completed protocol bundles for an IR with compliance summaries."""
	return frappe.get_all(
		"Active Protocol Bundle",
		filters={"inpatient_record": inpatient_record},
		fields=[
			"name", "protocol_bundle", "patient", "status",
			"activated_at", "compliance_score",
			"completed_at", "discontinued_at",
		],
		order_by="activated_at desc",
	)


def check_all_active_bundles() -> int:
	"""Scan all active bundles for overdue steps. Returns total missed count."""
	active_bundles = frappe.get_all(
		"Active Protocol Bundle",
		filters={"status": "Active"},
		pluck="name",
	)

	total_missed = 0
	for bundle_name in active_bundles:
		missed = check_overdue_steps(bundle_name)
		total_missed += missed

		if missed:
			_notify_missed_steps(bundle_name, missed)

	return total_missed


def _check_duplicate_bundle(inpatient_record: str, protocol_bundle: str):
	existing = frappe.db.exists(
		"Active Protocol Bundle",
		{
			"inpatient_record": inpatient_record,
			"protocol_bundle": protocol_bundle,
			"status": "Active",
		},
	)
	if existing:
		frappe.throw(
			_("An active instance of {0} already exists for this admission: {1}").format(
				frappe.bold(protocol_bundle), frappe.bold(existing)
			)
		)


def _ensure_active(doc: "frappe.Document"):
	if doc.status != "Active":
		frappe.throw(
			_("Bundle {0} is {1} and cannot be modified.").format(
				doc.name, doc.status
			)
		)


def _find_step(doc: "frappe.Document", step_name: str):
	for step in doc.step_trackers:
		if step.step_name == step_name:
			return step
	frappe.throw(_("Step '{0}' not found in bundle {1}.").format(step_name, doc.name))


def _auto_start_chart(inpatient_record: str, chart_template: str) -> str | None:
	"""Start a bedside chart if one doesn't already exist."""
	existing = frappe.db.exists(
		"IPD Bedside Chart",
		{
			"inpatient_record": inpatient_record,
			"chart_template": chart_template,
			"status": ("in", ("Active", "Paused")),
		},
	)
	if existing:
		return None

	try:
		from alcura_ipd_ext.services.charting_service import start_bedside_chart

		result = start_bedside_chart(inpatient_record, chart_template)
		return result["chart"]
	except Exception:
		frappe.logger("alcura_ipd_ext").warning(
			f"Failed to auto-start chart {chart_template} for IR {inpatient_record}",
			exc_info=True,
		)
		return None


def _check_bundle_completion(doc: "frappe.Document"):
	"""Mark bundle as Completed if all steps are in a terminal state."""
	all_terminal = all(
		step.status in ("Completed", "Skipped", "Missed")
		for step in doc.step_trackers
	)
	if all_terminal:
		doc.status = "Completed"
		doc.completed_at = now_datetime()
		doc.save(ignore_permissions=True)


def _notify_missed_steps(bundle_name: str, missed_count: int):
	"""Send notification about missed protocol steps."""
	doc = frappe.get_doc("Active Protocol Bundle", bundle_name)
	recipients = frappe.get_all(
		"Has Role",
		filters={"role": ("in", ("Nursing User", "Physician")), "parenttype": "User"},
		pluck="parent",
	)
	recipients = [u for u in set(recipients) if u not in ("Administrator", "Guest")]

	for user in recipients:
		existing = frappe.db.exists(
			"Notification Log",
			{
				"for_user": user,
				"document_type": "Active Protocol Bundle",
				"document_name": bundle_name,
				"read": 0,
			},
		)
		if existing:
			continue

		notification = frappe.new_doc("Notification Log")
		notification.update({
			"for_user": user,
			"from_user": frappe.session.user,
			"type": "Alert",
			"document_type": "Active Protocol Bundle",
			"document_name": bundle_name,
			"subject": _(
				"PROTOCOL ALERT: {0} step(s) missed in {1} for patient {2}"
			).format(missed_count, doc.protocol_bundle, doc.patient),
		})
		notification.insert(ignore_permissions=True)
