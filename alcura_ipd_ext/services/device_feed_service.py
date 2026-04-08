"""Device observation feed service (US-H3).

Handles:
- Ingesting external device readings into the patient chart
- Idempotency checking to prevent duplicate processing
- Parameter mapping and unit conversion
- Out-of-range detection and critical alerting
- Manual validation workflow for configured device types
"""

from __future__ import annotations

import json

import frappe
from frappe import _
from frappe.utils import now_datetime


def ingest_observation(
	source_device_type: str,
	source_device_id: str,
	patient_id: str | None = None,
	inpatient_record: str | None = None,
	readings: list[dict] | None = None,
	timestamp: str | None = None,
	idempotency_key: str | None = None,
	raw_payload: dict | None = None,
) -> dict:
	"""Main entry point for device observation ingestion.

	Returns dict with ``feed_name``, ``status``, ``chart_entry`` (if created),
	and ``alerts`` (list of out-of-range parameters).
	"""
	if idempotency_key:
		existing = check_idempotency(idempotency_key)
		if existing:
			return existing

	if not inpatient_record and patient_id:
		inpatient_record = _resolve_inpatient_record(patient_id)

	mapping_doc = _find_mapping(source_device_type)

	feed = frappe.get_doc({
		"doctype": "Device Observation Feed",
		"source_device_type": source_device_type,
		"source_device_id": source_device_id,
		"patient": patient_id,
		"inpatient_record": inpatient_record,
		"received_at": timestamp or now_datetime(),
		"idempotency_key": idempotency_key,
		"status": "Received",
		"payload": json.dumps(raw_payload) if raw_payload else None,
		"requires_validation": mapping_doc.requires_manual_validation if mapping_doc else 0,
	})
	feed.insert(ignore_permissions=True)

	if not mapping_doc:
		feed.db_set({
			"status": "Error",
			"error_message": f"No active mapping found for device type: {source_device_type}",
		})
		return {
			"feed_name": feed.name,
			"status": "Error",
			"chart_entry": None,
			"alerts": [],
		}

	try:
		return process_feed(feed, mapping_doc, readings or [])
	except Exception as e:
		feed.db_set({
			"status": "Error",
			"error_message": str(e),
			"processed_at": now_datetime(),
		})
		frappe.logger("alcura_ipd_ext").error(
			f"Device feed processing failed for {feed.name}: {e}",
			exc_info=True,
		)
		return {
			"feed_name": feed.name,
			"status": "Error",
			"chart_entry": None,
			"alerts": [],
		}


def process_feed(
	feed: "frappe.Document",
	mapping_doc: "frappe.Document",
	readings: list[dict],
) -> dict:
	"""Map readings, check ranges, and optionally create a chart entry."""
	mapped_readings = map_readings(readings, mapping_doc)

	for reading_row in mapped_readings:
		feed.append("readings", reading_row)
	feed.save(ignore_permissions=True)

	chart_name = find_active_chart(
		feed.inpatient_record, mapping_doc.chart_template
	)
	if chart_name:
		feed.db_set("bedside_chart", chart_name)

	alerts = [r for r in mapped_readings if r.get("is_out_of_range")]

	if feed.requires_validation:
		feed.db_set({
			"status": "Received",
			"processed_at": now_datetime(),
		})
		_notify_pending_validation(feed)
		return {
			"feed_name": feed.name,
			"status": "Received",
			"chart_entry": None,
			"alerts": [a["parameter_name"] for a in alerts],
		}

	chart_entry_name = None
	if chart_name:
		chart_entry_name = _create_chart_entry(feed, chart_name, mapped_readings)
		feed.db_set({
			"chart_entry": chart_entry_name,
			"status": "Mapped",
			"processed_at": now_datetime(),
		})
	else:
		feed.db_set({
			"status": "Mapped",
			"processed_at": now_datetime(),
		})

	if alerts:
		_raise_out_of_range_alerts(feed, alerts)

	return {
		"feed_name": feed.name,
		"status": "Mapped",
		"chart_entry": chart_entry_name,
		"alerts": [a["parameter_name"] for a in alerts],
	}


