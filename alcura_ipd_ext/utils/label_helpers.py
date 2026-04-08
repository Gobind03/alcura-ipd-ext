"""Helpers for generating labels, barcodes, and QR codes for IPD print formats.

These functions are registered as Jinja methods in hooks.py so they can
be called directly from print format templates.
"""

from __future__ import annotations

import base64
import io

import frappe
from frappe.utils import cint, format_date, getdate, now_datetime


def generate_qr_svg(data: str, box_size: int = 3) -> str:
	"""Generate a QR code as an inline SVG data URI.

	Falls back to a placeholder if the ``qrcode`` library is unavailable.

	Args:
		data: The string to encode in the QR code.
		box_size: Size multiplier for QR modules.

	Returns:
		An ``<img>`` tag with a base64-encoded PNG data URI, or a
		placeholder ``<span>`` if qrcode is not installed.
	"""
	try:
		import qrcode
		from qrcode.image.pil import PilImage

		qr = qrcode.QRCode(
			version=1,
			error_correction=qrcode.constants.ERROR_CORRECT_M,
			box_size=box_size,
			border=1,
		)
		qr.add_data(data)
		qr.make(fit=True)

		img = qr.make_image(image_factory=PilImage, fill_color="black", back_color="white")

		buf = io.BytesIO()
		img.save(buf, format="PNG")
		b64 = base64.b64encode(buf.getvalue()).decode("ascii")

		return f'<img src="data:image/png;base64,{b64}" style="width: {box_size * 30}px; height: {box_size * 30}px;" />'
	except ImportError:
		return f'<span style="font-size: 10px; color: #999;">[QR: {frappe.utils.escape_html(data)}]</span>'


def generate_barcode_svg(data: str, barcode_type: str = "code128") -> str:
	"""Generate a barcode as an inline SVG string.

	Falls back to a text placeholder if the ``python-barcode`` library
	is unavailable.

	Args:
		data: The string to encode.
		barcode_type: Barcode symbology (default: code128).

	Returns:
		An inline SVG string or a placeholder ``<span>``.
	"""
	try:
		import barcode
		from barcode.writer import SVGWriter

		bc_class = barcode.get_barcode_class(barcode_type)
		bc = bc_class(data, writer=SVGWriter())

		buf = io.BytesIO()
		bc.write(buf, options={"write_text": False, "module_height": 8.0})
		svg_str = buf.getvalue().decode("utf-8")

		# Strip XML declaration for inline use
		if "<?xml" in svg_str:
			svg_str = svg_str[svg_str.index("<svg"):]

		return svg_str
	except (ImportError, Exception):
		return f'<span style="font-family: monospace; font-size: 12px;">{frappe.utils.escape_html(data)}</span>'


def format_allergy_markers(patient: str) -> str:
	"""Return an HTML snippet showing allergy indicators for a patient.

	Checks the standard ``allergies`` child table on the Patient doctype.

	Args:
		patient: Patient name (doctype key).

	Returns:
		HTML string with allergy markers or empty string if none.
	"""
	if not patient:
		return ""

	allergies = frappe.get_all(
		"Patient Medical Record",
		filters={"parent": patient, "parentfield": "medical_history"},
		fields=["entry"],
		limit=0,
	)

	# Also try the standard allergies field structure
	patient_doc = frappe.get_doc("Patient", patient)
	allergy_list = []

	if hasattr(patient_doc, "allergies") and patient_doc.allergies:
		for a in patient_doc.allergies:
			allergy_list.append(a.get("allergen") or a.get("allergy") or str(a))

	if not allergy_list:
		return ""

	items = ", ".join(allergy_list[:5])
	extra = f" (+{len(allergy_list) - 5} more)" if len(allergy_list) > 5 else ""

	return (
		f'<span style="color: #d32f2f; font-weight: bold;">'
		f'ALLERGIES: {frappe.utils.escape_html(items)}{extra}'
		f'</span>'
	)


def get_admission_label_context(inpatient_record: str) -> dict:
	"""Build the full context dict needed by all admission label print formats.

	Aggregates data from Inpatient Record, Patient, and bed hierarchy.

	Args:
		inpatient_record: Name of the Inpatient Record.

	Returns:
		Dict with all label-relevant fields.
	"""
	ir = frappe.get_doc("Inpatient Record", inpatient_record)

	patient = frappe.get_doc("Patient", ir.patient) if ir.patient else frappe._dict()

	age = _compute_age(patient)

	practitioner_name = ""
	if ir.primary_practitioner:
		practitioner_name = frappe.db.get_value(
			"Healthcare Practitioner",
			ir.primary_practitioner,
			"practitioner_name",
		) or ir.primary_practitioner

	bed_label = ""
	if ir.get("custom_current_bed"):
		bed_label = frappe.db.get_value(
			"Hospital Bed", ir.custom_current_bed, "bed_label"
		) or ir.custom_current_bed

	ward_name = ""
	if ir.get("custom_current_ward"):
		ward_name = frappe.db.get_value(
			"Hospital Ward", ir.custom_current_ward, "ward_name"
		) or ir.custom_current_ward

	room_name = ""
	if ir.get("custom_current_room"):
		room_name = frappe.db.get_value(
			"Hospital Room", ir.custom_current_room, "room_name"
		) or ir.custom_current_room

	payer_display = ir.get("custom_payer_display") or ir.get("custom_payer_type") or "Cash"

	bedside_url = f"/bedside_profile?ir={inpatient_record}"

	return {
		"ir_name": ir.name,
		"patient_name": ir.patient_name or patient.get("patient_name", ""),
		"patient_id": ir.patient,
		"mr_number": patient.get("custom_mr_number", ""),
		"sex": patient.get("sex", ""),
		"dob": format_date(patient.get("dob")) if patient.get("dob") else "",
		"age": age,
		"blood_group": patient.get("blood_group", ""),
		"mobile": patient.get("mobile", ""),
		"practitioner": practitioner_name,
		"medical_department": ir.medical_department or "",
		"bed": ir.get("custom_current_bed", ""),
		"bed_label": bed_label,
		"room": ir.get("custom_current_room", ""),
		"room_name": room_name,
		"ward": ir.get("custom_current_ward", ""),
		"ward_name": ward_name,
		"admission_date": format_date(ir.admitted_datetime) if ir.admitted_datetime else "",
		"admission_priority": ir.get("custom_admission_priority", ""),
		"payer_display": payer_display,
		"allergy_html": format_allergy_markers(ir.patient),
		"bedside_url": bedside_url,
		"company": ir.company or "",
		"qr_code": generate_qr_svg(bedside_url, box_size=3),
		"barcode": generate_barcode_svg(ir.name),
	}


def _compute_age(patient) -> str:
	"""Compute a human-readable age string from patient DOB."""
	dob = patient.get("dob") if patient else None
	if not dob:
		return ""

	try:
		from frappe.utils import date_diff
		dob_date = getdate(dob)
		today = getdate(now_datetime())
		years = date_diff(today, dob_date) // 365
		return f"{years}Y"
	except Exception:
		return ""
