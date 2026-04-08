"""Tests for ICU monitoring profile service — profile resolution, auto-application,
profile swap on transfer, and compliance checking (US-H1)."""

from __future__ import annotations

import frappe
import pytest
from frappe.utils import now_datetime


# ── Helpers ──────────────────────────────────────────────────────────


def _make_chart_template(
	name: str = "Test ICU Vitals",
	chart_type: str = "Vitals",
	freq: int = 60,
) -> "frappe.Document":
	if frappe.db.exists("IPD Chart Template", name):
		return frappe.get_doc("IPD Chart Template", name)

	doc = frappe.get_doc({
		"doctype": "IPD Chart Template",
		"template_name": name,
		"chart_type": chart_type,
		"default_frequency_minutes": freq,
		"is_active": 1,
		"parameters": [
			{
				"parameter_name": "Temperature",
				"parameter_type": "Numeric",
				"uom": "°C",
				"is_mandatory": 1,
				"display_order": 10,
				"min_value": 35.0,
				"max_value": 42.0,
				"critical_low": 35.5,
				"critical_high": 39.5,
			},
		],
	})
	doc.insert(ignore_permissions=True)
	return doc


def _make_monitoring_profile(
	name: str,
	unit_type: str,
	templates: list[dict],
	company: str | None = None,
) -> "frappe.Document":
	if frappe.db.exists("ICU Monitoring Profile", name):
		frappe.delete_doc("ICU Monitoring Profile", name, force=True)

	doc = frappe.get_doc({
		"doctype": "ICU Monitoring Profile",
		"profile_name": name,
		"unit_type": unit_type,
		"is_active": 1,
		"company": company,
		"chart_templates": templates,
	})
	doc.insert(ignore_permissions=True)
	return doc


def _make_ward(
	code: str,
	classification: str,
	company: str | None = None,
) -> "frappe.Document":
	existing = frappe.db.exists("Hospital Ward", {"ward_code": code})
	if existing:
		return frappe.get_doc("Hospital Ward", existing)

	doc = frappe.get_doc({
		"doctype": "Hospital Ward",
		"ward_code": code,
		"ward_name": f"Test {code}",
		"ward_classification": classification,
		"company": company or frappe.defaults.get_defaults().get("company", "_Test Company"),
		"is_active": 1,
	})
	doc.insert(ignore_permissions=True)
	return doc


def _make_ir(
	ward: str | None = None,
) -> "frappe.Document":
	patient = _ensure_patient()
	ir = frappe.get_doc({
		"doctype": "Inpatient Record",
		"patient": patient.name,
		"company": frappe.defaults.get_defaults().get("company", "_Test Company"),
		"status": "Admitted",
		"scheduled_date": frappe.utils.today(),
	})
	ir.insert(ignore_permissions=True)

	if ward:
		ir.db_set("custom_current_ward", ward)
		ir.reload()

	return ir


def _ensure_patient() -> "frappe.Document":
	if frappe.db.exists("Patient", {"patient_name": "_Test Profile Patient"}):
		return frappe.get_doc("Patient", {"patient_name": "_Test Profile Patient"})
	p = frappe.get_doc({
		"doctype": "Patient",
		"first_name": "_Test",
		"last_name": "Profile Patient",
	})
	p.insert(ignore_permissions=True)
	return p


# ── Profile Validation Tests ────────────────────────────────────────


