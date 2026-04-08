"""Seed data for ICU Monitoring Profiles (US-H1).

Creates standard monitoring profiles that map ward classifications to
chart templates for auto-application on admission/transfer.
"""

from __future__ import annotations

import frappe

PROFILES = [
	{
		"profile_name": "ICU Standard Profile",
		"unit_type": "ICU",
		"is_active": 1,
		"description": "Standard ICU monitoring: vitals every hour, ventilator every hour.",
		"chart_templates": [
			{
				"chart_template": "ICU — Vitals",
				"is_mandatory": 1,
				"auto_start": 1,
				"display_order": 10,
			},
			{
				"chart_template": "Ventilator Monitoring",
				"is_mandatory": 0,
				"auto_start": 0,
				"display_order": 20,
			},
			{
				"chart_template": "Pain Assessment",
				"frequency_override": 120,
				"is_mandatory": 0,
				"auto_start": 1,
				"display_order": 30,
			},
		],
	},
	{
		"profile_name": "MICU Standard Profile",
		"unit_type": "MICU",
		"is_active": 1,
		"description": "Medical ICU monitoring with vitals and glucose tracking.",
		"chart_templates": [
			{
				"chart_template": "ICU — Vitals",
				"is_mandatory": 1,
				"auto_start": 1,
				"display_order": 10,
			},
			{
				"chart_template": "Glucose Monitoring",
				"frequency_override": 240,
				"is_mandatory": 0,
				"auto_start": 1,
				"display_order": 20,
			},
		],
	},
	{
		"profile_name": "CICU Standard Profile",
		"unit_type": "CICU",
		"is_active": 1,
		"description": "Cardiac ICU: vitals with hemodynamic focus.",
		"chart_templates": [
			{
				"chart_template": "ICU — Vitals",
				"is_mandatory": 1,
				"auto_start": 1,
				"display_order": 10,
			},
		],
	},
	{
		"profile_name": "SICU Standard Profile",
		"unit_type": "SICU",
		"is_active": 1,
		"description": "Surgical ICU monitoring with ventilator and pain.",
		"chart_templates": [
			{
				"chart_template": "ICU — Vitals",
				"is_mandatory": 1,
				"auto_start": 1,
				"display_order": 10,
			},
			{
				"chart_template": "Ventilator Monitoring",
				"is_mandatory": 0,
				"auto_start": 0,
				"display_order": 20,
			},
			{
				"chart_template": "Pain Assessment",
				"frequency_override": 120,
				"is_mandatory": 1,
				"auto_start": 1,
				"display_order": 30,
			},
		],
	},
	{
		"profile_name": "NICU Standard Profile",
		"unit_type": "NICU",
		"is_active": 1,
		"description": "Neonatal ICU: hourly vitals, glucose every 4 hours.",
		"chart_templates": [
			{
				"chart_template": "ICU — Vitals",
				"is_mandatory": 1,
				"auto_start": 1,
				"display_order": 10,
			},
			{
				"chart_template": "Glucose Monitoring",
				"frequency_override": 240,
				"is_mandatory": 0,
				"auto_start": 1,
				"display_order": 20,
			},
		],
	},
	{
		"profile_name": "HDU Standard Profile",
		"unit_type": "HDU",
		"is_active": 1,
		"description": "High-dependency unit: vitals every 2 hours.",
		"chart_templates": [
			{
				"chart_template": "ICU — Vitals",
				"frequency_override": 120,
				"is_mandatory": 1,
				"auto_start": 1,
				"display_order": 10,
			},
		],
	},
]


def setup_monitoring_profile_fixtures():
	"""Create monitoring profiles if they do not already exist. Idempotent."""
	for profile_data in PROFILES:
		if frappe.db.exists("ICU Monitoring Profile", profile_data["profile_name"]):
			continue

		templates = profile_data.pop("chart_templates")

		all_templates_exist = all(
			frappe.db.exists("IPD Chart Template", t["chart_template"])
			for t in templates
		)
		if not all_templates_exist:
			frappe.logger("alcura_ipd_ext").warning(
				f"Skipping profile {profile_data['profile_name']}: "
				"referenced chart template(s) not found."
			)
			profile_data["chart_templates"] = templates
			continue

		doc = frappe.get_doc({
			"doctype": "ICU Monitoring Profile",
			**profile_data,
		})
		for tmpl in templates:
			doc.append("chart_templates", tmpl)

		doc.insert(ignore_permissions=True)
		frappe.logger("alcura_ipd_ext").info(
			f"Created monitoring profile: {doc.profile_name}"
		)

		profile_data["chart_templates"] = templates

	frappe.db.commit()


def teardown_monitoring_profile_fixtures():
	"""Remove monitoring profiles created by this app."""
	for profile_data in PROFILES:
		name = profile_data["profile_name"]
		if frappe.db.exists("ICU Monitoring Profile", name):
			frappe.delete_doc("ICU Monitoring Profile", name, force=True)

	frappe.db.commit()
