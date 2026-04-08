# Testing: US-H3 — Device Observation Feed

## Test File

`alcura_ipd_ext/tests/test_device_feed_service.py`

## Test Scenarios

### Ingestion (TestIngestion)

| Scenario | Method | Expectation |
|----------|--------|-------------|
| Basic ingestion | test_basic_ingestion | Chart entry created, device_generated=1 |
| No mapping | test_no_mapping_returns_error | Status = Error |
| Out-of-range | test_out_of_range_detected | Alert includes parameter |

### Idempotency (TestIdempotency)

| Scenario | Method | Expectation |
|----------|--------|-------------|
| Duplicate key | test_duplicate_key_returns_existing | Same feed returned, duplicate=True |

### Validation Workflow (TestValidationWorkflow)

| Scenario | Method | Expectation |
|----------|--------|-------------|
| Manual validation required | test_manual_validation_required | Status = Received, no chart entry |
| Validate feed | test_validate_feed | Status = Validated |
| Reject feed | test_reject_feed | Status = Rejected |

### Parameter Mapping (TestParameterMapping)

| Scenario | Method | Expectation |
|----------|--------|-------------|
| Unit conversion | test_unit_conversion | Correct converted value |
| Unmapped passthrough | test_unmapped_parameter_passthrough | Stored with mapped_value=None |

### Mapping Validation (TestMappingValidation)

| Scenario | Method | Expectation |
|----------|--------|-------------|
| Empty mappings | test_rejects_empty_mappings | ValidationError |
| Duplicate device params | test_rejects_duplicate_device_params | ValidationError |
