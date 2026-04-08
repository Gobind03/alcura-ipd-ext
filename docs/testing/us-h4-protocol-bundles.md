# Testing: US-H4 — Protocol-Based Monitoring Bundles

## Test File

`alcura_ipd_ext/tests/test_protocol_bundle_service.py`

## Test Scenarios

### Bundle Validation (TestBundleValidation)

| Scenario | Method | Expectation |
|----------|--------|-------------|
| Empty steps | test_requires_steps | ValidationError |
| Duplicate step names | test_rejects_duplicate_step_names | ValidationError |
| Duplicate sequence | test_rejects_duplicate_sequence | ValidationError |
| Valid creation | test_valid_bundle_creation | Success |

### Activation (TestBundleActivation)

| Scenario | Method | Expectation |
|----------|--------|-------------|
| Creates trackers | test_activate_creates_trackers | 3 steps, Active |
| Duplicate blocked | test_duplicate_activation_blocked | ValidationError |
| Auto-starts chart | test_activate_auto_starts_chart | Chart created |

### Step Completion (TestStepCompletion)

| Scenario | Method | Expectation |
|----------|--------|-------------|
| Complete step | test_complete_step | Status = Completed |
| Double complete blocked | test_complete_already_completed_blocked | ValidationError |
| Skip step | test_skip_step | Status = Skipped |
| Skip requires reason | test_skip_requires_reason | ValidationError |

### Compliance Scoring (TestComplianceScoring)

| Scenario | Method | Expectation |
|----------|--------|-------------|
| Full compliance | test_full_compliance | 100%, Completed |
| Partial compliance | test_partial_compliance | Between 0-100% |

### Overdue Detection (TestOverdueDetection)

| Scenario | Method | Expectation |
|----------|--------|-------------|
| Overdue marked missed | test_overdue_steps_marked_missed | >= 2 missed |

### Discontinue (TestDiscontinue)

| Scenario | Method | Expectation |
|----------|--------|-------------|
| Discontinue bundle | test_discontinue_bundle | Discontinued |
| Requires reason | test_discontinue_requires_reason | ValidationError |

### Queries (TestBundleQueries)

| Scenario | Method | Expectation |
|----------|--------|-------------|
| List bundles for IR | test_get_bundles_for_ir | At least 1 |

## Report Testing

Protocol Compliance Report should be tested manually via Desk with
various filter combinations.
