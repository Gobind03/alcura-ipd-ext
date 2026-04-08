"""Tests for protocol bundle service — activation, step tracking,
compliance scoring, and lifecycle management (US-H4)."""

from __future__ import annotations

import frappe
import pytest
from frappe.utils import add_to_date, now_datetime


# ── Helpers ──────────────────────────────────────────────────────────


def _make_chart_template(name: str = "Bundle Test Vitals") -> "frappe.Document":
	if frappe.db.exists("IPD Chart Template", name):
		return frappe.get_doc("IPD Chart Template", name)

	doc = frappe.get_doc({
		"doctype": "IPD Chart Template",
		"template_name": name,
		"chart_type": "Vitals",
		"default_frequency_minutes": 60,
		"is_active": 1,
		"parameters": [
			{
				"parameter_name": "Temperature",
				"parameter_type": "Numeric",
				"uom": "°C",
				"is_mandatory": 1,
				"display_order": 10,
			},
		],
	})
	doc.insert(ignore_permissions=True)
	return doc


def _make_protocol_bundle(
	name: str,
	steps: list[dict],
	category: str = "Sepsis",
) -> "frappe.Document":
	if frappe.db.exists("Monitoring Protocol Bundle", name):
		frappe.delete_doc("Monitoring Protocol Bundle", name, force=True)

	doc = frappe.get_doc({
		"doctype": "Monitoring Protocol Bundle",
		"bundle_name": name,
		"bundle_code": name[:10],
		"category": category,
		"is_active": 1,
		"compliance_target_pct": 100,
		"steps": steps,
	})
	doc.insert(ignore_permissions=True)
	return doc


def _make_ir() -> "frappe.Document":
	patient = _ensure_patient()
	ir = frappe.get_doc({
		"doctype": "Inpatient Record",
		"patient": patient.name,
		"company": frappe.defaults.get_defaults().get("company", "_Test Company"),
		"status": "Admitted",
		"scheduled_date": frappe.utils.today(),
	})
	ir.insert(ignore_permissions=True)
	return ir


def _ensure_patient() -> "frappe.Document":
	if frappe.db.exists("Patient", {"patient_name": "_Test Bundle Patient"}):
		return frappe.get_doc("Patient", {"patient_name": "_Test Bundle Patient"})
	p = frappe.get_doc({
		"doctype": "Patient",
		"first_name": "_Test",
		"last_name": "Bundle Patient",
	})
	p.insert(ignore_permissions=True)
	return p


def _simple_steps() -> list[dict]:
	return [
		{
			"step_name": "Blood Culture",
			"step_type": "Lab Order",
			"sequence": 1,
			"is_mandatory": 1,
			"due_within_minutes": 30,
			"compliance_weight": 2.0,
		},
		{
			"step_name": "Lactate",
			"step_type": "Lab Order",
			"sequence": 2,
			"is_mandatory": 1,
			"due_within_minutes": 60,
			"compliance_weight": 1.0,
		},
		{
			"step_name": "Fluid Bolus",
			"step_type": "Task",
			"sequence": 3,
			"is_mandatory": 0,
			"due_within_minutes": 30,
			"compliance_weight": 1.0,
		},
	]


# ── Bundle Validation Tests ─────────────────────────────────────────


class TestBundleValidation:
	def test_requires_steps(self, admin_session):
		doc = frappe.get_doc({
			"doctype": "Monitoring Protocol Bundle",
			"bundle_name": "Empty Bundle",
			"category": "Sepsis",
			"is_active": 1,
		})
		with pytest.raises(frappe.ValidationError, match="at least one"):
			doc.insert(ignore_permissions=True)

	def test_rejects_duplicate_step_names(self, admin_session):
		doc = frappe.get_doc({
			"doctype": "Monitoring Protocol Bundle",
			"bundle_name": "Dup Steps Bundle",
			"category": "Sepsis",
			"is_active": 1,
			"steps": [
				{"step_name": "Blood Culture", "step_type": "Lab Order", "sequence": 1},
				{"step_name": "Blood Culture", "step_type": "Lab Order", "sequence": 2},
			],
		})
		with pytest.raises(frappe.ValidationError, match="Duplicate step name"):
			doc.insert(ignore_permissions=True)

	def test_rejects_duplicate_sequence(self, admin_session):
		doc = frappe.get_doc({
			"doctype": "Monitoring Protocol Bundle",
			"bundle_name": "Dup Seq Bundle",
			"category": "Sepsis",
			"is_active": 1,
			"steps": [
				{"step_name": "Step A", "step_type": "Task", "sequence": 1},
				{"step_name": "Step B", "step_type": "Task", "sequence": 1},
			],
		})
		with pytest.raises(frappe.ValidationError, match="Duplicate sequence"):
			doc.insert(ignore_permissions=True)

	def test_valid_bundle_creation(self, admin_session):
		bundle = _make_protocol_bundle("Valid Bundle", _simple_steps())
		assert bundle.name == "Valid Bundle"
		assert len(bundle.steps) == 3


