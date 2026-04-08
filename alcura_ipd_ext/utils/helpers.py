"""General-purpose helpers used across the app."""

import frappe


def get_healthcare_settings() -> dict:
	"""Fetch Healthcare Settings as a dict, with caching."""
	return frappe.get_cached_doc("Healthcare Settings").as_dict()
