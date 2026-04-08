# US-I4: Discharge Billing Checklist — Test Scenarios

## Auto-Check Unit Tests

1. Pending meds: returns clear when no active medication orders
2. Pending samples: returns clear when no pending samples
3. Unposted procedures: returns clear when no active procedure orders
4. Room rent closed: returns not clear when no discharge movement
5. TPA preauth: returns clear when no preauth exists

## Discharge Readiness Tests

6. No checklist exists → not ready
7. All items cleared → ready
8. Override authorized → ready

## Controller Tests

9. Status derived as Cleared when all items cleared/waived
10. Status derived as In Progress when mix of pending/cleared
11. Waiver requires reason (validation error if missing)

## Integration Tests

12. Create checklist from IR with payer → includes TPA check
13. Create checklist from cash IR → skips TPA check
14. Refresh auto-checks updates auto-derived items
15. Manual clear_item updates item status and audit fields
16. Override records user and datetime
