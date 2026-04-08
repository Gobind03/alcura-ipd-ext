"""Service for Admission Checklist creation and lifecycle management.

Handles:
- Template selection based on payer type and care setting
- Checklist creation from a template for a given Inpatient Record
- Item completion and waiver with audit trail
- Status recomputation (Incomplete → Complete / Overridden)
"""

from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import now_datetime


def create_checklist_for_admission(inpatient_record: str) -> dict:
	"""Create an Admission Checklist from the best-matching template.

	Args:
		inpatient_record: Name of the Inpatient Record.

	Returns:
		Dict with ``checklist`` (name) and ``status`` keys.

	Raises:
		frappe.ValidationError: If a checklist already exists or no
			matching template is found.
	"""
	existing = frappe.db.exists(
		"Admission Checklist", {"inpatient_record": inpatient_record}
	)
	if existing:
		frappe.throw(
			_("An Admission Checklist already exists for {0}: {1}").format(
				frappe.bold(inpatient_record), frappe.bold(existing)
			),
			exc=frappe.ValidationError,
		)

	ir_doc = frappe.get_doc("Inpatient Record", inpatient_record)
	payer_type = ir_doc.get("custom_payer_type") or ""
	template = _select_template(payer_type)

	if not template:
		frappe.throw(
			_("No active Admission Checklist Template found for payer type '{0}'. "
			  "Please create a template first.").format(payer_type or "All"),
			exc=frappe.ValidationError,
		)

	checklist = _create_from_template(ir_doc, template)

	ir_doc.db_set("custom_admission_checklist", checklist.name, update_modified=False)

	ir_doc.add_comment(
		"Info",
		_("Admission Checklist {0} created from template {1}.").format(
			frappe.bold(checklist.name), frappe.bold(template.name)
		),
	)

	return {"checklist": checklist.name, "status": checklist.status}


def complete_item(checklist_name: str, row_idx: int) -> dict:
	"""Mark a checklist entry as Completed.

	Args:
		checklist_name: Name of the Admission Checklist.
		row_idx: 1-based index of the entry row.

	Returns:
		Dict with ``checklist``, ``row_idx``, ``item``, and ``status`` keys.
	"""
	doc = frappe.get_doc("Admission Checklist", checklist_name)
	_validate_checklist_editable(doc)

	entry = _get_entry_by_idx(doc, row_idx)

	if entry.status != "Pending":
		frappe.throw(
			_("Item '{0}' is already {1}.").format(
				entry.item_label, entry.status
			),
			exc=frappe.ValidationError,
		)

	entry.status = "Completed"
	entry.completed_by = frappe.session.user
	entry.completed_on = now_datetime()

	doc.save(ignore_permissions=True)
	_recompute_status(doc)

	return {
		"checklist": doc.name,
		"row_idx": row_idx,
		"item": entry.item_label,
		"status": doc.status,
	}


def waive_item(checklist_name: str, row_idx: int, reason: str) -> dict:
	"""Waive (override) a mandatory checklist entry.

	Requires Healthcare Administrator role. The template item must have
	``can_override`` enabled.

	Args:
		checklist_name: Name of the Admission Checklist.
		row_idx: 1-based index of the entry row.
		reason: Mandatory reason for waiving.

	Returns:
		Dict with ``checklist``, ``row_idx``, ``item``, and ``status`` keys.
	"""
	if "Healthcare Administrator" not in frappe.get_roles():
		frappe.throw(
			_("Only Healthcare Administrators can waive checklist items."),
			exc=frappe.PermissionError,
		)

	if not reason or not reason.strip():
		frappe.throw(
			_("A reason is required to waive a checklist item."),
			exc=frappe.ValidationError,
		)

	doc = frappe.get_doc("Admission Checklist", checklist_name)
	_validate_checklist_editable(doc)

	entry = _get_entry_by_idx(doc, row_idx)

	if entry.status != "Pending":
		frappe.throw(
			_("Item '{0}' is already {1}.").format(
				entry.item_label, entry.status
			),
			exc=frappe.ValidationError,
		)

	# Verify the template item allows override
	if doc.template_used:
		template = frappe.get_doc("Admission Checklist Template", doc.template_used)
		template_item = next(
			(i for i in template.checklist_items if i.item_label == entry.item_label),
			None,
		)
		if template_item and not template_item.can_override:
			frappe.throw(
				_("Item '{0}' is not configured as overridable in the template.").format(
					entry.item_label
				),
				exc=frappe.ValidationError,
			)

	entry.status = "Waived"
	entry.override_by = frappe.session.user
	entry.override_reason = reason.strip()
	entry.completed_on = now_datetime()

	doc.save(ignore_permissions=True)
	_recompute_status(doc)

	doc.add_comment(
		"Info",
		_("Item '{0}' waived by {1}. Reason: {2}").format(
			entry.item_label,
			frappe.session.user,
			reason.strip(),
		),
	)

	return {
		"checklist": doc.name,
		"row_idx": row_idx,
		"item": entry.item_label,
		"status": doc.status,
	}


