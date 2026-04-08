# Device Observation Exception

## Purpose

ICU-focused report showing device feed failures, missing observation
intervals, and unacknowledged critical readings to close monitoring
gaps.

## Type

Script Report (ref_doctype: Device Observation Feed)

## Filters

| Filter          | Type               | Required | Default      |
|-----------------|--------------------|----------|--------------|
| From Date       | Date               | Yes      | Yesterday    |
| To Date         | Date               | Yes      | Today        |
| Exception Type  | Select             | No       | All          |
| Ward            | Link (Hospital Ward)| No      | All          |
| Patient         | Link (Patient)     | No       | All          |
| Device Type     | Data               | No       | All          |

## Exception Type Options

- Connectivity Failure
- Missing Observation
- Unacknowledged Abnormal

## Columns

| Column        | Type         | Width | Notes                      |
|---------------|-------------|-------|----------------------------|
| Exception Type| Data        | 180   | Color-coded pill           |
| Date/Time     | Datetime    | 170   |                            |
| Patient       | Link        | 120   |                            |
| Patient Name  | Data        | 150   |                            |
| Ward          | Link        | 120   |                            |
| Device Type   | Data        | 130   |                            |
| Device ID     | Data        | 120   |                            |
| Chart         | Link        | 130   | IPD Bedside Chart link     |
| Parameter     | Data        | 120   | For abnormal readings      |
| Description   | Data        | 250   |                            |
| Source Type   | Data        | 140   |                            |
| Source        | Dynamic Link| 140   | Drilldown to source record |

## Report Summary

- Total Exceptions (red/green)
- Connectivity Failures (red)
- Missing Observations (orange)
- Unacknowledged Abnormals (red)

## Chart

Bar chart showing exception count by type.

## Data Logic

Three separate queries (one per exception type) produce rows
normalized to a common format, sorted by datetime descending.

## Access

- Healthcare Administrator
- ICU Administrator
- Nursing User
