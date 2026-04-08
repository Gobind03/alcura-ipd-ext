# Nursing Workload by Ward

## Purpose

Ward-level operational dashboard for nursing superintendents showing
patient load, acuity, and actionable backlog metrics to guide staffing
decisions.

## Type

Script Report (ref_doctype: Hospital Ward)

## Filters

| Filter  | Type              | Required | Default        |
|---------|-------------------|----------|----------------|
| Company | Link (Company)    | No       | User default   |
| Ward    | Link (Hospital Ward) | No    | All active     |

## Columns

| Column            | Type | Width | Notes                                  |
|-------------------|------|-------|----------------------------------------|
| Ward              | Link | 140   |                                        |
| Ward Name         | Data | 140   |                                        |
| Census            | Int  | 80    | Admitted patients in ward              |
| High Acuity       | Int  | 100   | Fall High or Pressure High/Very High   |
| Active Charts     | Int  | 110   | Charts with status = Active            |
| Overdue Charts    | Int  | 120   | Orange highlight when > 0              |
| Pending Meds      | Int  | 110   | Scheduled, not yet due                 |
| Overdue Meds      | Int  | 110   | Missed MAR entries, red when > 0       |
| Overdue Protocol  | Int  | 130   | Missed protocol steps                  |
| Workload Score    | Int  | 120   | Composite; green/orange/red pill       |

## Report Summary

- Total Patients (blue)
- Overdue Charts (orange/green)
- Overdue Meds (red/green)
- High Acuity (red/blue)
- Highest Workload ward name (red)

## Chart

Stacked bar chart with Census, Overdue Charts, and Overdue Meds per ward.

## Data Logic

All counts use batch SQL with `GROUP BY ward`. Overdue chart detection
reuses `charting_service.get_overdue_charts()`. Workload score is a
weighted sum (see module doc for formula).

## Access

- Healthcare Administrator
- Nursing User
