# SLA Breach Report

## Purpose

Identify and analyze orders that have breached their SLA targets, broken down by milestone, to drive operational improvement.

## Type

Script Report on `IPD Clinical Order` (filtered to `is_sla_breached = 1`)

## Filters

| Filter | Type | Required | Default |
|--------|------|----------|---------|
| From Date | Date | Yes | 7 days ago |
| To Date | Date | Yes | Today |
| Order Type | Select | No | All |
| Urgency | Select | No | All |
| Ward | Link (Hospital Ward) | No | All |

## Columns

| Column | Type | Description |
|--------|------|-------------|
| Order | Link | Order reference |
| Patient | Data | Patient name |
| Type | Data | Order type |
| Urgency | Data | Urgency level |
| Status | Data | Current status |
| Ward | Link | Patient ward |
| Doctor | Data | Ordering practitioner |
| Ordered At | Datetime | Order placement time |
| Breach Count | Int | Number of SLA breaches |
| Breached Milestone | Data | Which milestone was breached |
| Target | Datetime | SLA target time |
| Delay (min) | Float | Minutes overdue |

## Data Logic

Each breached milestone generates a separate row in the report, allowing analysis of which milestone categories are most frequently breached.

## Access

- Healthcare Administrator
- Nursing User
