"""
Shared pytest fixtures for alcura_ipd_ext.

These fixtures are automatically available to every test file in this
directory and its subdirectories.
"""

import frappe
import pytest


@pytest.fixture(scope="session")
def site_setup():
	"""Ensure the Frappe test site is initialised once per session."""
	frappe.init(site="test_site")
	frappe.connect()
	yield
	frappe.destroy()


@pytest.fixture(autouse=True)
def rollback_db(site_setup):
	"""Roll back every DB change after each test to keep tests isolated."""
	frappe.db.savepoint("before_test")
	yield
	frappe.db.rollback(save_point="before_test")
	frappe.clear_cache()


@pytest.fixture()
def admin_session(site_setup):
	"""Set the session user to Administrator for tests that need elevated access."""
	prev_user = frappe.session.user
	frappe.set_user("Administrator")
	yield
	frappe.set_user(prev_user)
