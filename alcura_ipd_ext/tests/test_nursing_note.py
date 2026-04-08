"""Tests for nursing note creation, validation, and addendum flow (US-E4)."""

from __future__ import annotations

import frappe
import pytest
from frappe.utils import now_datetime


# ── Helpers ──────────────────────────────────────────────────────────


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
	if frappe.db.exists("Patient", {"patient_name": "_Test Note Patient"}):
		return frappe.get_doc("Patient", {"patient_name": "_Test Note Patient"})
	p = frappe.get_doc({
		"doctype": "Patient",
		"first_name": "_Test",
		"last_name": "Note Patient",
	})
	p.insert(ignore_permissions=True)
	return p


def _make_note(ir, **kwargs):
	defaults = {
		"doctype": "IPD Nursing Note",
		"patient": ir.patient,
		"inpatient_record": ir.name,
		"note_datetime": now_datetime(),
		"category": "General",
		"note_text": "Patient resting comfortably.",
		"urgency": "Routine",
	}
	defaults.update(kwargs)
	doc = frappe.get_doc(defaults)
	doc.insert(ignore_permissions=True)
	return doc


# ── Validation Tests ────────────────────────────────────────────────


class TestNursingNoteValidation:
	def test_note_text_required(self, admin_session):
		ir = _make_ir()
		doc = frappe.get_doc({
			"doctype": "IPD Nursing Note",
			"patient": ir.patient,
			"inpatient_record": ir.name,
			"note_datetime": now_datetime(),
			"category": "General",
			"note_text": "",
			"urgency": "Routine",
		})
		with pytest.raises(frappe.ValidationError, match="Note text"):
			doc.insert(ignore_permissions=True)

	def test_valid_note_creation(self, admin_session):
		ir = _make_ir()
		note = _make_note(ir)
		assert note.status == "Active"
		assert note.recorded_by is not None


# ── Addendum Tests ──────────────────────────────────────────────────


class TestNursingNoteAddendum:
	def test_addendum_marks_original(self, admin_session):
		ir = _make_ir()
		original = _make_note(ir)

		addendum = _make_note(
			ir,
			is_addendum=1,
			addendum_to=original.name,
			addendum_reason="Additional observation",
			note_text="Patient also reports mild headache.",
		)

		original.reload()
		assert original.status == "Amended"
		assert addendum.is_addendum
		assert addendum.addendum_to == original.name

	def test_addendum_requires_reason(self, admin_session):
		ir = _make_ir()
		original = _make_note(ir)

		doc = frappe.get_doc({
			"doctype": "IPD Nursing Note",
			"patient": ir.patient,
			"inpatient_record": ir.name,
			"note_datetime": now_datetime(),
			"category": "General",
			"note_text": "Addendum text.",
			"urgency": "Routine",
			"is_addendum": 1,
			"addendum_to": original.name,
			"addendum_reason": "",
		})
		with pytest.raises(frappe.ValidationError, match="addendum reason"):
			doc.insert(ignore_permissions=True)

	def test_double_addendum_blocked(self, admin_session):
		ir = _make_ir()
		original = _make_note(ir)

		_make_note(
			ir,
			is_addendum=1,
			addendum_to=original.name,
			addendum_reason="First addendum",
			note_text="First addendum text.",
		)

		doc = frappe.get_doc({
			"doctype": "IPD Nursing Note",
			"patient": ir.patient,
			"inpatient_record": ir.name,
			"note_datetime": now_datetime(),
			"category": "General",
			"note_text": "Second addendum.",
			"urgency": "Routine",
			"is_addendum": 1,
			"addendum_to": original.name,
			"addendum_reason": "Second addendum",
		})
		with pytest.raises(frappe.ValidationError, match="already been amended"):
			doc.insert(ignore_permissions=True)


# ── Urgency Tests ───────────────────────────────────────────────────


class TestNursingNoteUrgency:
	def test_critical_note_accepted(self, admin_session):
		ir = _make_ir()
		note = _make_note(
			ir,
			urgency="Critical",
			category="Escalation",
			note_text="Patient condition deteriorating rapidly.",
		)
		assert note.urgency == "Critical"
