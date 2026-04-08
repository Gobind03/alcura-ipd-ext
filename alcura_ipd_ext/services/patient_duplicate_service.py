"""Duplicate detection service for Patient registration.

Returns potential duplicate matches with match reasons so the caller
(API / UI) can warn the user without hard-blocking valid edge cases.
"""

from __future__ import annotations

import frappe


def check_duplicates(
	*,
	mobile: str | None = None,
	aadhaar: str | None = None,
	abha: str | None = None,
	mr_number: str | None = None,
	first_name: str | None = None,
	dob: str | None = None,
	exclude_patient: str | None = None,
) -> list[dict]:
	"""Find potential duplicate Patient records.

	Each returned dict has:
		- patient: Patient name (ID)
		- patient_name: full display name
		- mobile: patient mobile
		- match_reasons: list[str] describing why this is a match

	Args:
		mobile: 10-digit mobile to match
		aadhaar: Aadhaar number to match
		abha: ABHA number to match
		mr_number: MR number to match
		first_name: first name for fuzzy name+DOB matching
		dob: date of birth (YYYY-MM-DD) for fuzzy matching
		exclude_patient: Patient name to exclude (the current record)
	"""
	matches: dict[str, dict] = {}

	if mobile:
		_find_exact(matches, "mobile", "mobile", mobile.strip(), exclude_patient)

	if aadhaar:
		cleaned = aadhaar.strip().replace(" ", "").replace("-", "")
		_find_exact(matches, "custom_aadhaar_number", "Aadhaar", cleaned, exclude_patient)

	if abha:
		cleaned = abha.strip().replace(" ", "").replace("-", "")
		_find_exact(matches, "custom_abha_number", "ABHA Number", cleaned, exclude_patient)

	if mr_number:
		_find_exact(matches, "custom_mr_number", "MR Number", mr_number.strip(), exclude_patient)

	if first_name and dob:
		_find_fuzzy_name_dob(matches, first_name.strip(), dob, exclude_patient)

	result = sorted(matches.values(), key=lambda m: len(m["match_reasons"]), reverse=True)
	return result


def _find_exact(
	matches: dict[str, dict],
	field: str,
	reason_label: str,
	value: str,
	exclude_patient: str | None,
) -> None:
	"""Query Patient by exact field match and merge into matches dict."""
	if not value:
		return

	filters = {field: value}
	if exclude_patient:
		filters["name"] = ("!=", exclude_patient)

	rows = frappe.get_all(
		"Patient",
		filters=filters,
		fields=["name", "patient_name", "mobile", "dob"],
		limit_page_length=10,
	)

	for row in rows:
		key = row["name"]
		if key in matches:
			matches[key]["match_reasons"].append(reason_label)
		else:
			matches[key] = {
				"patient": row["name"],
				"patient_name": row["patient_name"],
				"mobile": row.get("mobile"),
				"dob": str(row["dob"]) if row.get("dob") else None,
				"match_reasons": [reason_label],
			}


def _find_fuzzy_name_dob(
	matches: dict[str, dict],
	first_name: str,
	dob: str,
	exclude_patient: str | None,
) -> None:
	"""Find patients with the same DOB whose first name sounds similar
	using MySQL/MariaDB SOUNDEX."""
	exclude_clause = ""
	params = {"dob": dob, "first_name": first_name}

	if exclude_patient:
		exclude_clause = "AND p.name != %(exclude)s"
		params["exclude"] = exclude_patient

	rows = frappe.db.sql(
		f"""
		SELECT p.name, p.patient_name, p.mobile, p.dob
		FROM `tabPatient` p
		WHERE p.dob = %(dob)s
		  AND SOUNDEX(p.first_name) = SOUNDEX(%(first_name)s)
		  {exclude_clause}
		LIMIT 10
		""",
		params,
		as_dict=True,
	)

	for row in rows:
		key = row["name"]
		reason = "Similar Name + Same DOB"
		if key in matches:
			matches[key]["match_reasons"].append(reason)
		else:
			matches[key] = {
				"patient": row["name"],
				"patient_name": row["patient_name"],
				"mobile": row.get("mobile"),
				"dob": str(row["dob"]) if row.get("dob") else None,
				"match_reasons": [reason],
			}
