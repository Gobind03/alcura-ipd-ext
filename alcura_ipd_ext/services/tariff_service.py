"""Tariff resolution service for IPD billing.

Resolves the best-matching Room Tariff Mapping for a given room type,
payer combination, and effective date.  Resolution priority:

1. **Exact match** — room_type + payer_type + specific payer + date
2. **Generic payer** — room_type + payer_type + no payer + date
3. **Cash fallback** — room_type + Cash + date (when payer_type != Cash)

All query helpers use indexed fields and avoid N+1 patterns.
"""

from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import getdate, today


# ── public API ──────────────────────────────────────────────────────


@frappe.whitelist()
def resolve_tariff(
	room_type: str,
	payer_type: str,
	payer: str | None = None,
	effective_date: str | None = None,
	company: str | None = None,
	charge_type: str | None = None,
) -> dict | None:
	"""Return the best-matching tariff mapping as a dict, or ``None``.

	The returned dict contains:
	- ``name``: Room Tariff Mapping name
	- ``price_list``: linked Price List
	- ``tariff_items``: list of child-row dicts (optionally filtered by
	  *charge_type* when provided)
	"""
	effective_date = getdate(effective_date or today())
	company = company or frappe.defaults.get_user_default("company")

	# Priority 1: exact match (specific payer)
	if payer:
		result = _find_mapping(room_type, payer_type, payer, effective_date, company)
		if result:
			return _format_result(result, charge_type)

	# Priority 2: generic payer (payer_type match, no specific payer)
	result = _find_mapping(room_type, payer_type, None, effective_date, company)
	if result:
		return _format_result(result, charge_type)

	# Priority 3: Cash fallback
	if payer_type != "Cash":
		result = _find_mapping(room_type, "Cash", None, effective_date, company)
		if result:
			return _format_result(result, charge_type)

	return None


@frappe.whitelist()
def get_tariff_rate(
	room_type: str,
	charge_type: str,
	payer_type: str = "Cash",
	payer: str | None = None,
	effective_date: str | None = None,
	company: str | None = None,
) -> float:
	"""Return the rate for a specific charge type, or ``0.0`` if unresolved."""
	result = resolve_tariff(
		room_type=room_type,
		payer_type=payer_type,
		payer=payer,
		effective_date=effective_date,
		company=company,
		charge_type=charge_type,
	)
	if not result or not result.get("tariff_items"):
		return 0.0

	return float(result["tariff_items"][0].get("rate", 0))


@frappe.whitelist()
def resolve_tariff_for_profile(
	room_type: str,
	patient_payer_profile: str,
	effective_date: str | None = None,
	company: str | None = None,
	charge_type: str | None = None,
) -> dict | None:
	"""Resolve tariff using a Patient Payer Profile for payer details."""
	profile = frappe.db.get_value(
		"Patient Payer Profile",
		patient_payer_profile,
		["payer_type", "payer", "insurance_payor"],
		as_dict=True,
	)
	if not profile:
		return None

	payer = profile.payer or None
	if profile.payer_type == "Insurance TPA" and profile.insurance_payor:
		payer_customer = frappe.db.get_value(
			"Insurance Payor", profile.insurance_payor, "customer"
		)
		if payer_customer:
			payer = payer_customer

	return resolve_tariff(
		room_type=room_type,
		payer_type=profile.payer_type,
		payer=payer,
		effective_date=effective_date,
		company=company,
		charge_type=charge_type,
	)


# ── internal helpers ────────────────────────────────────────────────


def _find_mapping(
	room_type: str,
	payer_type: str,
	payer: str | None,
	effective_date,
	company: str | None,
) -> dict | None:
	"""Find a single active Room Tariff Mapping matching the given criteria.

	Date-range logic: valid_from <= effective_date AND
	(valid_to IS NULL OR valid_to >= effective_date).
	"""
	filters = {
		"room_type": room_type,
		"payer_type": payer_type,
		"is_active": 1,
		"valid_from": ("<=", effective_date),
	}

	if payer:
		filters["payer"] = payer
	else:
		filters["payer"] = ("is", "not set")

	if company:
		filters["company"] = company

	# Fetch candidates; valid_to check needs OR-style logic
	mappings = frappe.db.get_all(
		"Room Tariff Mapping",
		filters=filters,
		fields=["name", "price_list", "valid_from", "valid_to"],
		order_by="valid_from desc",
	)

	for mapping in mappings:
		if mapping.valid_to is None or getdate(mapping.valid_to) >= effective_date:
			return mapping

	return None


def _format_result(mapping: dict, charge_type: str | None) -> dict:
	"""Build the return dict with tariff items from the matched mapping."""
	item_filters = {"parent": mapping.name}
	if charge_type:
		item_filters["charge_type"] = charge_type

	items = frappe.db.get_all(
		"Room Tariff Item",
		filters=item_filters,
		fields=[
			"charge_type",
			"item_code",
			"item_name",
			"rate",
			"uom",
			"billing_frequency",
			"description",
		],
		order_by="idx asc",
	)

	return {
		"name": mapping.name,
		"price_list": mapping.price_list,
		"valid_from": str(mapping.valid_from),
		"valid_to": str(mapping.valid_to) if mapping.valid_to else None,
		"tariff_items": items,
	}
