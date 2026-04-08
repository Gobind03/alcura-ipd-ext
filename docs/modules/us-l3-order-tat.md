# US-L3: Order-to-Execution TAT Report

## Purpose

Enable COOs, nursing heads, and department managers to analyse turnaround times for medication, lab, radiology, and procedure orders by department, ward, and urgency level, comparing actual performance against SLA targets to drive operational improvement.

## Scope

Enhancement to the existing Order TAT Report and SLA Breach Report to add:
- Summary metrics (avg TAT, median TAT, avg ack TAT, breach percentage)
- Department breakdown via `target_department` column and filter
- SLA target comparison column sourced from `IPD Order SLA Config`
- Bar chart showing average TAT vs SLA target by order type
- SLA Breach Report enhancements: department column, summary metrics, breach-by-type chart

## Reused Standard DocTypes

- **Healthcare Practitioner** — consultant filter
- **Medical Department** — department filter

## Reused Custom DocTypes

- **IPD Clinical Order** — primary data source with `ordered_at`, `acknowledged_at`, `completed_at`, `is_sla_breached`, `sla_breach_count`, `target_department`
- **IPD Order SLA Config** — SLA target definitions by order type and urgency
- **IPD Order SLA Milestone** — individual milestone tracking for breach detail
- **Hospital Ward** — ward filter

## New Custom DocTypes

None.

## Metric Definitions

| Metric | Definition |
|--------|------------|
| TAT (min) | `(completed_at - ordered_at)` in minutes |
| Ack TAT (min) | `(acknowledged_at - ordered_at)` in minutes |
| Avg TAT | Mean of all completed order TATs in the filtered set |
| Median TAT | Median of all completed order TATs |
| % Breached | `(breached_orders / total_orders) * 100` |
| Delay (min) | `(actual_at - target_at)` for breached milestones |
| SLA Target (min) | From `IPD Order SLA Config` for the order's type and urgency |

## Report Enhancements

### Order TAT Report
- New column: `target_department` (Department)
- New column: `sla_target_minutes` (SLA Target)
- New filter: Department
- Report summary: 5 cards (Total Orders, Avg TAT, Median TAT, Avg Ack TAT, % Breached)
- Chart: Bar chart of avg TAT by order type with SLA target overlay

### SLA Breach Report
- New column: `target_department` (Department)
- New filter: Department
- Report summary: 4 cards (Breached Orders, Total Breaches, Avg Delay, Max Delay)
- Chart: Bar chart of breach count by order type

## Permissions

| Role | Order TAT | SLA Breach |
|------|-----------|------------|
| Healthcare Administrator | Yes | Yes |
| Physician | Yes | No |
| Nursing User | Yes | Yes |

## Client-Side UX

- TAT values highlighted red when exceeding SLA target
- Urgency levels with color-coded pills (STAT/Emergency=red, Urgent=orange)
- Breached milestone pills in red
- High delay values (>60 min) in bold red

## Validation Logic

All TAT calculations are server-side. Date range filters are required.

## Performance

- SQL queries with parameterised conditions (no ORM N+1)
- SLA targets loaded once via batch query
- Order limit of 2000 rows for TAT report, 1000 for breach report

## Test Cases

See `docs/testing/us-l3-tests.md`

## Open Questions / Assumptions

- The SLA target comparison uses the `IPD Order SLA Config` doctype. If no config exists for a given order_type/urgency combination, the column shows null.
- Chart shows SLA target for "Routine" urgency only (as a baseline reference). SLA targets for other urgency levels can be viewed in the individual row data.