def validate_feed(feed_name: str, action: str) -> dict:
	"""Nurse validates or rejects a pending device observation feed.

	Args:
		feed_name: Name of the Device Observation Feed.
		action: "validate" or "reject".

	Returns dict with updated ``status`` and ``chart_entry``.
	"""
	feed = frappe.get_doc("Device Observation Feed", feed_name)

	if feed.status not in ("Received",):
		frappe.throw(
			_("Feed {0} has status {1} and cannot be {2}d.").format(
				feed.name, feed.status, action
			)
		)

	if action == "reject":
		feed.db_set({
			"status": "Rejected",
			"validated_by": frappe.session.user,
			"validated_at": now_datetime(),
		})
		return {"status": "Rejected", "chart_entry": None}

	if action == "validate":
		chart_entry_name = None
		if feed.bedside_chart:
			mapped_readings = [
				{
					"parameter_name": r.parameter_name,
					"numeric_value": r.mapped_value,
					"uom": r.uom,
				}
				for r in feed.readings
			]
			chart_entry_name = _create_chart_entry(
				feed, feed.bedside_chart, mapped_readings
			)

		feed.db_set({
			"status": "Validated",
			"validated_by": frappe.session.user,
			"validated_at": now_datetime(),
			"chart_entry": chart_entry_name,
		})
		return {"status": "Validated", "chart_entry": chart_entry_name}

	frappe.throw(_("Invalid action: {0}. Use 'validate' or 'reject'.").format(action))


def get_pending_validations(ward: str | None = None) -> list[dict]:
	"""Return device feeds awaiting nurse validation."""
	filters = {
		"status": "Received",
		"requires_validation": 1,
	}

	feeds = frappe.get_all(
		"Device Observation Feed",
		filters=filters,
		fields=[
			"name", "source_device_type", "source_device_id",
			"patient", "inpatient_record", "received_at",
			"bedside_chart",
		],
		order_by="received_at asc",
	)

	if ward:
		feeds = [
			f for f in feeds
			if _get_ward_for_ir(f.get("inpatient_record")) == ward
		]

	return feeds


def check_idempotency(idempotency_key: str) -> dict | None:
	"""Check if a feed with this idempotency key already exists."""
	existing = frappe.db.get_value(
		"Device Observation Feed",
		{"idempotency_key": idempotency_key},
		["name", "status", "chart_entry"],
		as_dict=True,
	)
	if existing:
		return {
			"feed_name": existing.name,
			"status": existing.status,
			"chart_entry": existing.chart_entry,
			"alerts": [],
			"duplicate": True,
		}
	return None


def map_readings(
	readings: list[dict],
	mapping_doc: "frappe.Document",
) -> list[dict]:
	"""Apply parameter mapping and unit conversion to raw device readings."""
	param_map = {
		m.device_parameter: m for m in mapping_doc.mappings
	}

	template_params = {}
	if mapping_doc.chart_template:
		for p in frappe.get_all(
			"IPD Chart Template Parameter",
			filters={"parent": mapping_doc.chart_template},
			fields=["parameter_name", "critical_low", "critical_high", "uom"],
		):
			template_params[p.parameter_name] = p

	result = []
	for reading in readings:
		device_param = reading.get("parameter") or reading.get("parameter_name", "")
		raw_value = reading.get("value")

		mapping = param_map.get(device_param)
		if not mapping:
			result.append({
				"parameter_name": device_param,
				"raw_value": str(raw_value) if raw_value is not None else None,
				"mapped_value": None,
				"uom": "",
				"is_out_of_range": 0,
			})
			continue

		try:
			numeric_raw = float(raw_value) if raw_value is not None else None
		except (ValueError, TypeError):
			numeric_raw = None

		mapped_value = None
		if numeric_raw is not None:
			factor = mapping.unit_conversion_factor or 1.0
			offset = mapping.unit_conversion_offset or 0.0
			mapped_value = numeric_raw * factor + offset

		chart_param = mapping.chart_parameter
		tmpl_param = template_params.get(chart_param)
		uom = tmpl_param.uom if tmpl_param else ""

		is_oor = 0
		if mapped_value is not None and tmpl_param:
			crit_low = tmpl_param.critical_low
			crit_high = tmpl_param.critical_high
			if crit_low and mapped_value < crit_low:
				is_oor = 1
			elif crit_high and mapped_value > crit_high:
				is_oor = 1

		result.append({
			"parameter_name": chart_param,
			"raw_value": str(raw_value) if raw_value is not None else None,
			"mapped_value": mapped_value,
			"uom": uom,
			"is_out_of_range": is_oor,
		})

	return result


