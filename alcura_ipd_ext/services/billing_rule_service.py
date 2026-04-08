"""Payer billing rule resolution service.

Resolves applicable billing rules for a patient's payer profile and
computes payer vs patient liability splits for individual line items
and full bills.

Resolution priority:
1. Item is non-payable or excluded consumable → full patient liability
2. Item is a package inclusion → zero separate charge
3. Sub-limit for charge category → cap cumulative payer amount at sub-limit
4. Co-pay (item-level override or profile-level default)
5. Deductible (profile-level, applied once across the bill)
6. Room rent cap → proportional deduction if actual room exceeds entitlement
"""

from __future__ import annotations

from dataclasses import dataclass, field

import frappe
from frappe.utils import flt, getdate, today


@dataclass
class ResolvedRules:
	"""Container for resolved billing rules from all levels."""

	non_payable_items: set[str] = field(default_factory=set)
	non_payable_item_groups: set[str] = field(default_factory=set)
	non_payable_categories: set[str] = field(default_factory=set)
	excluded_consumables: set[str] = field(default_factory=set)
	excluded_consumable_groups: set[str] = field(default_factory=set)
	package_inclusions: set[str] = field(default_factory=set)
	package_inclusion_groups: set[str] = field(default_factory=set)
	co_pay_overrides: dict[str, float] = field(default_factory=dict)
	sub_limits: dict[str, float] = field(default_factory=dict)
	room_rent_cap: float = 0.0
	default_co_pay_percent: float = 0.0
	deductible_amount: float = 0.0
	preauth_approved_amount: float = 0.0


@dataclass
class LineSplit:
	"""Payer/patient/excluded split for a single line item."""

	gross_amount: float = 0.0
	payer_amount: float = 0.0
	patient_amount: float = 0.0
	excluded_amount: float = 0.0
	rule_applied: str = ""


def resolve_billing_rules(
	patient_payer_profile: str,
	company: str | None = None,
	preauth_name: str | None = None,
) -> ResolvedRules:
	"""Resolve applicable billing rules from rule set + profile + preauth.

	Layer 1: Payer Billing Rule Set (by payer type/payer/insurer)
	Layer 2: Patient Payer Profile (co-pay %, deductible)
	Layer 3: TPA Preauth Request (approved amount, if any)
	"""
	rules = ResolvedRules()

	profile = frappe.db.get_value(
		"Patient Payer Profile",
		patient_payer_profile,
		["payer_type", "payer", "insurance_payor", "co_pay_percent",
		 "deductible_amount", "company"],
		as_dict=True,
	)
	if not profile:
		return rules

	rules.default_co_pay_percent = flt(profile.co_pay_percent)
	rules.deductible_amount = flt(profile.deductible_amount)
	company = company or profile.company

	rule_set = _find_rule_set(profile, company)
	if rule_set:
		_apply_rule_set(rule_set, rules)

	if preauth_name:
		approved = frappe.db.get_value(
			"TPA Preauth Request", preauth_name, "approved_amount"
		)
		rules.preauth_approved_amount = flt(approved)

	return rules


def compute_line_split(
	item_code: str | None,
	item_group: str | None,
	charge_category: str,
	gross_amount: float,
	rules: ResolvedRules,
) -> LineSplit:
	"""Compute payer/patient/excluded split for a single line item."""
	gross = flt(gross_amount)
	split = LineSplit(gross_amount=gross)

	if _is_non_payable(item_code, item_group, charge_category, rules):
		split.patient_amount = gross
		split.rule_applied = "Non-Payable"
		return split

	if _is_excluded_consumable(item_code, item_group, rules):
		split.excluded_amount = gross
		split.patient_amount = gross
		split.rule_applied = "Excluded Consumable"
		return split

	if _is_package_inclusion(item_code, item_group, rules):
		split.rule_applied = "Package Inclusion"
		return split

	co_pay = _get_co_pay_percent(item_code, rules)
	patient_share = gross * co_pay / 100
	payer_share = gross - patient_share

	split.payer_amount = payer_share
	split.patient_amount = patient_share
	split.rule_applied = f"Co-Pay {co_pay}%"

	return split


