# DocType: IPD Order SLA Config

## Overview

Configuration doctype that defines SLA (Service Level Agreement) targets for each combination of order type and urgency level. Used by the SLA service to initialize milestone targets when orders are placed.

## Naming

Auto-named as `{order_type}-{urgency}` (e.g., "Medication-STAT")

## Key Fields

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| order_type | Select | Yes | Medication/Lab Test/Radiology/Procedure |
| urgency | Select | Yes | Routine/Urgent/STAT/Emergency |
| is_active | Check | — | Default 1; inactive configs are ignored |
| milestones | Table (IPD SLA Milestone Target) | Yes | At least one milestone required |

## Child Table: IPD SLA Milestone Target

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| milestone | Data | Yes | e.g., "Acknowledged", "Dispensed", "Sample Collected" |
| sequence | Int | — | Execution order |
| target_minutes | Int | Yes | Minutes from order creation |
| escalation_role | Link (Role) | — | Role to notify on breach |
| escalation_delay_minutes | Int | — | Extra delay before escalation |

## Validation

- Unique combination of `order_type` + `urgency`
- At least one milestone required
- No duplicate milestone names within a config
- Target minutes must be positive

## Permissions

| Role | Access |
|------|--------|
| Healthcare Administrator | Full CRUD |
| Physician | Read only |

## Seed Data

Default configurations are created via patch `v0_0_6/setup_clinical_order_sla_defaults.py` covering all order type / urgency combinations with sensible Indian hospital defaults.
