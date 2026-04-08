# US-A2: Define Room Types Using Reusable Service-Unit Types

## Purpose

Provide a standardised way to classify IPD room types (General, Private, ICU, etc.) for billing, tariff mapping, admission filtering, and occupancy management. Room types drive per-day rates, TPA pre-authorisation categories, and package eligibility.

## Scope

- Extend the standard Healthcare Service Unit Type with IPD-specific metadata
- Add room category, occupancy class, nursing intensity, critical-care/isolation flags
- Add package eligibility and default price list linkage for tariff compatibility
- Client-side UX helpers for instant feedback on category selection
- Server-side validation for consistency and mandatory fields
- Workspace shortcut for easy access

## Reused Standard DocTypes

| DocType | How Used |
|---------|----------|
| Healthcare Service Unit Type | Extended via custom fields; primary doctype for room-type definitions |
| Item | Auto-created by standard HSUT `is_billable` flow; unchanged |
| Price List | Linked as `default_price_list` for future payer-based tariff mapping |
| Healthcare Service Unit | Will link to HSUT (downstream, not modified in this story) |
| Inpatient Record | References Healthcare Service Unit (downstream, not modified) |

## New Custom DocTypes

None. This story extends an existing standard doctype.

## Fields Added to Standard DocTypes

### Healthcare Service Unit Type — Custom Fields

All fields are conditional on `inpatient_occupancy` being enabled.

#### IPD Room Classification Section

| Fieldname | Type | Options | Notes |
|-----------|------|---------|-------|
| `ipd_classification_section` | Section Break | — | Label: "IPD Room Classification" |
| `ipd_room_category` | Select | General, Twin Sharing, Semi-Private, Private, Deluxe, Suite, ICU, CICU, MICU, NICU, PICU, SICU, HDU, Burns, Isolation, Other | Standard filter enabled |
| `occupancy_class` | Select | Single, Double, Triple, Multi-Bed, Dormitory | Beds per room/unit |
| `nursing_intensity` | Select | Standard, Enhanced, High, Critical | Staffing level |
| `is_critical_care_unit` | Check | — | Read-only; auto-set from ipd_room_category |
| `supports_isolation` | Check | — | Auto-set for Isolation category; manually settable for others |

#### Package & Tariff Section (collapsible)

| Fieldname | Type | Options | Notes |
|-----------|------|---------|-------|
| `package_eligible` | Check | — | Whether this room type can be included in package billing |
| `default_price_list` | Link | Price List | Filtered to selling price lists; for future payer-based pricing |

## Workflow States

Not applicable. Healthcare Service Unit Type is a non-submittable master. Active/disabled status uses the existing `disabled` field.

## Permissions

No new permissions. Custom fields inherit the existing Healthcare Service Unit Type permission model:

| Role | Access |
|------|--------|
| Healthcare Administrator | Full CRUD |
| Other roles per standard HSUT | Read as configured |

## Validation Logic

1. **Category required**: If `inpatient_occupancy=1`, `ipd_room_category` must be set.
2. **Critical care auto-flag**: `is_critical_care_unit` is set to 1 when `ipd_room_category` ∈ {ICU, CICU, MICU, NICU, PICU, SICU, HDU, Burns}; otherwise 0.
3. **Isolation auto-flag**: `supports_isolation` is set to 1 when `ipd_room_category=Isolation`. Not cleared for other categories (allows manual override).
4. **Nursing intensity suggestion**: Auto-set to "Critical" for critical-care types when unset.
5. **Intensity mismatch warning**: Non-blocking alert when a critical-care type has "Standard" nursing intensity.

## Notifications

None for this story. Future stories may add notifications for room-type configuration changes that affect active tariffs.

## Reporting Impact

Room type metadata (category, occupancy class, nursing intensity, critical care flag) will serve as dimensions for:
- Bed availability by room category
- Occupancy reports by room type
- Revenue analysis by room category
- TPA pre-auth category matching

These reports will be built in subsequent stories.

## Test Cases

See [docs/testing/us-a2-room-types.md](../testing/us-a2-room-types.md).

## Open Questions / Assumptions

1. **`insert_after: disabled`**: Assumes the standard Healthcare Service Unit Type has a `disabled` field. If the field name differs in the Marley Health fork, the `insert_after` value must be adjusted.
2. **No modification to standard Item creation**: The `is_billable` + Item auto-creation flow is untouched. Custom fields sit alongside it.
3. **Room category option superset**: Options include all Hospital Ward classification values plus room-level categories (Twin Sharing, Semi-Private, Deluxe).
4. **Nursing intensity is suggestive**: Auto-set for critical care but manually overridable.
5. **`is_critical_care_unit` is read-only**: Set by server logic only, not user-editable, to prevent inconsistency.
6. **Price List link is forward-looking**: `default_price_list` establishes the linkage for future payer-based tariff stories. No billing logic depends on it yet.