# ── Activation Tests ────────────────────────────────────────────────


class TestBundleActivation:
	def test_activate_creates_trackers(self, admin_session):
		from alcura_ipd_ext.services.protocol_bundle_service import activate_bundle

		bundle = _make_protocol_bundle("Activate Bundle", _simple_steps())
		ir = _make_ir()

		result = activate_bundle(ir.name, bundle.name)
		assert result["steps_created"] == 3

		doc = frappe.get_doc("Active Protocol Bundle", result["active_bundle"])
		assert doc.status == "Active"
		assert len(doc.step_trackers) == 3

	def test_duplicate_activation_blocked(self, admin_session):
		from alcura_ipd_ext.services.protocol_bundle_service import activate_bundle

		bundle = _make_protocol_bundle("Dup Activate Bundle", _simple_steps())
		ir = _make_ir()

		activate_bundle(ir.name, bundle.name)
		with pytest.raises(frappe.ValidationError, match="already exists"):
			activate_bundle(ir.name, bundle.name)

	def test_activate_auto_starts_chart(self, admin_session):
		from alcura_ipd_ext.services.protocol_bundle_service import activate_bundle

		tmpl = _make_chart_template("Auto Chart Bundle Vitals")
		steps = [
			{
				"step_name": "Monitor Vitals",
				"step_type": "Observation",
				"sequence": 1,
				"is_mandatory": 1,
				"due_within_minutes": 0,
				"chart_template": tmpl.name,
			},
		]
		bundle = _make_protocol_bundle("Chart Activate Bundle", steps)
		ir = _make_ir()

		result = activate_bundle(ir.name, bundle.name)
		assert len(result["charts_started"]) == 1


# ── Step Completion Tests ───────────────────────────────────────────


class TestStepCompletion:
	def test_complete_step(self, admin_session):
		from alcura_ipd_ext.services.protocol_bundle_service import (
			activate_bundle,
			complete_step,
		)

		bundle = _make_protocol_bundle("Complete Step Bundle", _simple_steps())
		ir = _make_ir()
		result = activate_bundle(ir.name, bundle.name)

		comp = complete_step(result["active_bundle"], "Blood Culture")
		assert comp["status"] == "Completed"
		assert comp["compliance_score"] > 0

	def test_complete_already_completed_blocked(self, admin_session):
		from alcura_ipd_ext.services.protocol_bundle_service import (
			activate_bundle,
			complete_step,
		)

		bundle = _make_protocol_bundle("DblComp Bundle", _simple_steps())
		ir = _make_ir()
		result = activate_bundle(ir.name, bundle.name)

		complete_step(result["active_bundle"], "Blood Culture")
		with pytest.raises(frappe.ValidationError, match="already completed"):
			complete_step(result["active_bundle"], "Blood Culture")

	def test_skip_step(self, admin_session):
		from alcura_ipd_ext.services.protocol_bundle_service import (
			activate_bundle,
			skip_step,
		)

		bundle = _make_protocol_bundle("Skip Step Bundle", _simple_steps())
		ir = _make_ir()
		result = activate_bundle(ir.name, bundle.name)

		skip = skip_step(result["active_bundle"], "Fluid Bolus", "Not indicated")
		assert skip["status"] == "Skipped"

	def test_skip_requires_reason(self, admin_session):
		from alcura_ipd_ext.services.protocol_bundle_service import (
			activate_bundle,
			skip_step,
		)

		bundle = _make_protocol_bundle("NoReason Skip Bundle", _simple_steps())
		ir = _make_ir()
		result = activate_bundle(ir.name, bundle.name)

		with pytest.raises(frappe.ValidationError, match="reason"):
			skip_step(result["active_bundle"], "Fluid Bolus", "")


