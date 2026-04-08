# Device Observation Feed

## Purpose

Records incoming device readings for audit and processing. Each feed
represents one device observation event with its raw payload, mapped
readings, and processing status.

## Naming

`DOF-.#####` (naming series)

## Key Fields

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| source_device_type | Data | Yes | Device manufacturer/model |
| source_device_id | Data | Yes | Unique device identifier |
| patient | Link (Patient) | No | |
| inpatient_record | Link (Inpatient Record) | No | |
| status | Select | Auto | Received/Mapped/Validated/Rejected/Error |
| received_at | Datetime | Yes | |
| idempotency_key | Data | No | Unique if provided |
| payload | JSON | No | Raw device payload |
| readings | Table | No | Mapped readings |

## Status Flow

Received -> Mapped (auto-processed) or Received (awaiting validation)
Received -> Validated (nurse approved) or Rejected (nurse rejected)
Received/Mapped -> Error (processing failure)

## Permissions

| Role | CRUD |
|------|------|
| Device Integration User | Create/Read/Write |
| Healthcare Administrator | Read/Write |
| Nursing User | Read/Write |

## Related DocTypes

- Device Observation Mapping (configuration)
- IPD Chart Entry (created from feed)
- IPD Bedside Chart (target)
