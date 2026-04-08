"""Tests for the IPD whitelisted API."""

from alcura_ipd_ext.api.ipd import get_active_ipd_records


def test_get_active_ipd_records_returns_list(admin_session):
	result = get_active_ipd_records()
	assert isinstance(result, list)
