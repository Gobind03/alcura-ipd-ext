"""Document event hooks for Patient Encounter (US-E3, US-F1/F2/F3).

Registered in hooks.py doc_events. These handlers fire for ALL Patient
Encounter saves, but only act when the encounter is linked to an
Inpatient Record via ``custom_linked_inpatient_record``.
"""

from __future__ import annotations

from alcura_ipd_ext.services.consultation_note_service import (
	on_submit_consultation_encounter,
	validate_consultation_encounter,
)


def validate(doc: "frappe.Document", method: str) -> None:
	if doc.get("custom_linked_inpatient_record"):
		validate_consultation_encounter(doc)


def on_submit(doc: "frappe.Document", method: str) -> None:
	if doc.get("custom_linked_inpatient_record"):
		on_submit_consultation_encounter(doc)
		_create_clinical_orders(doc)


def _create_clinical_orders(doc: "frappe.Document") -> None:
	"""Auto-create IPD Clinical Orders from prescription child tables."""
	ir = doc.get("custom_linked_inpatient_record")
	if not ir:
		return

	has_prescriptions = (
		doc.get("drug_prescription")
		or doc.get("lab_test_prescription")
		or doc.get("procedure_prescription")
	)
	if not has_prescriptions:
		return

	from alcura_ipd_ext.services.clinical_order_service import create_orders_from_encounter

	create_orders_from_encounter(doc.name)
