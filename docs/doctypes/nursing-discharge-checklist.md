# Nursing Discharge Checklist

## Overview

A structured checklist for nurses to complete before patient discharge, ensuring safe clinical closure. Contains 15 standard items spanning line removal, medication counseling, patient education, belongings, documentation, and safety.

## Module

Alcura IPD Extensions

## Naming

`NDC-.YYYY.-.#####` (e.g., NDC-2026-00001)

## Key Fields

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| inpatient_record | Link (Inpatient Record) | ✓ | Unique, indexed |
| patient | Link (Patient) | ✓ | Indexed |
| discharge_advice | Link (IPD Discharge Advice) | — | |
| status | Select | — | Pending / In Progress / Completed (read_only) |
| items | Table (Nursing Discharge Checklist Item) | ✓ | |
| total_items | Int | — | Read-only, computed |
| completed_items | Int | — | Read-only, computed |

## Child Table: Nursing Discharge Checklist Item

| Field | Type | Notes |
|-------|------|-------|
| item_name | Data | Required |
| item_category | Select | Line Removal / Medication / Patient Education / Documentation / Safety / Belongings / Other |
| is_mandatory | Check | |
| item_status | Select | Pending / Done / Not Applicable / Skipped |
| detail | Small Text | |
| completed_by | Link (User) | Read-only |
| completed_on | Datetime | Read-only |
| skip_reason | Small Text | Required when Skipped |

## Signoff Fields

- `completed_by`, `completed_on` — set on checklist signoff
- `verified_by`, `verified_on` — set on senior nurse verification
- `handover_notes` — optional notes at signoff

## Status Derivation

- Pending: no items completed
- In Progress: at least one item completed
- Completed: signoff performed (all mandatory items done)

## Controller Methods (Whitelisted)

- `complete_item(item_idx)` — marks item Done
- `mark_not_applicable(item_idx)` — marks item Not Applicable
- `skip_item(item_idx, reason)` — marks item Skipped with reason
- `sign_off(handover_notes)` — completes checklist (validates mandatory items)
- `verify()` — senior nurse verification

## Standard Items (15)

9 mandatory items covering: IV line removal, medication counseling, pharmacy receipt, home-care instructions, warning signs education, belongings return, final vitals, wristband removal, and discharge papers signing.

6 optional items covering: catheter removal, drain removal, diet instructions, follow-up appointment, valuables check, and escort arrangement.
