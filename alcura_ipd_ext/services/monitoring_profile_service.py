"""Monitoring profile auto-application service (US-H1).

Handles:
- Resolving the active ICU Monitoring Profile for a ward classification
- Auto-starting bedside charts on admission or transfer
- Discontinuing profile-started charts when a patient leaves a unit type
- Compliance checking for mandatory chart coverage
"""

from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import now_datetime


def get_profile_for_unit_type(
	unit_type: str,
	company: str | None = None,
) -> str | None:
	"""Return the active ICU Monitoring Profile name for a unit type.

	Company-specific profiles take priority over global ones.
	"""
	if company:
		profile = frappe.db.exists(
			"ICU Monitoring Profile",
			{"unit_type": unit_type, "company": company, "is_active": 1},
		)
		if profile:
			return profile

	return frappe.db.exists(
		"ICU Monitoring Profile",
		{
			"unit_type": unit_type,
			"is_active": 1,
			"company": ("is", "not set"),
		},
	)


def apply_profile_for_ward(
	inpatient_record: str,
	ward: str,
) -> list[dict]:
	"""Auto-start charts for the monitoring profile matching the ward's classification.

	Called after bed allocation or transfer. Skips charts that already have
	an active instance for the same template on the admission.

	Returns list of dicts with ``chart`` (name) and ``chart_template`` for each started chart.
	"""
	ward_data = frappe.db.get_value(
		"Hospital Ward", ward, ["ward_classification", "company"], as_dict=True
	)
	if not ward_data:
		return []

	profile_name = get_profile_for_unit_type(
		ward_data.ward_classification, ward_data.company
	)
	if not profile_name:
		return []

	profile = frappe.get_doc("ICU Monitoring Profile", profile_name)
	started = []

	for row in profile.chart_templates:
		if not row.auto_start:
			continue

		existing = frappe.db.exists(
			"IPD Bedside Chart",
			{
				"inpatient_record": inpatient_record,
				"chart_template": row.chart_template,
				"status": ("in", ("Active", "Paused")),
			},
		)
		if existing:
			continue

		from alcura_ipd_ext.services.charting_service import start_bedside_chart

		freq = row.frequency_override or None
		result = start_bedside_chart(
			inpatient_record=inpatient_record,
			chart_template=row.chart_template,
			frequency_minutes=freq,
		)

		frappe.db.set_value(
			"IPD Bedside Chart",
			result["chart"],
			"source_profile",
			profile_name,
			update_modified=False,
		)

		started.append({
			"chart": result["chart"],
			"chart_template": row.chart_template,
		})

	if started:
		_log_profile_application(inpatient_record, profile_name, started)

	return started


def remove_profile_charts(
	inpatient_record: str,
	old_ward: str,
) -> list[str]:
	"""Discontinue charts auto-started by the profile of the old ward.

	Only discontinues charts whose ``source_profile`` matches the profile
	for the old ward's classification. Manually started charts are untouched.

	Returns list of discontinued chart names.
	"""
	ward_data = frappe.db.get_value(
		"Hospital Ward", old_ward, ["ward_classification", "company"], as_dict=True
	)
	if not ward_data:
		return []

	profile_name = get_profile_for_unit_type(
		ward_data.ward_classification, ward_data.company
	)
	if not profile_name:
		return []

	charts = frappe.get_all(
		"IPD Bedside Chart",
		filters={
			"inpatient_record": inpatient_record,
			"source_profile": profile_name,
			"status": ("in", ("Active", "Paused")),
		},
		pluck="name",
	)

	discontinued = []
	for chart_name in charts:
		doc = frappe.get_doc("IPD Bedside Chart", chart_name)
		doc.status = "Discontinued"
		doc.discontinued_at = now_datetime()
		doc.discontinued_by = frappe.session.user
		doc.save(ignore_permissions=True)
		discontinued.append(chart_name)

	if discontinued:
		ir_doc = frappe.get_doc("Inpatient Record", inpatient_record)
		ir_doc.add_comment(
			"Info",
			_("{0} chart(s) discontinued (profile {1} no longer applicable).").format(
				len(discontinued), frappe.bold(profile_name)
			),
		)

	return discontinued


def swap_profile_on_transfer(
	inpatient_record: str,
	old_ward: str,
	new_ward: str,
) -> dict:
	"""Handle profile change when a patient is transferred between wards.

	If the ward classification changed, discontinues old profile charts and
	applies the new profile. If both wards have the same classification,
	no action is taken.

	Returns dict with ``removed`` and ``started`` lists.
	"""
	old_class = frappe.db.get_value("Hospital Ward", old_ward, "ward_classification")
	new_class = frappe.db.get_value("Hospital Ward", new_ward, "ward_classification")

	if old_class == new_class:
		return {"removed": [], "started": []}

	removed = remove_profile_charts(inpatient_record, old_ward)
	started = apply_profile_for_ward(inpatient_record, new_ward)

	return {"removed": removed, "started": started}


def get_compliance_for_ir(inpatient_record: str) -> dict:
	"""Check whether all mandatory charts from the applicable profile are active.

	Returns dict with ``profile``, ``compliant`` (bool), ``mandatory_total``,
	``mandatory_active``, and ``missing`` (list of template names).
	"""
	ir_data = frappe.db.get_value(
		"Inpatient Record",
		inpatient_record,
		["custom_current_ward", "company"],
		as_dict=True,
	)
	if not ir_data or not ir_data.custom_current_ward:
		return {"profile": None, "compliant": True, "mandatory_total": 0, "mandatory_active": 0, "missing": []}

	ward_data = frappe.db.get_value(
		"Hospital Ward",
		ir_data.custom_current_ward,
		["ward_classification", "company"],
		as_dict=True,
	)
	if not ward_data:
		return {"profile": None, "compliant": True, "mandatory_total": 0, "mandatory_active": 0, "missing": []}

	profile_name = get_profile_for_unit_type(
		ward_data.ward_classification, ward_data.company or ir_data.company
	)
	if not profile_name:
		return {"profile": None, "compliant": True, "mandatory_total": 0, "mandatory_active": 0, "missing": []}

	profile = frappe.get_doc("ICU Monitoring Profile", profile_name)
	mandatory_templates = [
		row.chart_template for row in profile.chart_templates if row.is_mandatory
	]

	active_templates = set(
		frappe.get_all(
			"IPD Bedside Chart",
			filters={
				"inpatient_record": inpatient_record,
				"status": ("in", ("Active", "Paused")),
			},
			pluck="chart_template",
		)
	)

	missing = [t for t in mandatory_templates if t not in active_templates]

	return {
		"profile": profile_name,
		"compliant": len(missing) == 0,
		"mandatory_total": len(mandatory_templates),
		"mandatory_active": len(mandatory_templates) - len(missing),
		"missing": missing,
	}


def _log_profile_application(
	inpatient_record: str,
	profile_name: str,
	started: list[dict],
) -> None:
	chart_names = ", ".join(s["chart_template"] for s in started)
	ir_doc = frappe.get_doc("Inpatient Record", inpatient_record)
	ir_doc.add_comment(
		"Info",
		_("Monitoring profile {0} applied. Charts started: {1}").format(
			frappe.bold(profile_name), chart_names
		),
	)