def find_active_chart(
	inpatient_record: str | None,
	chart_template: str,
) -> str | None:
	"""Find the active bedside chart for a given IR and template."""
	if not inpatient_record:
		return None

	return frappe.db.get_value(
		"IPD Bedside Chart",
		{
			"inpatient_record": inpatient_record,
			"chart_template": chart_template,
			"status": "Active",
		},
		"name",
	)


def _find_mapping(source_device_type: str) -> "frappe.Document | None":
	"""Find the active Device Observation Mapping for a device type."""
	name = frappe.db.get_value(
		"Device Observation Mapping",
		{"source_device_type": source_device_type, "is_active": 1},
		"name",
	)
	if name:
		return frappe.get_doc("Device Observation Mapping", name)
	return None


def _resolve_inpatient_record(patient_id: str) -> str | None:
	"""Find the active Inpatient Record for a patient."""
	return frappe.db.get_value(
		"Inpatient Record",
		{"patient": patient_id, "status": "Admitted"},
		"name",
	)


def _create_chart_entry(
	feed: "frappe.Document",
	chart_name: str,
	mapped_readings: list[dict],
) -> str:
	"""Create a chart entry from mapped device readings."""
	from alcura_ipd_ext.services.charting_service import record_chart_entry

	observations = []
	for r in mapped_readings:
		if r.get("mapped_value") is not None:
			observations.append({
				"parameter_name": r["parameter_name"],
				"numeric_value": r["mapped_value"],
				"uom": r.get("uom", ""),
			})

	if not observations:
		return None

	result = record_chart_entry(
		bedside_chart=chart_name,
		observations=observations,
		entry_datetime=str(feed.received_at),
		notes=f"Device: {feed.source_device_type} ({feed.source_device_id})",
	)

	frappe.db.set_value(
		"IPD Chart Entry",
		result["entry"],
		{
			"is_device_generated": 1,
			"device_feed": feed.name,
		},
		update_modified=False,
	)

	return result["entry"]


def _notify_pending_validation(feed: "frappe.Document") -> None:
	"""Notify nursing staff about a feed pending validation."""
	recipients = frappe.get_all(
		"Has Role",
		filters={"role": "Nursing User", "parenttype": "User"},
		pluck="parent",
	)
	for user in recipients:
		if user in ("Administrator", "Guest"):
			continue
		notification = frappe.new_doc("Notification Log")
		notification.update({
			"for_user": user,
			"from_user": frappe.session.user,
			"type": "Alert",
			"document_type": "Device Observation Feed",
			"document_name": feed.name,
			"subject": _(
				"Device reading from {0} requires validation — Patient {1}"
			).format(feed.source_device_type, feed.patient or "Unknown"),
		})
		notification.insert(ignore_permissions=True)


def _raise_out_of_range_alerts(
	feed: "frappe.Document",
	alerts: list[dict],
) -> None:
	"""Publish realtime alert for out-of-range device readings."""
	param_names = ", ".join(a["parameter_name"] for a in alerts)
	frappe.publish_realtime(
		"device_critical_alert",
		{
			"feed": feed.name,
			"patient": feed.patient,
			"inpatient_record": feed.inpatient_record,
			"device_type": feed.source_device_type,
			"parameters": param_names,
		},
	)


def _get_ward_for_ir(inpatient_record: str | None) -> str | None:
	if not inpatient_record:
		return None
	return frappe.db.get_value(
		"Inpatient Record", inpatient_record, "custom_current_ward"
	)
