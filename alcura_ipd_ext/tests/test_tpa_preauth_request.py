"""Tests for TPA Preauth Request (US-I1).

Covers status transitions, audit field population, validation logic,
and API helpers.
"""

from __future__ import annotations

import frappe
import pytest
from frappe.utils import now_datetime, today

from alcura_ipd_ext.alcura_ipd_ext.doctype.tpa_preauth_request.tpa_preauth_request import (
	VALID_TRANSITIONS,
)

MODULE = "Alcura IPD Extensions"


# ── Fixtures ────────────────────────────────────────────────────────


def _make_patient(suffix: str = "PAR") -> str:
	name = f"_Test Patient {suffix}"
	if frappe.db.exists("Patient", {"patient_name": name}):
		return frappe.db.get_value("Patient", {"patient_name": name}, "name")
	doc = frappe.new_doc("Patient")
	doc.update({"patient_name": name, "sex": "Male", "dob": "1990-01-01"})
	doc.insert(ignore_permissions=True)
	return doc.name


def _make_payer_profile(patient: str, payer_type: str = "Insurance TPA") -> str:
	doc = frappe.new_doc("Patient Payer Profile")
	doc.update({
		"patient": patient,
		"payer_type": payer_type,
		"valid_from": today(),
		"company": frappe.db.get_single_value("Global Defaults", "default_company")
			or "_Test Company",
	})
	if payer_type == "Insurance TPA":
		if frappe.db.exists("Insurance Payor", "_Test Insurer PAR"):
			doc.insurance_payor = "_Test Insurer PAR"
	elif payer_type in ("Corporate", "PSU"):
		if frappe.db.exists("Customer", "_Test Payer Customer PAR"):
			doc.payer = "_Test Payer Customer PAR"
	doc.insert(ignore_permissions=True)
	return doc.name


def _make_preauth(
	patient: str | None = None,
	payer_profile: str | None = None,
	**kwargs,
) -> "frappe.Document":
	patient = patient or _make_patient()
	payer_profile = payer_profile or _make_payer_profile(patient, kwargs.pop("payer_type", "Corporate"))
	company = frappe.db.get_single_value("Global Defaults", "default_company") or "_Test Company"

	doc = frappe.new_doc("TPA Preauth Request")
	doc.update({
		"patient": patient,
		"patient_payer_profile": payer_profile,
		"company": company,
		"primary_diagnosis": "Test Diagnosis",
		"requested_amount": 100000,
		**kwargs,
	})
	doc.insert(ignore_permissions=True)
	return doc


# ── Status Transition Tests ─────────────────────────────────────────


class TestTPAPreauthStatusTransitions:
	def test_draft_to_submitted(self):
		doc = _make_preauth()
		assert doc.status == "Draft"
		doc.action_submit_request()
		doc.reload()
		assert doc.status == "Submitted"
		assert doc.submitted_by == frappe.session.user
		assert doc.submitted_on is not None

	def test_submitted_to_approved(self):
		doc = _make_preauth()
		doc.action_submit_request()
		doc.reload()
		doc.action_approve(approved_amount=80000)
		doc.reload()
		assert doc.status == "Approved"
		assert doc.approved_amount == 80000
		assert doc.approved_by == frappe.session.user

	def test_submitted_to_partially_approved(self):
		doc = _make_preauth()
		doc.action_submit_request()
		doc.reload()
		doc.action_partially_approve(approved_amount=50000)
		doc.reload()
		assert doc.status == "Partially Approved"
		assert doc.approved_amount == 50000

	def test_submitted_to_rejected(self):
		doc = _make_preauth()
		doc.action_submit_request()
		doc.reload()
		doc.action_reject()
		doc.reload()
		assert doc.status == "Rejected"
		assert doc.rejected_by == frappe.session.user

	def test_submitted_to_query_raised(self):
		doc = _make_preauth()
		doc.action_submit_request()
		doc.reload()
		doc.action_raise_query()
		doc.reload()
		assert doc.status == "Query Raised"

	def test_query_raised_to_resubmitted(self):
		doc = _make_preauth()
		doc.action_submit_request()
		doc.reload()
		doc.action_raise_query()
		doc.reload()
		doc.action_resubmit()
		doc.reload()
		assert doc.status == "Resubmitted"

	def test_approved_to_closed(self):
		doc = _make_preauth()
		doc.action_submit_request()
		doc.reload()
		doc.action_approve(approved_amount=80000)
		doc.reload()
		doc.action_close()
		doc.reload()
		assert doc.status == "Closed"
		assert doc.closed_by == frappe.session.user

	def test_invalid_transition_raises(self):
		doc = _make_preauth()
		with pytest.raises(frappe.exceptions.ValidationError):
			doc.action_approve(approved_amount=80000)

	def test_cannot_skip_to_closed_from_draft(self):
		doc = _make_preauth()
		with pytest.raises(frappe.exceptions.ValidationError):
			doc.action_close()

	def test_all_transitions_covered_in_map(self):
		"""Ensure every status has a defined transition entry."""
		all_statuses = {
			"Draft", "Submitted", "Query Raised", "Resubmitted",
			"Approved", "Partially Approved", "Rejected", "Closed",
		}
		assert set(VALID_TRANSITIONS.keys()) == all_statuses


# ── Validation Tests ────────────────────────────────────────────────


class TestTPAPreauthValidation:
	def test_date_range_validation(self):
		with pytest.raises(frappe.exceptions.ValidationError):
			_make_preauth(valid_from="2026-06-01", valid_to="2026-01-01")

	def test_patient_profile_mismatch(self):
		patient_a = _make_patient("PAR-A")
		patient_b = _make_patient("PAR-B")
		profile_a = _make_payer_profile(patient_a, "Corporate")
		with pytest.raises(frappe.exceptions.ValidationError, match="Patient Mismatch"):
			_make_preauth(patient=patient_b, payer_profile=profile_a)

	def test_approved_amount_required_on_approval(self):
		doc = _make_preauth()
		doc.action_submit_request()
		doc.reload()
		doc.approved_amount = 0
		with pytest.raises(frappe.exceptions.ValidationError, match="Approved Amount"):
			doc.action_approve()


# ── Response Metadata Tests ─────────────────────────────────────────


class TestTPAPreauthResponses:
	def test_response_metadata_auto_filled(self):
		doc = _make_preauth()
		doc.append("responses", {
			"response_type": "Query",
			"response_text": "Please provide more details",
		})
		doc.save()
		row = doc.responses[0]
		assert row.response_by == frappe.session.user
		assert row.response_datetime is not None


# ── Audit Trail Tests ───────────────────────────────────────────────


class TestTPAPreauthAudit:
	def test_last_status_change_tracked(self):
		doc = _make_preauth()
		doc.action_submit_request()
		doc.reload()
		assert doc.last_status_change_by == frappe.session.user
		assert doc.last_status_change_on is not None

	def test_timeline_comment_on_patient(self):
		doc = _make_preauth()
		doc.action_submit_request()
		doc.reload()
		comments = frappe.db.get_all(
			"Comment",
			filters={
				"reference_doctype": "Patient",
				"reference_name": doc.patient,
				"comment_type": "Info",
				"content": ["like", f"%{doc.name}%"],
			},
		)
		assert len(comments) >= 1
