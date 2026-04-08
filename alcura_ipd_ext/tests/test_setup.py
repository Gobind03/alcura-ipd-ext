"""Smoke tests to verify the app is installed and wired correctly."""

import frappe


def test_app_is_installed():
	"""Confirm alcura_ipd_ext appears in the installed apps list."""
	installed = frappe.get_installed_apps()
	assert "alcura_ipd_ext" in installed


def test_hooks_metadata():
	"""Validate essential hooks metadata is present."""
	from alcura_ipd_ext.hooks import app_name, app_title, app_version

	assert app_name == "alcura_ipd_ext"
	assert app_title
	assert app_version
