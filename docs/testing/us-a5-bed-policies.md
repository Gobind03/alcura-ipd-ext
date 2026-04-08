# Testing: US-A5 — Configure Hospital Bed Policies

## Test File

`alcura_ipd_ext/alcura_ipd_ext/doctype/ipd_bed_policy/test_ipd_bed_policy.py`

## Test Scenarios

### 1. Defaults

| # | Scenario | Expected |
|---|----------|----------|
| 1.1 | `get_policy()` called without saving the Single | Returns hard-coded defaults (all exclusions enabled, Strict gender, Advisory payer, 60min SLA, 120min reservation, 0 buffer) |

### 2. Saved Values

| # | Scenario | Expected |
|---|----------|----------|
| 2.1 | Save with `exclude_dirty_beds=0`, `gender_enforcement=Ignore`, `cleaning_turnaround_sla_minutes=30`, `enforce_payer_eligibility=Strict` | `get_policy()` returns the saved values after cache clear |

### 3. Validation — Non-Negative Integers

| # | Scenario | Expected |
|---|----------|----------|
| 3.1 | Save with `cleaning_turnaround_sla_minutes = -10` | `ValidationError` raised |
| 3.2 | Save with `reservation_timeout_minutes = -5` | `ValidationError` raised |
| 3.3 | Save with `min_buffer_beds_per_ward = -1` | `ValidationError` raised |
| 3.4 | Save with all integer fields set to 0 | Saves successfully |

### 4. Permissions

| # | Scenario | Expected |
|---|----------|----------|
| 4.1 | Healthcare Administrator saves the policy | Succeeds |
| 4.2 | Nursing User attempts to save | `PermissionError` raised |
| 4.3 | Nursing User reads the policy | Succeeds (read-only access) |
