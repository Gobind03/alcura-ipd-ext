"""Whitelisted API methods for device observation feeds (US-H3).

These endpoints are intended for external device integrations (e.g. Dozee,
bedside monitors) that push readings into the patient chart.
"""

from __future__ import annotations

import json

import frappe


@frappe.whitelist()
def ingest_observation(
	source_device_type: str,
	source_device_id: str,
	readings: list | str,
	patient_id: str | None = None,
	inpatient_record: str | None = None,
	timestamp: str | None = None,
	idempotency_key: str | None = None,
) -> dict:
	"""Ingest a device observation reading.

	Expects ``readings`` as a list of dicts with at minimum
	``parameter`` and ``value`` keys.
	"""
	from alcura_ipd_ext.services.device_feed_service import (
		ingest_observation as _ingest,
	)

	if isinstance(readings, str):
		readings = json.loads(readings)

	return _ingest(
		source_device_type=source_device_type,
		source_device_id=source_device_id,
		patient_id=patient_id,
		inpatient_record=inpatient_record,
		readings=readings,
		timestamp=timestamp,
		idempotency_key=idempotency_key,
		raw_payload={"readings": readings},
	)


@frappe.whitelist()
def validate_feed(feed_name: str, action: str) -> dict:
	"""Validate or reject a pending device observation feed.

	Args:
		feed_name: Name of the Device Observation Feed.
		action: "validate" or "reject".
	"""
	from alcura_ipd_ext.services.device_feed_service import validate_feed as _validate

	return _validate(feed_name, action)


@frappe.whitelist()
def get_pending_validations(ward: str | None = None) -> list[dict]:
	"""Return device feeds awaiting nurse validation."""
	from alcura_ipd_ext.services.device_feed_service import (
		get_pending_validations as _get,
	)

	return _get(ward=ward)