class TestProfileValidation:
	def test_requires_at_least_one_template(self, admin_session):
		doc = frappe.get_doc({
			"doctype": "ICU Monitoring Profile",
			"profile_name": "Empty Profile",
			"unit_type": "ICU",
			"is_active": 1,
		})
		with pytest.raises(frappe.ValidationError, match="at least one"):
			doc.insert(ignore_permissions=True)

	def test_rejects_duplicate_templates(self, admin_session):
		tmpl = _make_chart_template("Dup Profile Tmpl")
		doc = frappe.get_doc({
			"doctype": "ICU Monitoring Profile",
			"profile_name": "Dup Template Profile",
			"unit_type": "ICU",
			"is_active": 1,
			"chart_templates": [
				{"chart_template": tmpl.name, "is_mandatory": 1, "auto_start": 1, "display_order": 10},
				{"chart_template": tmpl.name, "is_mandatory": 0, "auto_start": 1, "display_order": 20},
			],
		})
		with pytest.raises(frappe.ValidationError, match="Duplicate"):
			doc.insert(ignore_permissions=True)

	def test_rejects_inactive_template(self, admin_session):
		tmpl = _make_chart_template("Inactive Tmpl")
		tmpl.is_active = 0
		tmpl.save(ignore_permissions=True)

		doc = frappe.get_doc({
			"doctype": "ICU Monitoring Profile",
			"profile_name": "Inactive Tmpl Profile",
			"unit_type": "ICU",
			"is_active": 1,
			"chart_templates": [
				{"chart_template": tmpl.name, "is_mandatory": 1, "auto_start": 1, "display_order": 10},
			],
		})
		with pytest.raises(frappe.ValidationError, match="not active"):
			doc.insert(ignore_permissions=True)

	def test_rejects_duplicate_active_unit_type(self, admin_session):
		tmpl = _make_chart_template("Unique Unit Tmpl")
		_make_monitoring_profile(
			"First ICU Profile", "ICU",
			[{"chart_template": tmpl.name, "is_mandatory": 1, "auto_start": 1, "display_order": 10}],
		)

		doc = frappe.get_doc({
			"doctype": "ICU Monitoring Profile",
			"profile_name": "Second ICU Profile",
			"unit_type": "ICU",
			"is_active": 1,
			"chart_templates": [
				{"chart_template": tmpl.name, "is_mandatory": 1, "auto_start": 1, "display_order": 10},
			],
		})
		with pytest.raises(frappe.ValidationError, match="already exists"):
			doc.insert(ignore_permissions=True)

	def test_frequency_override_minimum(self, admin_session):
		tmpl = _make_chart_template("Freq Override Tmpl")
		doc = frappe.get_doc({
			"doctype": "ICU Monitoring Profile",
			"profile_name": "Bad Freq Profile",
			"unit_type": "PICU",
			"is_active": 1,
			"chart_templates": [
				{"chart_template": tmpl.name, "frequency_override": 0, "is_mandatory": 1, "auto_start": 1, "display_order": 10},
			],
		})
		with pytest.raises(frappe.ValidationError, match="at least 1 minute"):
			doc.insert(ignore_permissions=True)

	def test_valid_profile_creation(self, admin_session):
		tmpl = _make_chart_template("Valid Profile Tmpl")
		profile = _make_monitoring_profile(
			"Valid Profile", "HDU",
			[{"chart_template": tmpl.name, "is_mandatory": 1, "auto_start": 1, "display_order": 10}],
		)
		assert profile.name == "Valid Profile"
		assert len(profile.chart_templates) == 1


# ── Profile Resolution Tests ────────────────────────────────────────


class TestProfileResolution:
	def test_resolve_global_profile(self, admin_session):
		from alcura_ipd_ext.services.monitoring_profile_service import get_profile_for_unit_type

		tmpl = _make_chart_template("Resolve Global Tmpl")
		_make_monitoring_profile(
			"Global MICU Profile", "MICU",
			[{"chart_template": tmpl.name, "is_mandatory": 1, "auto_start": 1, "display_order": 10}],
		)

		result = get_profile_for_unit_type("MICU")
		assert result == "Global MICU Profile"

	def test_company_profile_takes_priority(self, admin_session):
		from alcura_ipd_ext.services.monitoring_profile_service import get_profile_for_unit_type

		tmpl = _make_chart_template("Company Prio Tmpl")
		_make_monitoring_profile(
			"Global CICU Profile", "CICU",
			[{"chart_template": tmpl.name, "is_mandatory": 1, "auto_start": 1, "display_order": 10}],
		)
		company = frappe.defaults.get_defaults().get("company", "_Test Company")
		_make_monitoring_profile(
			"Company CICU Profile", "CICU",
			[{"chart_template": tmpl.name, "is_mandatory": 1, "auto_start": 1, "display_order": 10}],
			company=company,
		)

		result = get_profile_for_unit_type("CICU", company)
		assert result == "Company CICU Profile"

	def test_no_profile_returns_none(self, admin_session):
		from alcura_ipd_ext.services.monitoring_profile_service import get_profile_for_unit_type

		result = get_profile_for_unit_type("Burns")
		assert result is None


