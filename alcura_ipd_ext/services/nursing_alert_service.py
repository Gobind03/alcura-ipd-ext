"""Alert and task generation for nursing risk indicators.

Creates ToDo assignments and timeline comments when risk thresholds
are breached during nursing admission assessment. Idempotent — will
not create duplicate alerts for the same risk event on the same IR.
"""

from __future__ import annotations

import frappe
from frappe import _


# Alert reference prefix used to prevent duplicates
_ALERT_REF_PREFIX = "NursingRisk"


# ── Alert Rule Definitions ───────────────────────────────────────────

_ALERT_RULES = [
	{
		"risk_field": "custom_fall_risk_level",
		"trigger_values": ("High",),
		"tag": "fall-risk",
		"description_tpl": "Fall Prevention Protocol — {patient_name} ({ir})",
		"priority": "High",
	},
	{
		"risk_field": "custom_pressure_risk_level",
		"trigger_values": ("High", "Very High"),
		"tag": "pressure-risk",
		"description_tpl": "Pressure Injury Prevention — {patient_name} ({ir})",
		"priority": "High",
	},
	{
		"risk_field": "custom_nutrition_risk_level",
		"trigger_values": ("High",),
		"tag": "nutrition-risk",
		"description_tpl": "Dietician Review Required — {patient_name} ({ir})",
		"priority": "Medium",
	},
]


# ── Public API ───────────────────────────────────────────────────────


def raise_risk_alerts(inpatient_record: str, flags: dict) -> list[str]:
	"""Evaluate risk flags and create ToDo alerts for any high-risk
	indicators. Also posts allergy alert comments.

	Args:
		inpatient_record: Name of the Inpatient Record.
		flags: Dict of custom field values just written to the IR.

	Returns:
		List of ToDo names created (empty if none triggered).
	"""
	ir_data = frappe.db.get_value(
		"Inpatient Record",
		inpatient_record,
		["patient", "patient_name", "custom_current_ward"],
		as_dict=True,
	)

	if not ir_data:
		return []

	created = []

	for rule in _ALERT_RULES:
		level = flags.get(rule["risk_field"]) or ""
		if level not in rule["trigger_values"]:
			continue

		todo_name = _create_risk_todo(
			inpatient_record=inpatient_record,
			patient_name=ir_data.patient_name or ir_data.patient,
			ward=ir_data.custom_current_ward or "",
			rule=rule,
		)
		if todo_name:
			created.append(todo_name)

	# Allergy alert as timeline comment
	allergy_alert = flags.get("custom_allergy_alert")
	allergy_summary = flags.get("custom_allergy_summary", "")
	if allergy_alert and allergy_summary:
		_post_allergy_comment(inpatient_record, allergy_summary)

	if created:
		frappe.publish_realtime(
			"nursing_risk_alert",
			{
				"inpatient_record": inpatient_record,
				"patient": ir_data.patient,
				"patient_name": ir_data.patient_name,
				"alerts": created,
			},
			after_commit=True,
		)

	return created


# ── Internal Helpers ─────────────────────────────────────────────────


def _make_reference_name(inpatient_record: str, tag: str) -> str:
	return f"{_ALERT_REF_PREFIX}:{tag}:{inpatient_record}"


def _has_existing_open_todo(reference_name: str) -> bool:
	"""Check for an existing open ToDo with the same reference."""
	return bool(
		frappe.db.exists(
			"ToDo",
			{
				"reference_type": "Inpatient Record",
				"reference_name": reference_name.split(":")[-1],
				"description": ("like", f"%{reference_name}%"),
				"status": "Open",
			},
		)
	)


def _get_ward_nursing_users(ward: str) -> list[str]:
	"""Return users with the Nursing User role. If a ward is provided,
	this could be scoped further; for now returns the first available
	Nursing User to assign the task."""
	users = frappe.get_all(
		"Has Role",
		filters={"role": "Nursing User", "parenttype": "User"},
		fields=["parent"],
		limit=5,
	)
	return [u.parent for u in users if u.parent != "Administrator"]


def _create_risk_todo(
	inpatient_record: str,
	patient_name: str,
	ward: str,
	rule: dict,
) -> str | None:
	"""Create a ToDo for a risk alert if one does not already exist."""
	ref = _make_reference_name(inpatient_record, rule["tag"])

	if _has_existing_open_todo(ref):
		return None

	assignees = _get_ward_nursing_users(ward)
	assignee = assignees[0] if assignees else frappe.session.user

	description = rule["description_tpl"].format(
		patient_name=patient_name,
		ir=inpatient_record,
	)
	# Embed the reference tag for idempotency checks
	description = f"{description}\n<!-- ref:{ref} -->"

	todo = frappe.get_doc({
		"doctype": "ToDo",
		"description": description,
		"reference_type": "Inpatient Record",
		"reference_name": inpatient_record,
		"allocated_to": assignee,
		"priority": rule.get("priority", "Medium"),
		"status": "Open",
	})
	todo.insert(ignore_permissions=True)

	# Timeline comment on the IR for audit
	frappe.get_doc("Inpatient Record", inpatient_record).add_comment(
		"Info",
		_("{risk_tag} alert raised: {desc}").format(
			risk_tag=rule["tag"].replace("-", " ").title(),
			desc=rule["description_tpl"].format(
				patient_name=patient_name,
				ir=inpatient_record,
			),
		),
	)

	return todo.name


def _post_allergy_comment(inpatient_record: str, allergy_summary: str):
	"""Post an allergy alert comment on the IR timeline if not already posted."""
	marker = f"ALLERGY ALERT: {allergy_summary}"

	existing = frappe.db.exists(
		"Comment",
		{
			"reference_doctype": "Inpatient Record",
			"reference_name": inpatient_record,
			"content": ("like", f"%{marker[:50]}%"),
		},
	)
	if existing:
		return

	frappe.get_doc("Inpatient Record", inpatient_record).add_comment(
		"Info",
		_(marker),
	)