# ── Compliance Scoring Tests ────────────────────────────────────────


class TestComplianceScoring:
	def test_full_compliance(self, admin_session):
		from alcura_ipd_ext.services.protocol_bundle_service import (
			activate_bundle,
			complete_step,
		)

		bundle = _make_protocol_bundle("Full Comply Bundle", _simple_steps())
		ir = _make_ir()
		result = activate_bundle(ir.name, bundle.name)

		complete_step(result["active_bundle"], "Blood Culture")
		complete_step(result["active_bundle"], "Lactate")
		complete_step(result["active_bundle"], "Fluid Bolus")

		doc = frappe.get_doc("Active Protocol Bundle", result["active_bundle"])
		assert doc.compliance_score == 100.0
		assert doc.status == "Completed"

	def test_partial_compliance(self, admin_session):
		from alcura_ipd_ext.services.protocol_bundle_service import (
			activate_bundle,
			complete_step,
		)

		bundle = _make_protocol_bundle("Partial Comply Bundle", _simple_steps())
		ir = _make_ir()
		result = activate_bundle(ir.name, bundle.name)

		complete_step(result["active_bundle"], "Blood Culture")

		doc = frappe.get_doc("Active Protocol Bundle", result["active_bundle"])
		assert 0 < doc.compliance_score < 100


# ── Overdue Detection Tests ─────────────────────────────────────────


class TestOverdueDetection:
	def test_overdue_steps_marked_missed(self, admin_session):
		from alcura_ipd_ext.services.protocol_bundle_service import (
			activate_bundle,
			check_overdue_steps,
		)

		bundle = _make_protocol_bundle("Overdue Bundle", _simple_steps())
		ir = _make_ir()
		result = activate_bundle(ir.name, bundle.name)

		apb = frappe.get_doc("Active Protocol Bundle", result["active_bundle"])
		past = add_to_date(now_datetime(), minutes=-120)
		for step in apb.step_trackers:
			step.due_at = past
		apb.save(ignore_permissions=True)

		missed = check_overdue_steps(result["active_bundle"])
		assert missed >= 2


# ── Discontinue Tests ───────────────────────────────────────────────


class TestDiscontinue:
	def test_discontinue_bundle(self, admin_session):
		from alcura_ipd_ext.services.protocol_bundle_service import (
			activate_bundle,
			discontinue_bundle,
		)

		bundle = _make_protocol_bundle("Disc Bundle", _simple_steps())
		ir = _make_ir()
		result = activate_bundle(ir.name, bundle.name)

		disc = discontinue_bundle(result["active_bundle"], "Patient improved")
		assert disc["status"] == "Discontinued"

	def test_discontinue_requires_reason(self, admin_session):
		from alcura_ipd_ext.services.protocol_bundle_service import (
			activate_bundle,
			discontinue_bundle,
		)

		bundle = _make_protocol_bundle("NoReason Disc Bundle", _simple_steps())
		ir = _make_ir()
		result = activate_bundle(ir.name, bundle.name)

		with pytest.raises(frappe.ValidationError, match="reason"):
			discontinue_bundle(result["active_bundle"], "")


# ── Query Tests ─────────────────────────────────────────────────────


class TestBundleQueries:
	def test_get_bundles_for_ir(self, admin_session):
		from alcura_ipd_ext.services.protocol_bundle_service import (
			activate_bundle,
			get_active_bundles_for_ir,
		)

		bundle = _make_protocol_bundle("Query Bundle", _simple_steps())
		ir = _make_ir()
		activate_bundle(ir.name, bundle.name)

		bundles = get_active_bundles_for_ir(ir.name)
		assert len(bundles) >= 1
		assert bundles[0]["protocol_bundle"] == bundle.name