def compute_bill_split(
	line_items: list[dict],
	patient_payer_profile: str,
	company: str | None = None,
	preauth_name: str | None = None,
) -> dict:
	"""Apply rules across all line items.

	Each line_item dict must have: item_code, item_group, charge_category,
	gross_amount. Optional: description, qty, rate.

	Returns dict with:
	- lines: list of dicts with per-line split
	- category_subtotals: dict of charge_category -> subtotal
	- gross_total, payer_total, patient_total, excluded_total
	- deductible_applied
	- preauth_approved_amount
	- preauth_overshoot (payer_total - approved, if positive)
	"""
	rules = resolve_billing_rules(patient_payer_profile, company, preauth_name)

	lines = []
	category_payer_totals: dict[str, float] = {}
	gross_total = 0.0
	payer_total = 0.0
	patient_total = 0.0
	excluded_total = 0.0

	for item in line_items:
		split = compute_line_split(
			item_code=item.get("item_code"),
			item_group=item.get("item_group"),
			charge_category=item.get("charge_category", "Other"),
			gross_amount=flt(item.get("gross_amount", 0)),
			rules=rules,
		)

		cat = item.get("charge_category", "Other")
		category_payer_totals.setdefault(cat, 0.0)
		category_payer_totals[cat] += split.payer_amount

		# Apply sub-limit per category
		sub_limit = rules.sub_limits.get(cat, 0)
		if sub_limit and category_payer_totals[cat] > sub_limit:
			excess = category_payer_totals[cat] - sub_limit
			split.payer_amount = max(0, split.payer_amount - excess)
			split.patient_amount += excess
			split.rule_applied += f" + Sub-Limit {cat}"
			category_payer_totals[cat] = sub_limit

		# Apply room rent cap
		if cat == "Room Rent" and rules.room_rent_cap:
			if split.payer_amount > rules.room_rent_cap:
				excess = split.payer_amount - rules.room_rent_cap
				split.payer_amount = rules.room_rent_cap
				split.patient_amount += excess
				split.rule_applied += " + Room Rent Cap"

		gross_total += split.gross_amount
		payer_total += split.payer_amount
		patient_total += split.patient_amount
		excluded_total += split.excluded_amount

		lines.append({
			**item,
			"payer_amount": split.payer_amount,
			"patient_amount": split.patient_amount,
			"excluded_amount": split.excluded_amount,
			"rule_applied": split.rule_applied,
		})

	# Apply deductible (reduces payer total, increases patient total)
	deductible_applied = 0.0
	if rules.deductible_amount and payer_total > 0:
		deductible_applied = min(rules.deductible_amount, payer_total)
		payer_total -= deductible_applied
		patient_total += deductible_applied

	preauth_overshoot = 0.0
	if rules.preauth_approved_amount and payer_total > rules.preauth_approved_amount:
		preauth_overshoot = payer_total - rules.preauth_approved_amount

	return {
		"lines": lines,
		"category_subtotals": category_payer_totals,
		"gross_total": gross_total,
		"payer_total": payer_total,
		"patient_total": patient_total,
		"excluded_total": excluded_total,
		"deductible_applied": deductible_applied,
		"preauth_approved_amount": rules.preauth_approved_amount,
		"preauth_overshoot": preauth_overshoot,
	}


# ── Internal helpers ────────────────────────────────────────────────


