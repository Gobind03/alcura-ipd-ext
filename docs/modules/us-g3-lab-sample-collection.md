# US-G3: Lab Sample Collection and Processing

## Purpose

Enable phlebotomists, nurses, and lab technicians to digitally track the full lifecycle of lab samples — from collection at bedside, through transport and receipt in the lab, to result publication — with support for recollection, critical result acknowledgment, and SLA tracking.

## Scope

- Sample creation from lab test clinical orders
- Collection recording with site and notes
- Transport handoff tracking
- Lab receipt with condition assessment
- Automatic recollection on bad sample condition
- Critical result detection and acknowledgment flow
- Barcode-based sample identification

## Reused DocTypes

| DocType | Usage |
|---------|-------|
| IPD Clinical Order | Source of lab test orders |
| Lab Test | Standard ERPNext Healthcare Lab Test for results |

## New Custom DocType: IPD Lab Sample

Tracks the physical sample through its lifecycle independently from the Lab Test result.

### Key Fields

| Section | Fields |
|---------|--------|
| Identity | clinical_order, patient, lab_test_name, sample_type, barcode |
| Collection | collection_status, collected_by, collected_at, collection_site, is_fasting_sample |
| Handoff | handed_off_by, handed_off_at, transport_mode |
| Receipt | received_by, received_at, sample_condition |
| Recollection | recollection_reason, parent_sample (link to original) |
| Critical | is_critical_result, critical_result_acknowledged_by/at |
| Status | Pending → Collected → In Transit → Received → Processing → Completed / Rejected |

### Status Transitions

| From | Valid To |
|------|----------|
| Pending | Collected, Rejected |
| Collected | In Transit, Received, Rejected |
| In Transit | Received, Rejected |
| Received | Processing, Rejected |
| Processing | Completed, Rejected |
| Completed | (terminal) |
| Rejected | (terminal) |

## Integration with Lab Test Events

Enhanced `lab_test_events.py`:
- On Lab Test submit: updates linked IPD Lab Sample to "Completed"
- Checks for critical values (custom_critical_low/high fields)
- If critical: sets `is_critical_result` on sample, fires critical result notification

## SLA Milestones

1. Acknowledged
2. Sample Collected
3. Sample Handed Off
4. Sample Received in Lab
5. Result Published

## Permissions

| Role | Create | Read | Write | Delete |
|------|--------|------|-------|--------|
| Laboratory User | ✓ | ✓ | ✓ | |
| Nursing User | ✓ | ✓ | ✓ | |
| Physician | | ✓ | | |
| Healthcare Administrator | ✓ | ✓ | ✓ | ✓ |

## Notifications

| Event | Recipients | Method |
|-------|-----------|--------|
| Sample collected | Lab User | Realtime |
| Bad sample condition / recollection | Nursing User | Notification Log |
| Critical result | Ordering practitioner, Nursing, Physician | Notification Log + realtime |

## API Endpoints

| Endpoint | Method |
|----------|--------|
| `alcura_ipd_ext.api.lab_sample.create_sample` | POST |
| `alcura_ipd_ext.api.lab_sample.record_collection` | POST |
| `alcura_ipd_ext.api.lab_sample.record_handoff` | POST |
| `alcura_ipd_ext.api.lab_sample.record_receipt` | POST |
| `alcura_ipd_ext.api.lab_sample.request_recollection` | POST |
| `alcura_ipd_ext.api.lab_sample.acknowledge_critical_result` | POST |
| `alcura_ipd_ext.api.lab_sample.get_collection_queue` | GET |
| `alcura_ipd_ext.api.lab_sample.get_sample_lifecycle` | GET |

## Test Cases

See `docs/testing/us-g3-tests.md` and `tests/test_lab_sample_service.py`.
