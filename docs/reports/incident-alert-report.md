# Incident Alert Report

## Purpose

Consolidated safety and quality incident report for quality managers,
enabling corrective action on fall-risk events, missed medications,
critical observations, and SLA breaches.

## Type

Script Report (ref_doctype: Inpatient Record)

## Filters

| Filter        | Type               | Required | Default      |
|---------------|--------------------|----------|--------------|
| From Date     | Date               | Yes      | 7 days ago   |
| To Date       | Date               | Yes      | Today        |
| Incident Type | Select             | No       | All          |
| Ward          | Link (Hospital Ward)| No      | All          |
| Patient       | Link (Patient)     | No       | All          |
| Severity      | Select             | No       | All          |

## Incident Type Options

- Fall Risk
- Pressure Risk
- Nutrition Risk
- Missed Medication
- Critical Observation
- SLA Breach

## Columns

| Column        | Type         | Width | Notes                      |
|---------------|-------------|-------|----------------------------|
| Date/Time     | Datetime    | 170   |                            |
| Incident Type | Data        | 150   | Color-coded pill           |
| Severity      | Data        | 90    | Red/orange/blue pill       |
| Patient       | Link        | 120   |                            |
| Patient Name  | Data        | 150   |                            |
| Ward          | Link        | 120   |                            |
| Description   | Data        | 250   |                            |
| Source Type   | Data        | 130   |                            |
| Source        | Dynamic Link| 140   | Drilldown to source record |
| Status        | Data        | 100   | Open/Closed/Resolved pill  |

## Report Summary

- Total Incidents (red/green indicator)
- Count per incident type with appropriate indicators

## Chart

Pie chart showing incident distribution by type.

## Data Logic

Four parallel queries normalize into a common row format, merged and
sorted by datetime descending. Each query limited to 500 rows.

## Access

- Healthcare Administrator
- Nursing User
- Physician
