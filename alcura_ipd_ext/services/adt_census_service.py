"""ADT Census Service (US-K3).

Computes daily Admission-Discharge-Transfer census for a given date and
optional ward/consultant filters.

Census definitions
------------------
For a given date D and ward W:

- **Opening census**: patients in ward W at midnight start of day D.
  Determined by finding each IR's last Bed Movement Log entry before
  midnight of D — if that entry's ``to_ward == W``, the patient was in
  the ward at midnight.

- **Admissions**: BML entries with ``movement_type = 'Admission'`` and
  ``to_ward = W`` within day D.

- **Transfers in**: BML entries with ``movement_type = 'Transfer'`` and
  ``to_ward = W`` within day D.

- **Transfers out**: BML entries with ``movement_type = 'Transfer'`` and
  ``from_ward = W`` within day D.

- **Discharges**: BML entries with ``movement_type = 'Discharge'`` and
  ``from_ward = W`` within day D.

- **Deaths**: subset of discharges where the linked ``IPD Discharge
  Advice`` has ``discharge_type = 'Death'``.

- **Closing census**: opening + admissions + transfers_in - transfers_out
  - discharges.

Edge cases
----------
- Same-day admission + discharge: counted in both.
- Same-day admission + transfer: admission in ward A, transfer out of A,
  transfer in to B.
- Multiple transfers in a day: each counted separately.
"""

from __future__ import annotations

import frappe
from frappe.utils import getdate


def get_adt_census(filters: dict | None = None) -> list[dict]:
	"""Return per-ward ADT census rows for the given date.

	Args:
		filters: dict with keys — date (required), ward, consultant,
			company, branch.

	Returns:
		List of dicts with keys: ward, ward_name, opening_census,
		admissions, transfers_in, transfers_out, discharges, deaths,
		closing_census. Optionally includes consultant if filtered.
	"""
	filters = filters or {}
	census_date = getdate(filters.get("date"))
	if not census_date:
		frappe.throw("Date is required for ADT Census.")

	day_start = f"{census_date} 00:00:00"
	day_end = f"{census_date} 23:59:59"

	wards = _get_target_wards(filters)
	if not wards:
		return []

	opening_map = _compute_opening_census(census_date, wards, filters)
	movement_counts = _compute_day_movements(day_start, day_end, wards, filters)
	death_counts = _compute_deaths(day_start, day_end, wards, filters)

	ward_names = _get_ward_names(wards)

	rows = []
	for ward in wards:
		opening = opening_map.get(ward, 0)
		mc = movement_counts.get(ward, {})
		admissions = mc.get("admissions", 0)
		transfers_in = mc.get("transfers_in", 0)
		transfers_out = mc.get("transfers_out", 0)
		discharges = mc.get("discharges", 0)
		deaths = death_counts.get(ward, 0)
		closing = opening + admissions + transfers_in - transfers_out - discharges

		rows.append({
			"ward": ward,
			"ward_name": ward_names.get(ward, ward),
			"opening_census": opening,
			"admissions": admissions,
			"transfers_in": transfers_in,
			"transfers_out": transfers_out,
			"discharges": discharges,
			"deaths": deaths,
			"closing_census": closing,
		})

	return rows


def get_adt_totals(rows: list[dict]) -> dict:
	"""Compute aggregate totals from census rows."""
	totals = {
		"opening_census": 0,
		"admissions": 0,
		"transfers_in": 0,
		"transfers_out": 0,
		"discharges": 0,
		"deaths": 0,
		"closing_census": 0,
	}
	for row in rows:
		for key in totals:
			totals[key] += row.get(key, 0)

	totals["net_movement"] = (
		totals["admissions"] + totals["transfers_in"]
		- totals["transfers_out"] - totals["discharges"]
	)
	return totals


# ── internal helpers ────────────────────────────────────────────────


def _get_target_wards(filters: dict) -> list[str]:
	"""Return list of ward names to include in census."""
	conditions = ["ward.is_active = 1"]
	params: dict = {}

	if filters.get("ward"):
		conditions.append("ward.name = %(ward)s")
		params["ward"] = filters["ward"]

	if filters.get("company"):
		conditions.append("ward.company = %(company)s")
		params["company"] = filters["company"]

	if filters.get("branch"):
		conditions.append("ward.branch = %(branch)s")
		params["branch"] = filters["branch"]

	where = " AND ".join(conditions)

	rows = frappe.db.sql(
		f"SELECT ward.name FROM `tabHospital Ward` ward WHERE {where} ORDER BY ward.ward_name",
		params,
		as_dict=True,
	)
	return [r["name"] for r in rows]


def _get_ward_names(wards: list[str]) -> dict[str, str]:
	if not wards:
		return {}
	result = frappe.db.sql(
		"""SELECT name, ward_name FROM `tabHospital Ward` WHERE name IN %(wards)s""",
		{"wards": wards},
		as_dict=True,
	)
	return {r["name"]: r["ward_name"] for r in result}