# ── Template Selection ───────────────────────────────────────────────


def _select_template(payer_type: str) -> "frappe.Document | None":
	"""Find the best-matching active template for a given payer type.

	Priority:
	1. Exact payer_type match (non-default)
	2. Default template for that payer_type
	3. Default template with blank payer_type (universal default)
	"""
	# Exact payer_type match
	if payer_type:
		name = frappe.db.get_value(
			"Admission Checklist Template",
			{"payer_type": payer_type, "is_active": 1, "is_default": 0},
			"name",
		)
		if name:
			return frappe.get_doc("Admission Checklist Template", name)

		name = frappe.db.get_value(
			"Admission Checklist Template",
			{"payer_type": payer_type, "is_active": 1, "is_default": 1},
			"name",
		)
		if name:
			return frappe.get_doc("Admission Checklist Template", name)

	# Universal default (blank payer_type)
	name = frappe.db.get_value(
		"Admission Checklist Template",
		{"payer_type": ("in", ["", None]), "is_active": 1, "is_default": 1},
		"name",
	)
	if name:
		return frappe.get_doc("Admission Checklist Template", name)

	# Any active template as last resort
	name = frappe.db.get_value(
		"Admission Checklist Template",
		{"is_active": 1},
		"name",
		order_by="is_default desc",
	)
	if name:
		return frappe.get_doc("Admission Checklist Template", name)

	return None


# ── Checklist Creation ───────────────────────────────────────────────


def _create_from_template(
	ir_doc, template: "frappe.Document"
) -> "frappe.Document":
	"""Create an Admission Checklist from a template."""
	doc = frappe.get_doc({
		"doctype": "Admission Checklist",
		"inpatient_record": ir_doc.name,
		"patient": ir_doc.patient,
		"template_used": template.name,
		"company": ir_doc.company,
		"status": "Incomplete",
	})

	for item in sorted(template.checklist_items, key=lambda x: x.sort_order or 0):
		doc.append("checklist_entries", {
			"item_label": item.item_label,
			"category": item.category,
			"is_mandatory": item.is_mandatory,
			"status": "Pending",
		})

	doc.insert(ignore_permissions=True)
	return doc


# ── Helpers ──────────────────────────────────────────────────────────


def _validate_checklist_editable(doc) -> None:
	if doc.status in ("Complete", "Overridden"):
		frappe.throw(
			_("Checklist {0} is already {1} and cannot be modified.").format(
				frappe.bold(doc.name), doc.status
			),
			exc=frappe.ValidationError,
		)


def _get_entry_by_idx(doc, row_idx: int):
	"""Return the checklist entry at the given 1-based index."""
	for entry in doc.checklist_entries:
		if entry.idx == row_idx:
			return entry

	frappe.throw(
		_("No checklist entry found at index {0}.").format(row_idx),
		exc=frappe.ValidationError,
	)


def _recompute_status(doc) -> None:
	"""Recompute the checklist status based on entry statuses.

	- Complete: all mandatory items are Completed (none Waived)
	- Overridden: all mandatory items are Completed or Waived (at least one Waived)
	- Incomplete: otherwise
	"""
	mandatory_entries = [e for e in doc.checklist_entries if e.is_mandatory]

	if not mandatory_entries:
		new_status = "Complete"
	else:
		all_done = all(e.status in ("Completed", "Waived") for e in mandatory_entries)
		any_waived = any(e.status == "Waived" for e in mandatory_entries)

		if all_done and any_waived:
			new_status = "Overridden"
		elif all_done:
			new_status = "Complete"
		else:
			new_status = "Incomplete"

	if new_status != doc.status:
		updates = {"status": new_status}
		if new_status in ("Complete", "Overridden"):
			updates["completed_by"] = frappe.session.user
			updates["completed_on"] = now_datetime()

		doc.db_set(updates, update_modified=True)
		doc.reload()

		# Sync status to IR
		if doc.inpatient_record:
			frappe.db.set_value(
				"Inpatient Record",
				doc.inpatient_record,
				"custom_checklist_status",
				new_status,
				update_modified=False,
			)
