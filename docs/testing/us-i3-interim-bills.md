# US-I3: Interim Bills — Test Scenarios

## Cash Split Tests

1. All items fully patient-liable for cash patients
2. Empty line items return zero totals

## Structure Tests

3. Missing inpatient record raises error
4. Return dict contains all expected keys

## Room Charge Tests

5. Room charges computed from bed movement history
6. Multiple movements produce multiple charge lines
7. Tariff resolution uses payer-aware rates

## Clinical Order Tests

8. Completed orders included in charges
9. Draft/On Hold orders appear in pending items

## Deposit Tests

10. Payment Entry advances correctly summed
11. No customer returns zero deposits

## Integration Tests

12. Full bill with room + clinical charges + payer rules + preauth
13. Cash patient bill bypasses rule engine
