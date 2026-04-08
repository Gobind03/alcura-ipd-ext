# US-I2: Payer Billing Rules — Test Scenarios

## Line Split Unit Tests

1. Non-payable item → full patient liability
2. Excluded consumable → full patient liability + excluded flag
3. Package inclusion → zero charge
4. Default co-pay applied correctly
5. Co-pay override applied for specific item
6. Zero co-pay → full payer coverage
7. 100% co-pay → full patient liability

## Bill Split Integration Tests

8. Sub-limit applied across multiple items in same category
9. Deductible reduces payer total, increases patient total
10. Preauth overshoot calculated when payer total > approved amount
11. Room rent cap applied to room rent charges
12. Mixed rules: non-payable + co-pay + sub-limit in single bill

## DocType Validation Tests

13. Date range validation (valid_from > valid_to → error)
14. Missing co-pay percent on Co-Pay Override rule → error
15. Missing sub-limit amount on Sub-Limit rule → error
16. Missing cap amount on Room Rent Cap rule → error
17. Payer required for Corporate/PSU payer type
18. Insurance Payor required for Insurance TPA payer type

## Rule Set Resolution Tests

19. Specific payer match takes priority over generic
20. Date-range filtering works correctly
21. Inactive rule sets are skipped
22. No matching rule set → profile-level co-pay only
