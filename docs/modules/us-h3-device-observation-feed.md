# US-H3: Device Observation Feed

## Purpose

Accept external device readings (e.g. Dozee, Philips IntelliVue) and map
them into bedside chart observations, with idempotency, audit, optional
manual validation, and out-of-range alerting.

## Scope

- Pluggable device source architecture (not hardcoded to any device)
- Parameter mapping with unit conversion
- Idempotent ingestion via unique idempotency keys
- Optional manual nurse validation workflow
- Out-of-range detection and realtime alerts
- Full audit trail with raw payload storage
- Device-generated flag on chart entries

## Reused Custom DocTypes

| DocType | Usage |
|---------|-------|
| IPD Chart Template | Referenced by mapping config |
| IPD Bedside Chart | Target for auto-created chart entries |
| IPD Chart Entry | `is_device_generated`, `device_feed` fields added |

## New Custom DocTypes

### Device Observation Feed

| Field | Type | Notes |
|-------|------|-------|
| source_device_type | Data | e.g. "Dozee" |
| source_device_id | Data | Unique device identifier |
| patient | Link (Patient) | |
| inpatient_record | Link (Inpatient Record) | |
| bedside_chart | Link (IPD Bedside Chart) | Set after mapping |
| status | Select | Received/Mapped/Validated/Rejected/Error |
| received_at | Datetime | |
| processed_at | Datetime | Read-only |
| idempotency_key | Data | Unique |
| chart_entry | Link (IPD Chart Entry) | Read-only |
| payload | JSON | Raw device payload |
| requires_validation | Check | From mapping config |
| validated_by | Link (User) | |
| validated_at | Datetime | |
| readings | Table (Device Observation Reading) | |

### Device Observation Reading (child table)

| Field | Type | Notes |
|-------|------|-------|
| parameter_name | Data | Chart parameter name |
| raw_value | Data | Original device value |
| mapped_value | Float | After unit conversion |
| uom | Data | |
| is_out_of_range | Check | Read-only |

### Device Observation Mapping

| Field | Type | Notes |
|-------|------|-------|
| source_device_type | Data | |
| chart_template | Link (IPD Chart Template) | |
| is_active | Check | |
| requires_manual_validation | Check | |
| mappings | Table (Device Parameter Mapping) | |

### Device Parameter Mapping (child table)

| Field | Type | Notes |
|-------|------|-------|
| device_parameter | Data | Key in device payload |
| chart_parameter | Data | Parameter in chart template |
| unit_conversion_factor | Float | Default 1.0 |
| unit_conversion_offset | Float | Default 0.0 |

## API Endpoints

| Endpoint | Module | Auth |
|----------|--------|------|
| ingest_observation | api/device_feed.py | API key/secret |
| validate_feed | api/device_feed.py | Nursing User |
| get_pending_validations | api/device_feed.py | Nursing User |

## Permissions

| Role | Device Feed | Device Mapping |
|------|-------------|----------------|
| Device Integration User | Create/Read/Write | - |
| Healthcare Administrator | Read/Write | Full |
| ICU Administrator | - | Create/Read/Write |
| Nursing User | Read/Write | - |

## Validation Logic

- Mapping: no duplicate device parameters, conversion factor != 0
- Feed: idempotency key prevents reprocessing
- Range checks against chart template critical_low/critical_high

## Notifications

- Pending validation: in-app notification to Nursing User role
- Out-of-range: realtime event `device_critical_alert`

## Test Cases

See `tests/test_device_feed_service.py`:
- Basic ingestion with chart entry creation
- No mapping returns error
- Out-of-range detection
- Idempotency duplicate prevention
- Manual validation workflow (validate/reject)
- Unit conversion mapping
- Unmapped parameter passthrough
- Mapping validation (empty, duplicate)

## Open Questions / Assumptions

- One active mapping per (device_type, chart_template) pair
- Patient resolution from patient_id looks for active Admitted IR
- Readings with unmapped parameters are stored but not charted
- Raw payload preserved in JSON field for audit
