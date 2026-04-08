# Testing: US-H1 — ICU Monitoring Profiles

## Test File

`alcura_ipd_ext/tests/test_monitoring_profile_service.py`

## Test Scenarios

### Profile Validation (TestProfileValidation)

| Scenario | Method | Expectation |
|----------|--------|-------------|
| Empty template list | test_requires_at_least_one_template | ValidationError |
| Duplicate templates | test_rejects_duplicate_templates | ValidationError |
| Inactive template ref | test_rejects_inactive_template | ValidationError |
| Duplicate active unit_type | test_rejects_duplicate_active_unit_type | ValidationError |
| Bad frequency override | test_frequency_override_minimum | ValidationError |
| Valid profile | test_valid_profile_creation | Success |

### Profile Resolution (TestProfileResolution)

| Scenario | Method | Expectation |
|----------|--------|-------------|
| Global profile found | test_resolve_global_profile | Returns profile name |
| Company profile priority | test_company_profile_takes_priority | Company profile wins |
| No profile | test_no_profile_returns_none | Returns None |

### Auto-Application (TestAutoApplication)

| Scenario | Method | Expectation |
|----------|--------|-------------|
| Apply starts charts | test_apply_profile_starts_charts | Charts created with source_profile |
| Skips existing | test_apply_skips_existing_active_chart | No duplicates |
| Skips non-autostart | test_apply_skips_non_autostart | Only auto_start=1 |
| No profile = no-op | test_no_profile_for_ward_is_noop | Empty result |

### Profile Removal (TestProfileRemoval)

| Scenario | Method | Expectation |
|----------|--------|-------------|
| Discontinues profile charts | test_remove_profile_charts | Status = Discontinued |
| Preserves manual charts | test_manual_charts_not_removed | Manual chart untouched |

### Profile Swap (TestProfileSwap)

| Scenario | Method | Expectation |
|----------|--------|-------------|
| Classification change | test_swap_on_classification_change | Old removed, new started |
| Same classification | test_no_swap_same_classification | No-op |

### Compliance (TestProfileCompliance)

| Scenario | Method | Expectation |
|----------|--------|-------------|
| All mandatory active | test_compliant_when_all_mandatory_active | compliant=True |
| Mandatory missing | test_non_compliant_when_mandatory_missing | compliant=False |
