# ADR: Room Type — Reuse Healthcare Service Unit Type vs Custom DocType

## Status

Accepted

## Date

2026-04-08

## Context

US-A2 requires storing room-type metadata for Indian hospital IPD operations: room category (General, Private, ICU, etc.), occupancy class, nursing intensity, critical-care and isolation flags, package eligibility, and default tariff linkage.

The question is whether to:

- **Option A**: Extend the standard `Healthcare Service Unit Type` with custom fields
- **Option B**: Create a new custom doctype (e.g., `IPD Room Type`) that wraps or references the standard HSUT

## Decision

**Option A: Extend Healthcare Service Unit Type with custom fields.**

## Rationale

### Arguments for extending (chosen)

1. **Preserves the standard billing pipeline.** HSUT's `is_billable` flag auto-creates an `Item` linked to the service-unit type. This Item flows into Sales Invoices via the existing billing infrastructure. A wrapper doctype would need to duplicate or redirect this mechanism.

2. **Keeps the standard reference chain intact.** The chain `Healthcare Service Unit Type → Healthcare Service Unit → Inpatient Record → Sales Invoice` is already wired in ERPNext Healthcare. Custom fields on HSUT keep this chain working without any overrides.

3. **No indirection layer.** A custom doctype would require every downstream query, filter, and report to join through an extra table. Custom fields add columns directly to the existing table.

4. **Clean UI with `depends_on`.** Custom fields with `depends_on: eval:doc.inpatient_occupancy` are only displayed when relevant (inpatient types). Consulting-room types see a clean, uncluttered form.

5. **Upgrade safety.** Custom fields are a first-class Frappe extension mechanism. They survive app upgrades and are exported/imported via fixtures.

6. **Precedent.** ERPNext itself extends standard doctypes this way (e.g., HRMS adds fields to Employee, ERPNext adds fields to Item). This is the established pattern.

### Arguments for a custom doctype (rejected)

1. **Full form control.** A dedicated doctype allows complete control over layout, permissions, and workflow. However, the metadata we're adding is simple (a handful of select/check/link fields) and does not justify a separate form.

2. **Cleaner separation.** IPD-specific fields would not exist on non-IPD HSUT records at the database level. However, the columns are nullable and have no storage or performance impact. The UI hides them via `depends_on`.

3. **Independent permissions.** A separate doctype could have its own role-permission matrix. However, room-type configuration is an administrative action that aligns with the existing HSUT permissions (Healthcare Administrator).

### Trade-offs accepted

- Custom fields are present as database columns on ALL Healthcare Service Unit Type records, even non-IPD ones. This is a negligible overhead (nullable columns, no index cost for unqueried values).
- We cannot fully restructure the HSUT form. Custom fields are appended after the `disabled` field. This is acceptable since the IPD section is logically a separate concern that belongs at the bottom.
- If Frappe/ERPNext core ever adds fields with the same names (unlikely given our `ipd_` prefix), a migration would be needed.

## Consequences

- All IPD room-type metadata lives on `Healthcare Service Unit Type` via 11 custom fields.
- No new doctype is created for this story.
- The `after_install` hook creates the custom fields; `before_uninstall` removes them.
- Custom fields are exported as fixtures filtered by `module = "Alcura IPD Extensions"`.
- Future stories that need room-type data can query HSUT directly without a join.
- If requirements grow significantly (e.g., complex room-type workflows, submittable lifecycle), this decision can be revisited and a dedicated doctype created at that time.

## Related

- [US-A2 Module Doc](../modules/us-a2-room-types.md)
- [US-A1 Ward Master](../modules/us-a1-ward-master.md) — Hospital Ward links to HSUT via `healthcare_service_unit_type`