def _compute_opening_census(census_date, wards: list[str], filters: dict) -> dict[str, int]:
	"""Count patients in each ward at midnight of census_date.

	For each admitted or recently-discharged IR, find the last BML entry
	before midnight. If that entry's to_ward is in our ward list, count
	the patient in that ward.

	We use a correlated subquery to get the latest BML per IR before midnight.
	"""
	midnight = f"{census_date} 00:00:00"

	consultant_join = ""
	consultant_condition = ""
	params: dict = {"midnight": midnight, "wards": wards}

	if filters.get("consultant"):
		consultant_condition = "AND ir.primary_practitioner = %(consultant)s"
		params["consultant"] = filters["consultant"]

	if filters.get("company"):
		consultant_condition += " AND ir.company = %(ir_company)s"
		params["ir_company"] = filters["company"]

	rows = frappe.db.sql(
		f"""
		SELECT
			latest_bml.to_ward AS ward,
			COUNT(DISTINCT latest_bml.inpatient_record) AS cnt
		FROM (
			SELECT bml.inpatient_record, bml.to_ward
			FROM `tabBed Movement Log` bml
			INNER JOIN (
				SELECT inpatient_record, MAX(movement_datetime) AS max_dt
				FROM `tabBed Movement Log`
				WHERE movement_datetime < %(midnight)s
				GROUP BY inpatient_record
			) latest ON bml.inpatient_record = latest.inpatient_record
				AND bml.movement_datetime = latest.max_dt
			WHERE bml.to_ward IN %(wards)s
				AND bml.movement_type != 'Discharge'
		) latest_bml
		INNER JOIN `tabInpatient Record` ir
			ON ir.name = latest_bml.inpatient_record
		WHERE 1=1 {consultant_condition}
		GROUP BY latest_bml.to_ward
		""",
		params,
		as_dict=True,
	)

	return {r["ward"]: int(r["cnt"]) for r in rows}


def _compute_day_movements(
	day_start: str, day_end: str, wards: list[str], filters: dict,
) -> dict[str, dict[str, int]]:
	"""Count admissions, transfers in/out, discharges per ward for the day.

	Uses four targeted queries -- one per movement direction -- to avoid
	ward-attribution ambiguity that arises in a single combined query.
	"""
	params: dict = {"day_start": day_start, "day_end": day_end, "wards": wards}

	consultant_condition = ""
	if filters.get("consultant"):
		consultant_condition = "AND bml.ordered_by_practitioner = %(consultant)s"
		params["consultant"] = filters["consultant"]

	company_condition = ""
	if filters.get("company"):
		company_condition = "AND bml.company = %(company)s"
		params["company"] = filters["company"]

	result: dict[str, dict[str, int]] = {}

	def _ensure_ward(ward: str) -> None:
		if ward not in result:
			result[ward] = {"admissions": 0, "transfers_in": 0, "transfers_out": 0, "discharges": 0}

	_movement_queries = [
		("admissions", "Admission", "bml.to_ward", "bml.to_ward IN %(wards)s"),
		("transfers_in", "Transfer", "bml.to_ward", "bml.to_ward IN %(wards)s"),
		("transfers_out", "Transfer", "bml.from_ward", "bml.from_ward IN %(wards)s"),
		("discharges", "Discharge", "bml.from_ward", "bml.from_ward IN %(wards)s"),
	]

	for key, movement_type, ward_col, ward_filter in _movement_queries:
		rows = frappe.db.sql(
			f"""
			SELECT {ward_col} AS ward, COUNT(*) AS cnt
			FROM `tabBed Movement Log` bml
			WHERE bml.movement_type = %(mt)s
				AND bml.movement_datetime BETWEEN %(day_start)s AND %(day_end)s
				AND {ward_filter}
				{consultant_condition}
				{company_condition}
			GROUP BY {ward_col}
			""",
			{**params, "mt": movement_type},
			as_dict=True,
		)
		for r in rows:
			_ensure_ward(r["ward"])
			result[r["ward"]][key] = int(r["cnt"])

	return result


def _compute_deaths(
	day_start: str, day_end: str, wards: list[str], filters: dict,
) -> dict[str, int]:
	"""Count deaths per ward — discharge BMLs linked to IPD Discharge Advice with discharge_type='Death'."""
	params: dict = {"day_start": day_start, "day_end": day_end, "wards": wards}

	consultant_condition = ""
	if filters.get("consultant"):
		consultant_condition = "AND bml.ordered_by_practitioner = %(consultant)s"
		params["consultant"] = filters["consultant"]

	company_condition = ""
	if filters.get("company"):
		company_condition = "AND bml.company = %(company)s"
		params["company"] = filters["company"]

	rows = frappe.db.sql(
		f"""
		SELECT bml.from_ward AS ward, COUNT(*) AS cnt
		FROM `tabBed Movement Log` bml
		INNER JOIN `tabIPD Discharge Advice` da
			ON da.inpatient_record = bml.inpatient_record
			AND da.discharge_type = 'Death'
			AND da.docstatus != 2
		WHERE bml.movement_type = 'Discharge'
			AND bml.movement_datetime BETWEEN %(day_start)s AND %(day_end)s
			AND bml.from_ward IN %(wards)s
			{consultant_condition}
			{company_condition}
		GROUP BY bml.from_ward
		""",
		params,
		as_dict=True,
	)

	return {r["ward"]: int(r["cnt"]) for r in rows}
