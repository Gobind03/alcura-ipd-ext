# Bed Reservation

## Purpose

Manages the lifecycle of a bed hold for a scheduled patient admission. Supports two modes: reserving a specific named bed or holding capacity by room type.

## Module

Alcura IPD Extensions

## Naming

`naming_series: BED-RES-.#####` (e.g., BED-RES-00001)

## Track Changes

Yes

## Is Submittable

No — lifecycle is status-driven (Draft / Active / Expired / Cancelled / Consumed)

## Fields

### Reservation Identity

| Fieldname | Type | Options | Required | Notes |
|-----------|------|---------|----------|-------|
| naming_series | Select | `BED-RES-.#####` | Yes | Hidden |
| reservation_type | Select | Specific Bed, Room Type Hold | Yes | Indexed |
| status | Select | Draft, Active, Expired, Cancelled, Consumed | Yes | Read-only, indexed |
| company | Link → Company | | Yes | Indexed |

### Patient & Consultant

| Fieldname | Type | Options | Required | Notes |
|-----------|------|---------|----------|-------|
| patient | Link → Patient | | No | Indexed |
| patient_name | Data | | No | Fetched from patient, read-only |
| consulting_practitioner | Link → Healthcare Practitioner | | No | |
| practitioner_name | Data | | No | Fetched, read-only |

### Bed Selection

| Fieldname | Type | Options | Required | Notes |
|-----------|------|---------|----------|-------|
| service_unit_type | Link → Healthcare Service Unit Type | | Conditional | Required for Room Type Hold; indexed |
| hospital_ward | Link → Hospital Ward | | No | Indexed |
| hospital_room | Link → Hospital Room | | No | Visible for Specific Bed only |
| hospital_bed | Link → Hospital Bed | | Conditional | Required for Specific Bed; indexed |
| bed_name | Data | | No | Fetched from bed, read-only |

### Reservation Window

| Fieldname | Type | Default | Required | Notes |
|-----------|------|---------|----------|-------|
| reservation_start | Datetime | Now | Yes | |
| timeout_minutes | Int | 120 (from IPD Bed Policy) | Yes | |
| reservation_end | Datetime | Auto-computed | No | Read-only, indexed (used by expiry query) |

### Provisional Payer

| Fieldname | Type | Options | Required | Notes |
|-----------|------|---------|----------|-------|
| payer_type | Select | Cash, Corporate, TPA | No | |
| payer | Link → Customer | | No | Visible when payer_type is Corporate or TPA |

### Notes

| Fieldname | Type | Required |
|-----------|------|----------|
| notes | Small Text | No |

### Audit Trail

| Fieldname | Type | Notes |
|-----------|------|-------|
| reserved_by | Link → User | Set on activation |
| reserved_on | Datetime | Set on activation |
| cancelled_by | Link → User | Set on cancellation |
| cancelled_on | Datetime | Set on cancellation |
| cancellation_reason | Small Text | Mandatory on cancel |
| is_override | Check | Set when override cancels |
| override_authorized_by | Link → User | |
| override_reason | Small Text | Mandatory on override |
| expired_on | Datetime | Set by scheduler |
| consumed_on | Datetime | Set on consume |
| consumed_by_inpatient_record | Link → Inpatient Record | Set on consume |

## Indexes

- `patient` (search_index)
- `hospital_bed` (search_index)
- `hospital_ward` (search_index)
- `service_unit_type` (search_index)
- `status` (search_index + in_standard_filter)
- `reservation_end` (search_index)
- `company` (search_index)

## Permissions

| Role | Read | Write | Create | Delete |
|------|------|-------|--------|--------|
| Healthcare Administrator | Yes | Yes | Yes | Yes |
| Nursing User | Yes | Yes | Yes | No |
| Physician | Yes | No | No | No |

## Controller

`alcura_ipd_ext/alcura_ipd_ext/doctype/bed_reservation/bed_reservation.py`

### Lifecycle Hooks

- `before_insert`: Sets default timeout from IPD Bed Policy, computes reservation_end, forces Draft status
- `validate`: Validates type-field coupling, reservation window, company match, recomputes end

### Whitelisted Methods

- `action_activate()`: Delegates to `bed_reservation_service.activate_reservation()`
- `action_cancel(reason, is_override, override_reason)`: Delegates to `cancel_reservation()`
- `action_consume(inpatient_record)`: Delegates to `consume_reservation()`

## Business Logic

All business logic lives in `alcura_ipd_ext/services/bed_reservation_service.py`. See source for race-safety implementation using `SELECT … FOR UPDATE`.

## Client Script

`alcura_ipd_ext/alcura_ipd_ext/doctype/bed_reservation/bed_reservation.js`

- Action buttons: Activate, Cancel, Override & Cancel, Mark as Consumed
- Field toggles based on reservation_type
- Link queries filtered to active/vacant entities
- Status indicator colors: Draft (grey), Active (blue), Expired (orange), Cancelled (red), Consumed (green)
