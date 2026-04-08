"""Add performance indexes for high-frequency charting queries (US-H2)
and new fields for ICU monitoring (US-H1, US-H3)."""

from __future__ import annotations

import frappe


def execute():
	_add_index_if_missing(
		"IPD Chart Entry",
		"idx_ce_chart_datetime",
		["bedside_chart", "entry_datetime"],
	)
	_add_index_if_missing(
		"IPD Chart Entry",
		"idx_ce_ir_datetime",
		["inpatient_record", "entry_datetime"],
	)
	_add_index_if_missing(
		"IPD Chart Observation",
		"idx_co_parent_param",
		["parent", "parameter_name"],
	)

	from alcura_ipd_ext.setup.monitoring_profile_fixtures import setup_monitoring_profile_fixtures

	setup_monitoring_profile_fixtures()

	frappe.db.commit()


def _add_index_if_missing(doctype: str, index_name: str, columns: list[str]):
	table = f"tab{doctype}"
	existing = frappe.db.sql(
		f"SHOW INDEX FROM `{table}` WHERE Key_name = %s",
		index_name,
	)
	if existing:
		return

	col_list = ", ".join(f"`{c}`" for c in columns)
	frappe.db.sql_ddl(
		f"ALTER TABLE `{table}` ADD INDEX `{index_name}` ({col_list})"
	)
	frappe.logger("alcura_ipd_ext").info(
		f"Added index {index_name} on {table} ({col_list})"
	)
