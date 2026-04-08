# SLA Breach Report

## Purpose

Identify and analyse orders that have breached their SLA targets, broken down by milestone and department, to drive operational improvement.

## Type

Script Report with chart on `IPD Clinical Order` (filtered to `is_sla_breached = 1`)

## Filters

| Filter | Type | Required | Default |
|--------|------|----------|---------|
| From Date | Date | Yes | 7 days ago |
| To Date | Date | Yes | Today |
| Order Type | Select | No | All |
| Urgency | Select | No | All |
| Ward | Link (Hospital Ward) | No | All |
| Department | Link (Medical Department) | No | All |

## Columns

| Column | Type | Description |
|--------|------|-------------|
| Order | Link | Order reference |
| Patient | Data | Patient name |
| Type | Data | Order type |
| Urgency | Data | Urgency level (color-coded pills) |
| Status | Data | Current status |
| Ward | Link | Patient ward |
| Department | Link | Target department |
| Doctor | Data | Ordering practitioner |
| Ordered At | Datetime | Order placement time |
| Breach Count | Int | Number of SLA breaches for this order |
| Breached Milestone | Data | Which milestone was breached (red pill) |
| Target | Datetime | SLA target time |
| Delay (min) | Float | Minutes overdue (red when >60 min, orange otherwise) |

## Report Summary

- Breached Orders (unique order count, red indicator)
- Total Breaches (each milestone breach is counted)
- Avg Delay (min)
- Max Delay (min, red indicator)

## Chart

Bar chart showing breach count by order type.

## Data Logic

Each breached milestone generates a separate row, allowing analysis of which milestone categories are most frequently breached.

## Access

- Healthcare Administrator
- Nursing User
