# Active Protocol Bundle

## Purpose

Tracks an activated protocol for a specific patient admission, including
step completion status and compliance scoring.

## Naming

`APB-.#####` (naming series)

## Key Fields

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| protocol_bundle | Link | Yes | Master protocol definition |
| patient | Link | Yes | |
| inpatient_record | Link | Yes | |
| status | Select | Auto | Active/Completed/Discontinued/Expired |
| compliance_score | Percent | Auto | Computed from step weights |
| step_trackers | Table | Auto | Generated from bundle steps |

## Status Flow

Active -> Completed (all steps terminal)
Active -> Discontinued (manual with reason)
Active -> Expired (duration-based, future)

## Permissions

| Role | CRUD |
|------|------|
| Physician | Create/Read/Write |
| ICU Administrator | Create/Read/Write |
| Healthcare Administrator | Read/Write |
| Nursing User | Read/Write |
