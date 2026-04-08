# Report: Doctor Census

## Purpose

Provides a practitioner-centric view of all currently admitted patients, designed for daily ward round preparation. Shows key metrics at a glance: location, length of stay, active problems, pending tests, due medications, critical alerts, last progress note, vitals currency, allergy alerts, and overdue charts.

## Type

Script Report

## Reference DocType

Inpatient Record

## Filters

| Filter | Type | Required | Default | Notes |
|--------|------|----------|---------|-------|
| Practitioner | Link -> Healthcare Practitioner | Yes | -- | Filter by primary practitioner |
| Company | Link -> Company | No | User default | -- |
| Ward | Link -> Hospital Ward | No | -- | Filter by current ward |
| Department | Link -> Medical Department | No | -- | Filter by medical department |

## Columns

| Column | Type | Width | Notes |
|--------|------|-------|-------|
| Inpatient Record | Link | 140 | Links to the IR form |
| Patient | Link | 120 | Links to the Patient form |
| Patient Name | Data | 160 | -- |
| Ward | Data | 100 | Current ward from IR custom fields |
| Room | Data | 80 | Current room |
| Bed | Data | 80 | Current bed |
| Admitted | Date | 100 | Admission (scheduled) date |
| Days | Int | 60 | Computed: today - admission_date + 1; highlighted red when > 7 |
| Problems | Int | 80 | Active problem count; orange pill when > 0 |
| Pending Tests | Int | 90 | Active lab orders count; blue pill when > 0 |
| Due Meds | Int | 80 | Today's due medication entries; orange pill when > 0 |
| Critical | Int | 70 | Critical observation alerts; red pill when > 0 |
| Last Note | Date | 100 | Date of last progress note |
| Last Vitals | Datetime | 140 | Timestamp of last vitals chart entry |
| Allergy | Check | 70 | Red "ALLERGY" pill when true |
| Overdue | Int | 80 | Count of overdue bedside charts; red pill when > 0 |
| Department | Data | 120 | Medical department |

## Report Summary

Summary cards displayed above the grid:
- Total Patients (count)
- With Critical Alerts (red indicator)
- Overdue Charts (orange indicator)
- Pending Tests (blue indicator)

## Interactive Features

- **Start Round Note** button — creates a Progress Note encounter for the selected patient row and navigates to the form
- **View Round Summary** button — opens a dialog with full clinical snapshot (problems, vitals, labs, meds, fluid balance, recent notes)
- Row selection via standard Frappe report checkboxes

## Permissions

| Role | Access |
|------|--------|
| Physician | Yes |
| Healthcare Administrator | Yes |

## Data Source

Single query against `tabInpatient Record` filtered by `primary_practitioner` and `status = "Admitted"`, reading custom fields for location, allergies, problem counts, charting status, pending tests, due medications, and critical alerts. Days admitted is computed server-side from `scheduled_date`.