# ── Auto-Application Tests ──────────────────────────────────────────


class TestAutoApplication:
	def test_apply_profile_starts_charts(self, admin_session):
		from alcura_ipd_ext.services.monitoring_profile_service import apply_profile_for_ward

		tmpl = _make_chart_template("Apply Tmpl")
		ward = _make_ward("AA-ICU", "ICU")
		_make_monitoring_profile(
			"Apply ICU Profile", "ICU",
			[{"chart_template": tmpl.name, "is_mandatory": 1, "auto_start": 1, "display_order": 10}],
		)

		ir = _make_ir()
		started = apply_profile_for_ward(ir.name, ward.name)

		assert len(started) == 1
		assert started[0]["chart_template"] == tmpl.name

		chart = frappe.get_doc("IPD Bedside Chart", started[0]["chart"])
		assert chart.source_profile == "Apply ICU Profile"
		assert chart.status == "Active"

	def test_apply_skips_existing_active_chart(self, admin_session):
		from alcura_ipd_ext.services.charting_service import start_bedside_chart
		from alcura_ipd_ext.services.monitoring_profile_service import apply_profile_for_ward

		tmpl = _make_chart_template("Skip Existing Tmpl")
		ward = _make_ward("SE-ICU", "ICU")
		_make_monitoring_profile(
			"Skip Existing Profile", "ICU",
			[{"chart_template": tmpl.name, "is_mandatory": 1, "auto_start": 1, "display_order": 10}],
		)

		ir = _make_ir()
		start_bedside_chart(ir.name, tmpl.name)

		started = apply_profile_for_ward(ir.name, ward.name)
		assert len(started) == 0

	def test_apply_skips_non_autostart(self, admin_session):
		from alcura_ipd_ext.services.monitoring_profile_service import apply_profile_for_ward

		tmpl = _make_chart_template("NoAuto Tmpl")
		ward = _make_ward("NA-ICU", "ICU")
		_make_monitoring_profile(
			"NoAuto Profile", "ICU",
			[{"chart_template": tmpl.name, "is_mandatory": 0, "auto_start": 0, "display_order": 10}],
		)

		ir = _make_ir()
		started = apply_profile_for_ward(ir.name, ward.name)
		assert len(started) == 0

	def test_no_profile_for_ward_is_noop(self, admin_session):
		from alcura_ipd_ext.services.monitoring_profile_service import apply_profile_for_ward

		ward = _make_ward("NP-GEN", "General")
		ir = _make_ir()
		started = apply_profile_for_ward(ir.name, ward.name)
		assert len(started) == 0


# ── Profile Removal Tests ───────────────────────────────────────────


class TestProfileRemoval:
	def test_remove_profile_charts(self, admin_session):
		from alcura_ipd_ext.services.monitoring_profile_service import (
			apply_profile_for_ward,
			remove_profile_charts,
		)

		tmpl = _make_chart_template("Remove Tmpl")
		ward = _make_ward("RM-ICU", "ICU")
		_make_monitoring_profile(
			"Remove ICU Profile", "ICU",
			[{"chart_template": tmpl.name, "is_mandatory": 1, "auto_start": 1, "display_order": 10}],
		)

		ir = _make_ir()
		started = apply_profile_for_ward(ir.name, ward.name)
		assert len(started) == 1

		removed = remove_profile_charts(ir.name, ward.name)
		assert len(removed) == 1

		chart = frappe.get_doc("IPD Bedside Chart", started[0]["chart"])
		assert chart.status == "Discontinued"

	def test_manual_charts_not_removed(self, admin_session):
		from alcura_ipd_ext.services.charting_service import start_bedside_chart
		from alcura_ipd_ext.services.monitoring_profile_service import remove_profile_charts

		tmpl = _make_chart_template("Manual Not Removed Tmpl")
		ward = _make_ward("MN-ICU", "ICU")

		ir = _make_ir()
		chart_result = start_bedside_chart(ir.name, tmpl.name)

		removed = remove_profile_charts(ir.name, ward.name)
		assert len(removed) == 0

		chart = frappe.get_doc("IPD Bedside Chart", chart_result["chart"])
		assert chart.status == "Active"


