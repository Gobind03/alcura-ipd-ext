# US-I1: TPA Preauth — Test Scenarios

## Status Transition Tests

1. Draft → Submitted: verify audit fields populated
2. Submitted → Approved: verify approved_amount, approved_by, approved_on
3. Submitted → Partially Approved: verify approved_amount set
4. Submitted → Rejected: verify rejected_by, rejected_on
5. Submitted → Query Raised: verify notification sent to TPA Desk User
6. Query Raised → Resubmitted: verify cycle works
7. Approved → Closed: verify closed_by, closed_on
8. Invalid transition (Draft → Approved): verify ValidationError raised
9. Invalid transition (Draft → Closed): verify ValidationError raised

## Validation Tests

10. Date range: valid_from > valid_to raises error
11. Patient-profile mismatch raises error
12. Approved amount required on approval status

## Response Metadata Tests

13. Response child rows auto-populate response_by and response_datetime

## Audit Trail Tests

14. last_status_change_by and last_status_change_on updated on every transition
15. Timeline comment posted on Patient record
16. Timeline comment posted on Inpatient Record (when linked)

## API Tests

17. create_preauth_from_admission: pre-fills from IR and payer profile
18. create_preauth_from_admission: throws if no payer profile
19. create_preauth_from_admission: throws if Cash payer
20. create_preauth_from_order: pre-fills from clinical order
21. create_preauth_from_order: throws for non-Procedure/Radiology orders
22. get_preauth_summary: returns all preauths for an IR

## Permission Tests

23. TPA Desk User can create and write
24. Physician can only read
25. Accounts User can only read
