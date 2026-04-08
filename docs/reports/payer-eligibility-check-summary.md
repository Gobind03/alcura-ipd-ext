# Payer Eligibility Check Summary — Report

## Purpose

Provides a filterable overview of all payer eligibility verification records. Helps TPA coordinators and administrators track verification status, identify pending checks, and monitor approval trends.

## Type

Script Report on `Payer Eligibility Check`

## Access

| Role | Access |
|------|--------|
| Healthcare Administrator | Yes |
| TPA Desk User | Yes |
| Accounts User | Yes |

## Filters

| Filter | Type | Options |
|--------|------|---------|
| Status | Select | Pending, Verified, Conditional, Rejected, Expired |
| Payer Type | Select | Cash, Corporate, Insurance TPA, PSU, Government Scheme |
| Company | Link | Company |
| From Date | Date | Creation date range start |
| To Date | Date | Creation date range end |

## Columns

| Column | Type | Width |
|--------|------|-------|
| Check ID | Link (Payer Eligibility Check) | 160 |
| Patient | Link (Patient) | 140 |
| Patient Name | Data | 160 |
| Payer Profile | Link (Patient Payer Profile) | 160 |
| Payer Type | Data | 120 |
| Status | Data | 100 |
| Approved Amount | Currency | 130 |
| Pre-Auth Ref | Data | 130 |
| Verified By | Link (User) | 140 |
| Verified On | Datetime | 160 |
| Valid To | Date | 110 |
| Inpatient Record | Link (Inpatient Record) | 140 |
| Company | Link (Company) | 140 |

## Visual Features

- Status column uses color-coded indicator pills:
  - Pending: orange
  - Verified: green
  - Conditional: blue
  - Rejected: red
  - Expired: grey

## Data Source

Direct SQL query on `tabPayer Eligibility Check` with parameterized filters. Ordered by `modified DESC`.

## Workspace

Available from the IPD Desk workspace under the Reports section.
