# Overdue Charts Report

## Purpose

Ward-level monitor showing all bedside charts that are overdue for their next recording. Used by charge nurses and ward supervisors.

## Type

Script Report (ref_doctype: IPD Bedside Chart)

## Filters

| Filter | Type | Required |
|--------|------|----------|
| ward | Link: Hospital Ward | No |
| company | Link: Company | No |
| grace_minutes | Int | No (default: 0) |

## Columns

Chart link, Patient Name, Chart Type, Ward, Bed, Frequency (min), Last Entry, Next Due, Overdue (min).

## Data Source

Uses `charting_service.get_overdue_charts()`. Results sorted by overdue minutes descending (most overdue first).

## Permissions

Healthcare Administrator, Nursing User, Physician.