def _find_rule_set(profile: dict, company: str) -> str | None:
	"""Find the best-matching active rule set for the given payer profile.

	Priority: specific payer > payer type only > no match.
	"""
	effective_date = getdate(today())
	base_filters = {
		"is_active": 1,
		"company": company,
		"valid_from": ("<=", effective_date),
	}

	# Try specific payer first
	payer_field = None
	payer_value = None
	if profile.payer_type in ("Corporate", "PSU") and profile.payer:
		payer_field = "payer"
		payer_value = profile.payer
	elif profile.payer_type == "Insurance TPA" and profile.insurance_payor:
		payer_field = "insurance_payor"
		payer_value = profile.insurance_payor

	if payer_field and payer_value:
		filters = {**base_filters, "payer_type": profile.payer_type, payer_field: payer_value}
		result = _query_rule_set(filters, effective_date)
		if result:
			return result

	# Try payer type only (no specific payer)
	filters = {
		**base_filters,
		"payer_type": profile.payer_type,
		"payer": ("is", "not set"),
		"insurance_payor": ("is", "not set"),
	}
	result = _query_rule_set(filters, effective_date)
	if result:
		return result

	return None


def _query_rule_set(filters: dict, effective_date) -> str | None:
	sets = frappe.db.get_all(
		"Payer Billing Rule Set",
		filters=filters,
		fields=["name", "valid_to"],
		order_by="valid_from desc",
	)
	for s in sets:
		if s.valid_to is None or getdate(s.valid_to) >= effective_date:
			return s.name
	return None


def _apply_rule_set(rule_set_name: str, rules: ResolvedRules):
	"""Populate ResolvedRules from a Payer Billing Rule Set's child rows."""
	items = frappe.db.get_all(
		"Payer Billing Rule Item",
		filters={"parent": rule_set_name},
		fields=["rule_type", "applies_to", "item_code", "item_group",
				"charge_category", "co_pay_percent", "sub_limit_amount", "cap_amount"],
		order_by="idx asc",
	)
	for row in items:
		rt = row.rule_type
		key = row.item_code or row.item_group or row.charge_category or ""

		if rt == "Non-Payable":
			if row.applies_to == "Item":
				rules.non_payable_items.add(row.item_code)
			elif row.applies_to == "Item Group":
				rules.non_payable_item_groups.add(row.item_group)
			elif row.applies_to == "Charge Category":
				rules.non_payable_categories.add(row.charge_category)

		elif rt == "Excluded Consumable":
			if row.applies_to == "Item":
				rules.excluded_consumables.add(row.item_code)
			elif row.applies_to == "Item Group":
				rules.excluded_consumable_groups.add(row.item_group)

		elif rt == "Package Inclusion":
			if row.applies_to == "Item":
				rules.package_inclusions.add(row.item_code)
			elif row.applies_to == "Item Group":
				rules.package_inclusion_groups.add(row.item_group)

		elif rt == "Co-Pay Override":
			rules.co_pay_overrides[key] = flt(row.co_pay_percent)

		elif rt == "Sub-Limit":
			if row.charge_category:
				rules.sub_limits[row.charge_category] = flt(row.sub_limit_amount)

		elif rt == "Room Rent Cap":
			rules.room_rent_cap = flt(row.cap_amount)


def _is_non_payable(item_code: str | None, item_group: str | None,
					charge_category: str, rules: ResolvedRules) -> bool:
	if item_code and item_code in rules.non_payable_items:
		return True
	if item_group and item_group in rules.non_payable_item_groups:
		return True
	if charge_category and charge_category in rules.non_payable_categories:
		return True
	return False


def _is_excluded_consumable(item_code: str | None, item_group: str | None,
							rules: ResolvedRules) -> bool:
	if item_code and item_code in rules.excluded_consumables:
		return True
	if item_group and item_group in rules.excluded_consumable_groups:
		return True
	return False


def _is_package_inclusion(item_code: str | None, item_group: str | None,
						  rules: ResolvedRules) -> bool:
	if item_code and item_code in rules.package_inclusions:
		return True
	if item_group and item_group in rules.package_inclusion_groups:
		return True
	return False


def _get_co_pay_percent(item_code: str | None, rules: ResolvedRules) -> float:
	if item_code and item_code in rules.co_pay_overrides:
		return rules.co_pay_overrides[item_code]
	return rules.default_co_pay_percent
