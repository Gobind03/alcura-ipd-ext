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
	frappe.logger("alcura_ipd_ext").info("Alcura IPD Extensions installed successfully.")


def before_uninstall():
	"""Cleanup before the app is removed from a site."""
	from alcura_ipd_ext.setup.custom_fields import teardown_custom_fields
	from alcura_ipd_ext.setup.intake_fixtures import teardown_intake_fixtures
	from alcura_ipd_ext.setup.roles import teardown_roles

	teardown_intake_fixtures()
	teardown_custom_fields()
	teardown_roles()
	frappe.logger("alcura_ipd_ext").info("Alcura IPD Extensions: custom fields and roles removed.")
