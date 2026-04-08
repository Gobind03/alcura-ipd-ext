# US-G3: Lab Sample Tests

## Test File

`alcura_ipd_ext/tests/test_lab_sample_service.py`

## Test Classes and Coverage

### TestSampleCreation

| Test | What it validates |
|------|------------------|
| `test_create_sample_from_order` | Creates sample with correct patient, lab_test_name, status, barcode |
| `test_create_sample_fails_for_medication` | Cannot create sample from Medication orders |
| `test_create_sample_fails_for_cancelled` | Cannot create sample from Cancelled orders |

### TestSampleCollection

| Test | What it validates |
|------|------------------|
| `test_record_collection` | Sets status to Collected, records collector, site, timestamp |

### TestSampleHandoff

| Test | What it validates |
|------|------------------|
| `test_record_handoff` | Sets status to In Transit, records transport mode |

### TestSampleReceipt

| Test | What it validates |
|------|------------------|
| `test_record_receipt_acceptable` | Sets status to Received, needs_recollection = False |
| `test_record_receipt_hemolyzed_triggers_recollection` | Bad condition triggers recollection, creates new sample |

### TestRecollection

| Test | What it validates |
|------|------------------|
| `test_request_recollection` | Marks original as Rejected, creates linked new sample |

### TestCriticalResult

| Test | What it validates |
|------|------------------|
| `test_acknowledge_critical_result` | Records acknowledger and timestamp |
| `test_acknowledge_non_critical_fails` | Cannot acknowledge non-critical samples |

### TestSampleTransitions

| Test | What it validates |
|------|------------------|
| `test_valid_transitions` | Full lifecycle: Pending → Collected → In Transit → Received → Processing → Completed |
| `test_invalid_transition_raises` | Pending → Completed raises ValidationError |
| `test_cannot_transition_from_terminal` | Rejected/Completed cannot transition further |

### TestCollectionQueue

| Test | What it validates |
|------|------------------|
| `test_collection_queue_returns_pending` | Queue returns pending samples |

### TestSampleLifecycle

| Test | What it validates |
|------|------------------|
| `test_full_lifecycle` | Returns all samples for an order |

## Running

```bash
bench --site <site> run-tests --app alcura_ipd_ext --module alcura_ipd_ext.tests.test_lab_sample_service
```
