# ADR: Unified Clinical Order Model

## Status

Accepted

## Context

The IPD workflow requires tracking of medication, lab test, radiology, and procedure orders. These order types share common lifecycle stages (ordering, acknowledgment, execution, completion), SLA tracking requirements, and notification patterns.

Two approaches were considered:
1. **Separate doctypes** per order type (IPD Medication Order, IPD Lab Order, etc.)
2. **Unified doctype** with an `order_type` discriminator field

## Decision

We chose a **single `IPD Clinical Order` doctype** with an `order_type` discriminator (Medication / Lab Test / Radiology / Procedure) and type-specific field sections controlled by `depends_on` expressions.

## Rationale

- **Shared infrastructure:** SLA tracking, notifications, queue pages, and reports operate on all order types uniformly. A single doctype eliminates duplicate service layer code.
- **Consistent with existing patterns:** The `Patient Encounter` already uses a polymorphic approach with different note types via `custom_ipd_note_type`. The charting subsystem uses template-driven polymorphism.
- **Queue performance:** Department queues need to query across order types (Nurse Station Queue shows all types). A single table with composite indexes is more efficient than UNION queries across multiple doctypes.
- **Simpler permission model:** One set of permissions covers all order types, with role-based field visibility handled by the UI.
- **Extensibility:** New order types (e.g., Diet, Physiotherapy) can be added by extending the Select options and adding type-specific fields without creating new doctypes.

## Consequences

- **Larger schema:** The doctype JSON has more fields than a type-specific doctype would, but `depends_on` keeps the form clean.
- **Validation complexity:** The Python controller must validate different required fields based on `order_type`, which is handled in `_validate_order_type_fields()`.
- **Migration path:** If order types diverge significantly in the future, the unified model can be decomposed by creating type-specific doctypes and migrating data via a patch.

## Alternatives Rejected

- **Separate doctypes:** Would require 4+ doctypes, 4+ controllers, duplicated SLA/notification logic, and complex UNION queries for cross-type views.
- **Abstract base class:** Frappe doesn't support doctype inheritance, so this would require significant framework workarounds.
