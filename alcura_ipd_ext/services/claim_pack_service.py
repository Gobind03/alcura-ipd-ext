"""TPA claim pack generation service.

Provides domain logic for creating claim packs with auto-populated
document checklists, checking document availability, and identifying
pending documents.
"""

from __future__ import annotations

import frappe
from frappe import _

# Standard document types for a TPA claim pack
_STANDARD_DOCUMENTS: list[dict] = [
	{"document_type": "Final Bill", "is_mandatory": 1, "description": "Final hospital bill"},
	{"document_type": "Bill Break-Up", "is_mandatory": 1, "description": "Itemized bill break-up"},
	{"document_type": "Discharge Summary", "is_mandatory": 1, "description": "Clinical discharge summary"},
	{"document_type": "Investigation Report", "is_mandatory": 0, "description": "Lab and radiology reports"},
	{"document_type": "Operative Notes", "is_mandatory": 0, "description": "Surgical / procedure notes"},
	{"document_type": "Implant Sticker", "is_mandatory": 0, "description": "Implant sticker / invoice"},
	{"document_type": "Pharmacy Summary", "is_mandatory": 0, "description": "Pharmacy consumption summary"},
	{"document_type": "Preauth Approval", "is_mandatory": 1, "description": "TPA pre-authorization approval letter"},
	{"document_type": "Consent Form", "is_mandatory": 1, "description": "Patient consent form"},
	{"document_type": "ID Proof", "is_mandatory": 1, "description": "Patient / policyholder ID proof"},
]


@frappe.whitelist()
def create_claim_pack(inpatient_record: str) -> str:
	"""Create a TPA Claim Pack with auto-populated document checklist.

	Returns the name of the created claim pack.
	"""
	ir = frappe.get_doc("Inpatient Record", inpatient_record)
	payer_profile = ir.get("custom_patient_payer_profile")

	insurance_payor = None
	if payer_profile:
		insurance_payor = frappe.db.get_value(
			"Patient Payer Profile", payer_profile, "insurance_payor"
		)

	preauth = frappe.db.get_value(
		"TPA Preauth Request",
		{"inpatient_record": inpatient_record},
		"name",
		order_by="creation desc",
	)

	doc = frappe.new_doc("TPA Claim Pack")
	doc.update({
		"inpatient_record": inpatient_record,
		"patient": ir.patient,
		"patient_payer_profile": payer_profile or "",
		"insurance_payor": insurance_payor or "",
		"company": ir.company,
		"tpa_preauth_request": preauth or "",
	})

	for doc_def in _STANDARD_DOCUMENTS:
		doc.append("documents", {
			**doc_def,
			"is_available": 0,
		})

	doc.insert(ignore_permissions=True)

	# Link to IR
	frappe.db.set_value(
		"Inpatient Record", inpatient_record,
		"custom_claim_pack", doc.name,
		update_modified=False,
	)

	return doc.name


def refresh_document_availability(claim_pack_name: str):
	"""Check which documents have attachments and update is_available."""
	doc = frappe.get_doc("TPA Claim Pack", claim_pack_name)

	for row in doc.documents:
		row.is_available = 1 if row.file_attachment else 0

	doc.save(ignore_permissions=True)


def get_pending_documents(claim_pack_name: str) -> list[dict]:
	"""Return list of mandatory documents not yet attached."""
	doc = frappe.get_doc("TPA Claim Pack", claim_pack_name)

	return [
		{
			"document_type": row.document_type,
			"description": row.description,
			"is_mandatory": row.is_mandatory,
		}
		for row in doc.documents
		if row.is_mandatory and not row.is_available and not row.file_attachment
	]
