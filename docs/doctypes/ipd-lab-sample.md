# IPD Lab Sample

## Overview

Tracks the physical lab sample through its lifecycle — from creation, through collection and transport, to receipt in the lab. Supports recollection workflows and critical result acknowledgment.

## Module

Alcura IPD Extensions

## Naming

Auto-named via series: `SAMP-.#####`

## Key Fields

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| clinical_order | Link (IPD Clinical Order) | Yes | Lab Test order |
| patient | Link (Patient) | Yes | Auto-fetched |
| lab_test_name | Data | Yes | Auto-fetched from order |
| sample_type | Data | No | Blood, Urine, Swab, etc. |
| barcode | Data | Auto | Unique, auto-generated |
| status | Select | Yes | Pending → Collected → In Transit → Received → Processing → Completed / Rejected |
| collection_status | Select | Yes | Pending / Collected / Recollection Needed / Recollected |
| collected_by | Link (User) | Auto | Nurse/phlebotomist |
| collected_at | Datetime | Auto | |
| collection_site | Data | No | e.g., Left Antecubital |
| handed_off_by | Link (User) | On handoff | |
| transport_mode | Select | On handoff | Manual / Pneumatic Tube / Runner |
| received_by | Link (User) | On receipt | Lab technician |
| sample_condition | Select | On receipt | Acceptable / Hemolyzed / Clotted / Insufficient / Contaminated |
| parent_sample | Link (IPD Lab Sample) | On recollection | Original sample |
| is_critical_result | Check | Auto | Set by lab_test_events |
| critical_result_acknowledged_by | Link (User) | On acknowledgment | |
| linked_lab_test | Link (Lab Test) | Auto | Set on Lab Test submit |

## Status Transitions

Enforced by `transition_to()`:

| From | Valid To |
|------|----------|
| Pending | Collected, Rejected |
| Collected | In Transit, Received, Rejected |
| In Transit | Received, Rejected |
| Received | Processing, Rejected |
| Processing | Completed, Rejected |
| Completed | Terminal |
| Rejected | Terminal |

## Validations

- Lab samples can only be created for Lab Test orders
- Recollection requires a reason
- Critical result acknowledgment auto-sets timestamp

## Permissions

- **Laboratory User**: Create, Read, Write
- **Nursing User**: Create, Read, Write
- **Physician**: Read only
- **Healthcare Administrator**: Full access

## Related

- `alcura_ipd_ext.services.lab_sample_service`
- `alcura_ipd_ext.api.lab_sample`
- `alcura_ipd_ext.overrides.lab_test_events` (critical result detection)
