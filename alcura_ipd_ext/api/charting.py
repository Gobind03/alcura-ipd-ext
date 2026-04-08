"""Whitelisted API methods for bedside charting operations (US-E4)."""

from __future__ import annotations

import frappe
from frappe import _


@frappe.whitelist()
def start_chart(
	inpatient_record: str,
	chart_template: str,
	frequency_minutes: int | None = None,
) -> dict:
	"""Start a bedside chart for an admission."""
	from alcura_ipd_ext.services.charting_service import start_bedside_chart

	return start_bedside_chart(
		inpatient_record=inpatient_record,
		chart_template=chart_template,
		frequency_minutes=int(frequency_minutes) if frequency_minutes else None,
	)


@frappe.whitelist()
def record_entry(
	bedside_chart: str,
	observations: list | str,
	entry_datetime: str | None = None,
	notes: str = "",
) -> dict:
	"""Record a chart entry."""
	from alcura_ipd_ext.services.charting_service import record_chart_entry

	if isinstance(observations, str):
		import json
		observations = json.loads(observations)

	return record_chart_entry(
		bedside_chart=bedside_chart,
		observations=observations,
		entry_datetime=entry_datetime,
		notes=notes,
	)


@frappe.whitelist()
def get_chart_parameters(bedside_chart: str) -> list[dict]:
	"""Return template parameters for a bedside chart."""
	from alcura_ipd_ext.services.charting_service import get_chart_parameters as _get

	return _get(bedside_chart)


@frappe.whitelist()
def create_correction_entry(original_entry: str, correction_reason: str) -> dict:
	"""Create a correction for an existing chart entry."""
	from alcura_ipd_ext.services.charting_service import create_correction_entry as _create

	return _create(original_entry, correction_reason)


@frappe.whitelist()
def get_charts_for_admission(inpatient_record: str) -> list[dict]:
	"""Return all bedside charts for an admission."""
	from alcura_ipd_ext.services.charting_service import get_charts_for_ir

	return get_charts_for_ir(inpatient_record)


@frappe.whitelist()
def get_overdue(
	ward: str | None = None,
	company: str | None = None,
	grace_minutes: int = 0,
) -> list[dict]:
	"""Return overdue charts, optionally filtered by ward."""
	from alcura_ipd_ext.services.charting_service import get_overdue_charts

	return get_overdue_charts(
		ward=ward,
		company=company,
		grace_minutes=int(grace_minutes) if grace_minutes else 0,
	)


# ── Observation Trends (US-H2) ───────────────────────────────────────


@frappe.whitelist()
def get_observation_trend(
	bedside_chart: str,
	parameter_name: str,
	from_datetime: str | None = None,
	to_datetime: str | None = None,
	limit: int = 200,
) -> list[dict]:
	"""Return time-series data for a single parameter, optimised for graphing."""
	from alcura_ipd_ext.services.observation_trend_service import get_parameter_trend

	return get_parameter_trend(
		bedside_chart=bedside_chart,
		parameter_name=parameter_name,
		from_datetime=from_datetime,
		to_datetime=to_datetime,
		limit=int(limit),
	)


@frappe.whitelist()
def get_multi_parameter_trend(
	bedside_chart: str,
	parameter_names: list | str,
	from_datetime: str | None = None,
	to_datetime: str | None = None,
) -> dict:
	"""Return time-series data for multiple parameters (overlay charts)."""
	import json

	from alcura_ipd_ext.services.observation_trend_service import (
		get_multi_parameter_trend as _get,
	)

	if isinstance(parameter_names, str):
		parameter_names = json.loads(parameter_names)

	return _get(
		bedside_chart=bedside_chart,
		parameter_names=parameter_names,
		from_datetime=from_datetime,
		to_datetime=to_datetime,
	)


@frappe.whitelist()
def get_observation_schedule(
	bedside_chart: str,
	from_datetime: str | None = None,
	to_datetime: str | None = None,
) -> list[dict]:
	"""Return expected vs actual observation slots, highlighting missed entries."""
	from alcura_ipd_ext.services.observation_trend_service import (
		get_observation_schedule as _get,
	)

	return _get(bedside_chart, from_datetime, to_datetime)


@frappe.whitelist()
def get_dashboard_summary(
	ward: str | None = None,
	shift_start: str | None = None,
	shift_end: str | None = None,
) -> list[dict]:
	"""Return aggregated observation summary per active chart for ICU dashboard."""
	from alcura_ipd_ext.services.observation_trend_service import (
		get_dashboard_summary as _get,
	)

	return _get(ward=ward, shift_start=shift_start, shift_end=shift_end)


# ── I/O ─────────────────────────────────────────────────────────────


@frappe.whitelist()
def get_fluid_balance_summary(
	inpatient_record: str,
	date: str | None = None,
) -> dict:
	"""Return fluid balance summary for an admission."""
	from alcura_ipd_ext.services.io_service import get_fluid_balance

	return get_fluid_balance(inpatient_record, date)


@frappe.whitelist()
def get_hourly_fluid_balance(
	inpatient_record: str,
	date: str | None = None,
) -> list[dict]:
	"""Return hourly fluid balance breakdown."""
	from alcura_ipd_ext.services.io_service import get_hourly_balance

	return get_hourly_balance(inpatient_record, date)


@frappe.whitelist()
def create_io_correction(original_entry: str, correction_reason: str) -> dict:
	"""Create a correction for an I/O entry."""
	from alcura_ipd_ext.services.io_service import create_io_correction as _create

	return _create(original_entry, correction_reason)


# ── MAR ──────────────────────────────────────────────────────────────


@frappe.whitelist()
def create_mar_correction(original_entry: str, correction_reason: str) -> dict:
	"""Create a correction for a MAR entry."""
	from alcura_ipd_ext.services.mar_service import create_mar_correction as _create

	return _create(original_entry, correction_reason)


@frappe.whitelist()
def get_mar_summary(
	inpatient_record: str,
	date: str | None = None,
) -> dict:
	"""Return MAR summary for an admission."""
	from alcura_ipd_ext.services.mar_service import get_mar_summary as _get

	return _get(inpatient_record, date)
