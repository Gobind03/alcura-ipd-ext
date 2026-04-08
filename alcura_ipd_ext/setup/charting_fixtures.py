"""Seed data for bedside charting templates (US-E4).

Creates standard chart templates for:
- General Ward Vitals
- ICU Vitals
- Glucose Monitoring
- Pain Assessment
- Ventilator Monitoring
"""

from __future__ import annotations

import frappe

_N = "Numeric"
_S = "Select"
_T = "Text"
_C = "Check"


def _param(
	name: str,
	ptype: str = _N,
	uom: str = "",
	options: str = "",
	mandatory: bool = True,
	order: int = 0,
	min_val: float | None = None,
	max_val: float | None = None,
	crit_low: float | None = None,
	crit_high: float | None = None,
) -> dict:
	return {
		"parameter_name": name,
		"parameter_type": ptype,
		"uom": uom,
		"options": options,
		"is_mandatory": 1 if mandatory else 0,
		"display_order": order,
		"min_value": min_val or 0,
		"max_value": max_val or 0,
		"critical_low": crit_low or 0,
		"critical_high": crit_high or 0,
	}


TEMPLATES = [
	{
		"template_name": "General Ward — Vitals",
		"chart_type": "Vitals",
		"default_frequency_minutes": 240,
		"is_active": 1,
		"applicable_unit_types": "General",
		"description": "Standard vital signs for general ward patients (every 4 hours).",
		"parameters": [
			_param("Temperature", _N, "°C", order=10, min_val=35.0, max_val=42.0, crit_low=35.5, crit_high=39.5),
			_param("Pulse", _N, "bpm", order=20, min_val=30, max_val=200, crit_low=50, crit_high=130),
			_param("BP Systolic", _N, "mmHg", order=30, min_val=60, max_val=250, crit_low=80, crit_high=180),
			_param("BP Diastolic", _N, "mmHg", order=40, min_val=30, max_val=150, crit_low=50, crit_high=110),
			_param("SpO2", _N, "%", order=50, min_val=50, max_val=100, crit_low=90, crit_high=0),
			_param("Respiratory Rate", _N, "breaths/min", order=60, min_val=5, max_val=50, crit_low=10, crit_high=30),
		],
	},
	{
		"template_name": "ICU — Vitals",
		"chart_type": "Vitals",
		"default_frequency_minutes": 60,
		"is_active": 1,
		"applicable_unit_types": "ICU, MICU, SICU, CICU, PICU, NICU, HDU",
		"description": "Intensive care vital signs with additional haemodynamic parameters (hourly).",
		"parameters": [
			_param("Temperature", _N, "°C", order=10, min_val=35.0, max_val=42.0, crit_low=35.5, crit_high=39.5),
			_param("Pulse", _N, "bpm", order=20, min_val=30, max_val=200, crit_low=50, crit_high=130),
			_param("BP Systolic", _N, "mmHg", order=30, min_val=60, max_val=250, crit_low=80, crit_high=180),
			_param("BP Diastolic", _N, "mmHg", order=40, min_val=30, max_val=150, crit_low=50, crit_high=110),
			_param("MAP", _N, "mmHg", order=45, min_val=40, max_val=150, crit_low=60, crit_high=130),
			_param("SpO2", _N, "%", order=50, min_val=50, max_val=100, crit_low=90, crit_high=0),
			_param("Respiratory Rate", _N, "breaths/min", order=60, min_val=5, max_val=50, crit_low=10, crit_high=30),
			_param("CVP", _N, "cmH2O", order=70, min_val=-5, max_val=30, mandatory=False),
			_param("EtCO2", _N, "mmHg", order=80, min_val=15, max_val=60, crit_low=25, crit_high=50, mandatory=False),
		],
	},
	{
		"template_name": "Glucose Monitoring",
		"chart_type": "Glucose",
		"default_frequency_minutes": 360,
		"is_active": 1,
		"applicable_unit_types": "",
		"description": "Blood glucose monitoring with insulin tracking (every 6 hours).",
		"parameters": [
			_param("Blood Glucose", _N, "mg/dL", order=10, min_val=20, max_val=600, crit_low=60, crit_high=300),
			_param("Insulin Type", _S, "", "Regular\nNPH\nGlargine\nLispro\nAspart\nOther", mandatory=False, order=20),
			_param("Insulin Dose", _N, "units", order=30, min_val=0, max_val=100, mandatory=False),
		],
	},
	{
		"template_name": "Pain Assessment",
		"chart_type": "Pain",
		"default_frequency_minutes": 240,
		"is_active": 1,
		"applicable_unit_types": "",
		"description": "Pain assessment using NRS 0–10 scale with location and intervention tracking.",
		"parameters": [
			_param("Pain Score", _N, "", order=10, min_val=0, max_val=10, crit_high=7),
			_param("Pain Location", _T, "", order=20, mandatory=False),
			_param("Pain Character", _S, "", "Sharp\nDull\nBurning\nAching\nThrobbing\nRadiating\nOther", mandatory=False, order=30),
			_param("Intervention Given", _T, "", order=40, mandatory=False),
			_param("Post-Intervention Score", _N, "", order=50, min_val=0, max_val=10, mandatory=False),
		],
	},
	{
		"template_name": "Ventilator Monitoring",
		"chart_type": "Ventilator",
		"default_frequency_minutes": 60,
		"is_active": 1,
		"applicable_unit_types": "ICU, MICU, SICU, CICU",
		"description": "Ventilator parameters for mechanically ventilated patients (hourly).",
		"parameters": [
			_param("Mode", _S, "", "CMV\nSIMV\nPSV\nCPAP\nBiPAP\nAPRV\nHFOV\nOther", order=10),
			_param("FiO2", _N, "%", order=20, min_val=21, max_val=100),
			_param("PEEP", _N, "cmH2O", order=30, min_val=0, max_val=25),
			_param("PIP", _N, "cmH2O", order=40, min_val=0, max_val=60, crit_high=40),
			_param("Tidal Volume", _N, "mL", order=50, min_val=100, max_val=1000),
			_param("Rate Set", _N, "breaths/min", order=60, min_val=0, max_val=40),
			_param("Rate Actual", _N, "breaths/min", order=70, min_val=0, max_val=50),
			_param("SpO2", _N, "%", order=80, min_val=50, max_val=100, crit_low=88),
			_param("EtCO2", _N, "mmHg", order=90, min_val=15, max_val=60, crit_low=25, crit_high=50, mandatory=False),
		],
	},
]


def setup_charting_fixtures():
	"""Create chart templates if they do not already exist. Idempotent."""
	for tmpl_data in TEMPLATES:
		if frappe.db.exists("IPD Chart Template", tmpl_data["template_name"]):
			continue

		doc = frappe.get_doc({
			"doctype": "IPD Chart Template",
			**{k: v for k, v in tmpl_data.items() if k != "parameters"},
		})
		for param in tmpl_data["parameters"]:
			doc.append("parameters", param)

		doc.insert(ignore_permissions=True)
		frappe.logger("alcura_ipd_ext").info(
			f"Created chart template: {tmpl_data['template_name']}"
		)

	frappe.db.commit()


def teardown_charting_fixtures():
	"""Remove chart templates created by this app."""
	for tmpl_data in TEMPLATES:
		name = tmpl_data["template_name"]
		if frappe.db.exists("IPD Chart Template", name):
			frappe.delete_doc("IPD Chart Template", name, force=True)

	frappe.db.commit()
