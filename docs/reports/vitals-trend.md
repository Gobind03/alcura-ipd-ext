# Vitals Trend Report

## Purpose

Line chart visualization of vital parameter values over time for a patient or admission.

## Type

Script Report (ref_doctype: IPD Chart Entry)

## Filters

| Filter | Type | Required |
|--------|------|----------|
| inpatient_record | Link: Inpatient Record | No |
| patient | Link: Patient | No |
| from_date | Date | No (default: -7 days) |
| to_date | Date | No (default: today) |

## Columns

Entry Date/Time, Parameter, Value, UOM, Critical flag, Recorded By, Patient, Entry link.

## Visualization

Multi-line chart with one series per parameter (Temperature, Pulse, BP, SpO2, etc.). Only numeric non-zero values are plotted. Uses Frappe Charts.

## Data Source

Joins `IPD Chart Entry` (Active, Vitals type) with `IPD Chart Observation` to retrieve parameter values chronologically.

## Permissions

Healthcare Administrator, Nursing User, Physician.
