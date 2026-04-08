# Order TAT Report

## Purpose

Analyze turnaround times for IPD Clinical Orders to identify bottlenecks and measure department performance against SLA targets.

## Type

Script Report on `IPD Clinical Order`

## Filters

| Filter | Type | Required | Default |
|--------|------|----------|---------|
| From Date | Date | Yes | 7 days ago |
| To Date | Date | Yes | Today |
| Order Type | Select | No | All |
| Urgency | Select | No | All |
| Ward | Link (Hospital Ward) | No | All |
| Consultant | Link (Healthcare Practitioner) | No | All |
| Status | Select | No | All |

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
| Acknowledged At | Datetime | Acknowledgment time |
| Completed At | Datetime | Completion time |
| TAT (min) | Float | Total turnaround time in minutes |
| Ack TAT (min) | Float | Time to acknowledgment in minutes |
| SLA Breached | Check | Whether SLA was breached |

## Access

- Healthcare Administrator
- Physician
- Nursing User
