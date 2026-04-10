"""Lifecycle hooks executed during app install / uninstall."""

import frappe


def after_install():
	"""Runs once after the app is installed on a site."""
	from alcura_ipd_ext.setup.charting_fixtures import setup_charting_fixtures
	from alcura_ipd_ext.setup.custom_fields import setup_custom_fields
	from alcura_ipd_ext.setup.intake_fixtures import setup_intake_fixtures
	from alcura_ipd_ext.setup.monitoring_profile_fixtures import setup_monitoring_profile_fixtures
	from alcura_ipd_ext.setup.roles import setup_roles

	setup_roles()
	setup_custom_fields()
	setup_intake_fixtures()
	setup_charting_fixtures()
	setup_monitoring_profile_fixtures()
	_patch_healthcare_schema()
	frappe.logger("alcura_ipd_ext").info("Alcura IPD Extensions installed successfully.")


def _patch_healthcare_schema():
	"""Add missing columns to Healthcare module tables if needed.

	Some ERPNext Healthcare doctypes define fields that may not have
	corresponding database columns after partial migrations.
	"""
	patches = [
		("Patient Medical Record", "reference_name", "varchar(255)"),
		("Patient Medical Record", "reference_doctype", "varchar(255)"),
	]
	for dt, col, col_type in patches:
		table = f"tab{dt}"
		try:
			if not frappe.db.table_exists(table):
				continue
			existing = set(frappe.db.get_table_columns(dt))
			if col not in existing:
				frappe.db.sql_ddl(f"ALTER TABLE `{table}` ADD COLUMN `{col}` {col_type}")
		except Exception:
			pass


def before_uninstall():
	"""Cleanup before the app is removed from a site."""
	from alcura_ipd_ext.setup.custom_fields import teardown_custom_fields
	from alcura_ipd_ext.setup.intake_fixtures import teardown_intake_fixtures
	from alcura_ipd_ext.setup.roles import teardown_roles

	teardown_intake_fixtures()
	teardown_custom_fields()
	teardown_roles()
	frappe.logger("alcura_ipd_ext").info("Alcura IPD Extensions: custom fields and roles removed.")
