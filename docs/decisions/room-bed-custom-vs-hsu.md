# ADR: Room & Bed — Custom DocTypes vs Healthcare Service Unit Custom Fields

## Status

Accepted

## Date

2026-04-08

## Context

US-A3 requires modelling individual hospital rooms and beds with rich operational
state: occupancy, housekeeping, maintenance hold, infection block, gender
restriction, and equipment readiness. Each bed must also integrate with the
standard billing/admission pipeline that flows through `Healthcare Service Unit`
→ `Inpatient Occupancy` → `Inpatient Record` → `Sales Invoice`.

Two approaches were evaluated:

- **Option A**: Add custom fields to `Healthcare Service Unit` for both rooms
  (group nodes) and beds (leaf nodes)
- **Option B**: Create dedicated `Hospital Room` and `Hospital Bed` custom
  doctypes, with each bed bridging to an auto-created HSU leaf node

## Decision

**Option B: Dedicated custom doctypes with HSU bridge.**

## Rationale

### Arguments for custom doctypes (chosen)

1. **Schema clarity.** Room-specific fields (room number, wing, AC flag) and
   bed-specific fields (housekeeping status, maintenance hold, infection block)
   are fundamentally different concerns. A single HSU record cannot cleanly
   represent both without heavy `depends_on` logic.

2. **Flat-table performance.** Nurse-station and IPD-desk workflows require
   high-throughput queries: "show all vacant, clean beds in ward X". Flat tables
   with indexed status columns (`occupancy_status`, `housekeeping_status`,
   `hospital_ward`) are significantly faster than tree-based queries with nested
   set model (lft/rgt) joins.

3. **Transaction safety.** Concurrent bed allocation requires row-level locking
   (`SELECT … FOR UPDATE`) on the bed record. NSM tree operations on HSU involve
   updating lft/rgt across many rows in the same transaction, increasing lock
   contention and deadlock risk.

4. **Uniqueness constraints.** Room number unique per ward and bed number unique
   per room are natural composite uniqueness rules. Enforcing these on HSU group/
   leaf nodes requires custom validation with race-condition guards. Dedicated
   doctypes make this straightforward with `for_update` queries.

5. **Clean forms for different roles.** Hospital Room and Hospital Bed get
   their own form layouts, list views, and permission matrices. Nurses see a
   bed-centric view; administrators see a room-centric view. Overloading the
   HSU tree view for these workflows would be awkward.

6. **Upgrade safety.** Custom fields on HSU would coexist with any fields
   Frappe/ERPNext or Marley Health add in future versions. Dedicated doctypes
   are fully isolated.

### Arguments for HSU custom fields (rejected)

1. **Single hierarchy.** All facility data lives in one tree. However, the tree
   view is rarely used for operational bed management; list views with filters
   are preferred.

2. **No bridge needed.** Billing pipeline works natively. However, the bridge
   (auto-create HSU leaf from Hospital Bed) is a one-time operation per bed and
   adds negligible complexity.

3. **Fewer doctypes.** True, but the operational complexity is merely moved into
   conditional field visibility and validation logic on a shared doctype.

### Trade-offs accepted

- Each Hospital Bed auto-creates a corresponding HSU leaf node, resulting in
  two records per physical bed. Storage overhead is negligible.
- Occupancy status must be kept in sync between Hospital Bed and HSU. A
  `doc_events` hook on HSU propagates changes triggered by the standard
  admission/discharge flow.
- Queries that need both operational state and billing data must join across
  Hospital Bed and HSU. This is acceptable because such queries are infrequent
  (reports, not real-time operations).

## Consequences

- Two new custom doctypes: `Hospital Room` and `Hospital Bed`.
- Each `Hospital Bed` links to one `Healthcare Service Unit` leaf node.
- The standard billing/admission pipeline is preserved without modification.
- Ward and room capacity counters are rolled up from Hospital Bed records.
- Future stories (transfers, occupancy dashboards, nurse station) query the
  flat Hospital Bed table for operational data.

## Related

- [US-A2 Room Type Reuse ADR](room-type-reuse-vs-custom.md)
- [US-A1 Ward Master](../modules/us-a1-ward-master.md)
- [US-A3 Module Doc](../modules/us-a3-room-bed-setup.md)
