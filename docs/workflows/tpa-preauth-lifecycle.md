# TPA Preauth Lifecycle

## States

1. **Draft** — initial creation, not yet sent to TPA
2. **Submitted** — sent to TPA for review
3. **Query Raised** — TPA has requested additional information
4. **Resubmitted** — hospital has responded to TPA query
5. **Approved** — TPA has approved the full requested amount
6. **Partially Approved** — TPA has approved a lesser amount
7. **Rejected** — TPA has declined the request
8. **Closed** — final state after settlement or administrative closure

## Transition Rules

- All transitions are enforced server-side in `tpa_preauth_request.py`
- Each transition records the acting user and timestamp in audit fields
- Timeline comments are posted on Patient and Inpatient Record
- Notifications are sent to relevant roles

## Query-Response Cycle

- When TPA raises a query, the hospital adds a Response-type entry to the responses child table
- The request is then Resubmitted
- This cycle can repeat multiple times
- Each response entry captures: type, user, datetime, text, and optional attachment

## Audit Trail

Every status change records:
- Who made the change (user)
- When the change occurred (datetime)
- A timeline comment on linked Patient and Inpatient Record
