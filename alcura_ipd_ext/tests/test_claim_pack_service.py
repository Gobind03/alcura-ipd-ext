"""Tests for TPA Claim Pack service (US-I5).

Covers claim pack creation, document availability refresh,
pending document detection, and status transitions.
"""

from __future__ import annotations

import frappe
import pytest
from frappe.utils import today

from alcura_ipd_ext.alcura_ipd_ext.doctype.tpa_claim_pack.tpa_claim_pack import (
	VALID_TRANSITIONS,
)
from alcura_ipd_ext.services.claim_pack_service import (
	get_pending_documents,
	refresh_document_availability,
)


def _get_company() -> str:
	return frappe.db.get_single_value("Global Defaults", "default_company") or "_Test Company"


def _make_claim_pack(**kwargs) -> "frappe.Document":
	doc = frappe.new_doc("TPA Claim Pack")
	doc.update({
		"inpatient_record": kwargs.get("inpatient_record", "_Test IR CP"),
		"patient": kwargs.get("patient", "_Test Patient CP"),
		"company": _get_company(),
		**kwargs,
	})
	doc.append("documents", {
		"document_type": "Final Bill",
		"is_mandatory": 1,
		"is_available": 0,
		"description": "Final bill",
	})
	doc.append("documents", {
		"document_type": "Discharge Summary",
		"is_mandatory": 1,
		"is_available": 0,
		"description": "Discharge summary",
	})
	doc.append("documents", {
		"document_type": "Implant Sticker",
		"is_mandatory": 0,
		"is_available": 0,
		"description": "Implant sticker",
	})
	doc.insert(ignore_permissions=True)
	return doc


class TestTPAClaimPackTransitions:
	def test_draft_to_in_review(self):
		doc = _make_claim_pack()
		assert doc.status == "Draft"
		doc.action_send_for_review()
		doc.reload()
		assert doc.status == "In Review"
		assert doc.reviewed_by == frappe.session.user

	def test_in_review_to_submitted(self):
		doc = _make_claim_pack()
		doc.action_send_for_review()
		doc.reload()
		doc.action_mark_submitted()
		doc.reload()
		assert doc.status == "Submitted"
		assert doc.submitted_by_user == frappe.session.user

	def test_submitted_to_acknowledged(self):
		doc = _make_claim_pack()
		doc.action_send_for_review()
		doc.reload()
		doc.action_mark_submitted()
		doc.reload()
		doc.action_mark_acknowledged()
		doc.reload()
		assert doc.status == "Acknowledged"

	def test_acknowledged_to_settled(self):
		doc = _make_claim_pack()
		doc.action_send_for_review()
		doc.reload()
		doc.action_mark_submitted()
		doc.reload()
		doc.action_mark_acknowledged()
		doc.reload()
		doc.action_mark_settled(settlement_amount=50000, settlement_reference="REF-001")
		doc.reload()
		assert doc.status == "Settled"
		assert doc.settlement_amount == 50000

	def test_invalid_transition(self):
		doc = _make_claim_pack()
		with pytest.raises(frappe.exceptions.ValidationError):
			doc.action_mark_submitted()

	def test_disputed_to_resubmit(self):
		doc = _make_claim_pack()
		doc.action_send_for_review()
		doc.reload()
		doc.action_mark_submitted()
		doc.reload()
		doc.action_mark_disputed(disallowance_amount=5000, reason="Missing docs")
		doc.reload()
		assert doc.status == "Disputed"
		doc.action_mark_submitted()
		doc.reload()
		assert doc.status == "Submitted"


class TestTPAClaimPackDocuments:
	def test_pending_documents(self):
		doc = _make_claim_pack()
		pending = get_pending_documents(doc.name)
		mandatory_types = [d["document_type"] for d in pending]
		assert "Final Bill" in mandatory_types
		assert "Discharge Summary" in mandatory_types
		# Non-mandatory should not appear
		assert "Implant Sticker" not in mandatory_types

	def test_refresh_availability_with_attachment(self):
		doc = _make_claim_pack()
		# Simulate attaching a file
		doc.documents[0].file_attachment = "/files/test_bill.pdf"
		doc.save(ignore_permissions=True)
		refresh_document_availability(doc.name)
		doc.reload()
		assert doc.documents[0].is_available == 1
		assert doc.documents[1].is_available == 0

	def test_all_transitions_covered(self):
		all_statuses = {"Draft", "In Review", "Submitted", "Acknowledged", "Settled", "Disputed"}
		assert set(VALID_TRANSITIONS.keys()) == all_statuses
