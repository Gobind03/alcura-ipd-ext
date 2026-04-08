"""Patch to seed charting template fixtures for existing installations."""

from __future__ import annotations

import frappe


def execute():
	from alcura_ipd_ext.setup.charting_fixtures import setup_charting_fixtures
	from alcura_ipd_ext.setup.custom_fields import setup_custom_fields

	setup_custom_fields()
	setup_charting_fixtures()
