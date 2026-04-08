# Order TAT Report

## Purpose

Analyse turnaround times for IPD Clinical Orders to identify bottlenecks and measure department performance against SLA targets.

## Type

Script Report with chart on `IPD Clinical Order`

## Filters

| Filter | Type | Required | Default |
|--------|------|----------|---------|
| From Date | Date | Yes | 7 days ago |
| To Date | Date | Yes | Today |
| Order Type | Select | No | All |
| Urgency | Select | No | All |
| Ward | Link (Hospital Ward) | No | All |
| Department | Link (Medical Department) | No | All |
| Consultant | Link (Healthcare Practitioner) | No | All |
| Status | Select | No | All |

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
| Acknowledged At | Datetime | Acknowledgment time |
| Completed At | Datetime | Completion time |
| TAT (min) | Float | Total turnaround in minutes (red when above SLA target) |
| Ack TAT (min) | Float | Time to acknowledgment in minutes |
| SLA Target (min) | Float | Configured SLA target from IPD Order SLA Config |
| SLA Breached | Check | Whether SLA was breached |

## Report Summary

- Total Orders (count)
- Avg TAT (min)
- Median TAT (min)
- Avg Ack TAT (min)
- % Breached (color-coded: red >10%, orange >5%, green otherwise)

## Chart

Bar chart showing average TAT by order type with SLA target (Routine urgency) overlay.

## Access

- Healthcare Administrator
- Physician
- Nursing User