# ── Profile Swap Tests ──────────────────────────────────────────────


class TestProfileSwap:
	def test_swap_on_classification_change(self, admin_session):
		from alcura_ipd_ext.services.monitoring_profile_service import (
			apply_profile_for_ward,
			swap_profile_on_transfer,
		)

		tmpl1 = _make_chart_template("Swap ICU Tmpl")
		tmpl2 = _make_chart_template("Swap HDU Tmpl", freq=120)
		ward_icu = _make_ward("SW-ICU", "ICU")
		ward_hdu = _make_ward("SW-HDU", "HDU")
		_make_monitoring_profile(
			"Swap ICU Profile", "ICU",
			[{"chart_template": tmpl1.name, "is_mandatory": 1, "auto_start": 1, "display_order": 10}],
		)
		_make_monitoring_profile(
			"Swap HDU Profile", "HDU",
			[{"chart_template": tmpl2.name, "is_mandatory": 1, "auto_start": 1, "display_order": 10}],
		)

		ir = _make_ir()
		apply_profile_for_ward(ir.name, ward_icu.name)

		result = swap_profile_on_transfer(ir.name, ward_icu.name, ward_hdu.name)
		assert len(result["removed"]) == 1
		assert len(result["started"]) == 1

	def test_no_swap_same_classification(self, admin_session):
		from alcura_ipd_ext.services.monitoring_profile_service import swap_profile_on_transfer

		ward1 = _make_ward("SS-ICU1", "ICU")
		ward2 = _make_ward("SS-ICU2", "ICU")
		ir = _make_ir()

		result = swap_profile_on_transfer(ir.name, ward1.name, ward2.name)
		assert len(result["removed"]) == 0
		assert len(result["started"]) == 0


# ── Compliance Tests ────────────────────────────────────────────────


class TestProfileCompliance:
	def test_compliant_when_all_mandatory_active(self, admin_session):
		from alcura_ipd_ext.services.monitoring_profile_service import (
			apply_profile_for_ward,
			get_compliance_for_ir,
		)

		tmpl = _make_chart_template("Comply Tmpl")
		ward = _make_ward("CP-ICU", "ICU")
		_make_monitoring_profile(
			"Comply ICU Profile", "ICU",
			[{"chart_template": tmpl.name, "is_mandatory": 1, "auto_start": 1, "display_order": 10}],
		)

		ir = _make_ir(ward=ward.name)
		apply_profile_for_ward(ir.name, ward.name)

		result = get_compliance_for_ir(ir.name)
		assert result["compliant"]
		assert result["mandatory_total"] == 1
		assert result["mandatory_active"] == 1
		assert result["missing"] == []

	def test_non_compliant_when_mandatory_missing(self, admin_session):
		from alcura_ipd_ext.services.monitoring_profile_service import get_compliance_for_ir

		tmpl = _make_chart_template("NonComply Tmpl")
		ward = _make_ward("NC-ICU", "ICU")
		_make_monitoring_profile(
			"NonComply ICU Profile", "ICU",
			[{"chart_template": tmpl.name, "is_mandatory": 1, "auto_start": 1, "display_order": 10}],
		)

		ir = _make_ir(ward=ward.name)
		result = get_compliance_for_ir(ir.name)
		assert not result["compliant"]
		assert result["missing"] == [tmpl.name]
