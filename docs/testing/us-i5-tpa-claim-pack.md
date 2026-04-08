# US-I5: TPA Claim Pack — Test Scenarios

## Status Transition Tests

1. Draft → In Review: verify reviewed_by set
2. In Review → Submitted: verify submitted_by_user set
3. Submitted → Acknowledged: verify transition
4. Acknowledged → Settled: verify settlement fields
5. Submitted → Disputed: verify disallowance fields
6. Disputed → Submitted: verify resubmit cycle
7. Invalid transition (Draft → Submitted): raises error

## Document Tests

8. Pending documents returns only mandatory with no attachment
9. Refresh availability updates is_available based on file_attachment
10. All transition statuses covered in map

## Service Tests

11. create_claim_pack auto-populates standard document list
12. create_claim_pack links to preauth when available
13. create_claim_pack links to IR via custom field

## Audit Tests

14. Timeline comment posted on IR on status change
15. Prepared by/on set on insert
