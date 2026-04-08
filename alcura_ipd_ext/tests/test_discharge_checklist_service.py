"""Tests for discharge billing checklist service (US-I4).

Covers checklist creation, auto-check derivation, manual clearance,
waivers, overrides, and discharge readiness validation.
"""

from __future__ import annotations

import frappe
import pytest
from frappe.utils import today

from alcura_ipd_ext.services.discharge_checklist_service import (
	_check_pending_meds,
	_check_pending_samples,
	_check_room_rent_closed,
	_check_tpa_preauth,
	_check_unposted_procedures,
	create_discharge_checklist,
	validate_discharge_ready,
)


# ── Auto-check unit tests (no IR needed) ───────────────────────────


class TestAutoCheckFunctions:
	def test_pending_meds_no_ir(self):
		is_clear, detail = _check_pending_meds("NON-EXISTENT-IR")
		assert is_clear is True
		assert "No pending" in detail

	def test_pending_samples_no_ir(self):
		is_clear, detail = _check_pending_samples("NON-EXISTENT-IR")
		assert is_clear is True

	def test_unposted_procedures_no_ir(self):
		is_clear, detail = _check_unposted_procedures("NON-EXISTENT-IR")
		assert is_clear is True

	def test_room_rent_closed_no_ir(self):
		is_clear, detail = _check_room_rent_closed("NON-EXISTENT-IR")
		assert is_clear is False
		assert "discharge movement" in detail.lower()

	def test_tpa_preauth_no_ir(self):
		is_clear, detail = _check_tpa_preauth("NON-EXISTENT-IR")
		assert is_clear is True
		assert "No preauth" in detail


# ── Discharge readiness validation ──────────────────────────────────


class TestDischargeReadiness:
	def test_no_checklist_returns_not_ready(self):
		result = validate_discharge_ready("NON-EXISTENT-IR")
		assert result["ready"] is False
		assert result["status"] == "No Checklist"


# ── DocType controller tests ───────────────────────────────────────


class TestDischargeBillingChecklist:
	def test_status_cleared_when_all_items_cleared(self):
		doc = frappe.new_doc("Discharge Billing Checklist")
		doc.update({
			"inpatient_record": "_Test IR",
			"patient": "_Test Patient",
			"company": frappe.db.get_single_value("Global Defaults", "default_company")
				or "_Test Company",
		})
		doc.append("items", {
			"check_name": "Test Check",
			"check_category": "Clinical",
			"check_status": "Cleared",
		})
		doc._update_status()
		assert doc.status == "Cleared"

	def test_status_pending_when_items_pending(self):
		doc = frappe.new_doc("Discharge Billing Checklist")
		doc.update({
			"inpatient_record": "_Test IR 2",
			"patient": "_Test Patient",
			"company": frappe.db.get_single_value("Global Defaults", "default_company")
				or "_Test Company",
		})
		doc.append("items", {
			"check_name": "Check 1",
			"check_category": "Clinical",
			"check_status": "Cleared",
		})
		doc.append("items", {
			"check_name": "Check 2",
			"check_category": "Financial",
			"check_status": "Pending",
		})
		doc._update_status()
		assert doc.status == "In Progress"

	def test_waiver_requires_reason(self):
		doc = frappe.new_doc("Discharge Billing Checklist")
		doc.update({
			"inpatient_record": "_Test IR 3",
			"patient": "_Test Patient",
			"company": frappe.db.get_single_value("Global Defaults", "default_company")
				or "_Test Company",
		})
		doc.append("items", {
			"check_name": "Check 1",
			"check_category": "Clinical",
			"check_status": "Waived",
			"waiver_reason": "",
		})
		with pytest.raises(frappe.exceptions.ValidationError, match="Waiver reason"):
			doc._validate_waiver_reasons()
