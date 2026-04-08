# US-E2: Nursing Admission Assessment — Test Scenarios

## Test File

`alcura_ipd_ext/tests/test_nursing_risk_service.py`

## Test Cases

| # | Test | Description |
|---|------|-------------|
| 1 | `test_classify_fall_risk_low` | Morse Fall Scale score 0-24 returns Low |
| 2 | `test_classify_fall_risk_moderate` | Morse Fall Scale score 25-44 returns Moderate |
| 3 | `test_classify_fall_risk_high` | Morse Fall Scale score >= 45 returns High |
| 4 | `test_classify_braden_no_risk` | Braden Scale score >= 19 returns No Risk |
| 5 | `test_classify_braden_low` | Braden Scale score 15-18 returns Low |
| 6 | `test_classify_braden_moderate` | Braden Scale score 13-14 returns Moderate |
| 7 | `test_classify_braden_high` | Braden Scale score 10-12 returns High |
| 8 | `test_classify_braden_very_high` | Braden Scale score <= 9 returns Very High |
| 9 | `test_classify_nutrition_low` | MUST score 0 returns Low |
| 10 | `test_classify_nutrition_medium` | MUST score 1 returns Medium |
| 11 | `test_classify_nutrition_high` | MUST score >= 2 returns High |
| 12 | `test_update_risk_flags_from_scored_assessments` | Submitting scored PAs updates IR risk fields |
| 13 | `test_allergy_extraction_from_intake` | Allergy data extracted from intake responses |
| 13b | `test_allergy_none_known` | None Known allergy returns no alert |
| 14 | `test_high_fall_risk_creates_todo` | High fall risk creates assignment |
| 15 | `test_high_pressure_risk_creates_todo` | High pressure risk creates assignment |
| 16 | `test_duplicate_alert_prevention` | Same alert not created twice |
| 17 | `test_allergy_alert_creates_comment` | Allergy alert adds IR timeline comment |
| 18 | `test_risk_flags_updated_timestamp` | Timestamp/user recorded on flag update |
| 19 | `test_risk_summary_api` | API returns correct risk summary |
| 20 | `test_ward_risk_overview` | Ward-level overview returns all admitted patients |

## Coverage Areas

- **Risk classification**: Pure function unit tests for all three scales at all thresholds
- **Risk flag persistence**: Integration tests verifying IR custom fields are updated
- **Allergy extraction**: Parsing intake assessment response rows for allergy data
- **Alert generation**: ToDo creation for fall, pressure, and nutrition risks
- **Idempotency**: Duplicate alert prevention across repeated invocations
- **Audit trail**: Timeline comments and timestamp recording
- **API layer**: Risk summary and ward overview return correct data
