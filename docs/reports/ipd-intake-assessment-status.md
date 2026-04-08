# IPD Intake Assessment Status Report

## Purpose

Track pending vs completed intake assessments across specialties, wards, and date ranges. Helps nursing supervisors and admin staff identify bottlenecks in the admission assessment process.

## Type

Script Report

## Reference DocType

IPD Intake Assessment

## Filters

| Filter | Type | Default | Notes |
|--------|------|---------|-------|
| Company | Link → Company | — | Filter by company |
| Specialty | Link → Medical Department | — | Filter by medical department |
| Status | Select | — | Draft / In Progress / Completed |
| From Date | Date | 1 month ago | Assessment created after this date |
| To Date | Date | Today | Assessment created before this date |
| Template | Link → IPD Intake Assessment Template | — | Filter by specific template |

## Columns

| Column | Type | Width |
|--------|------|-------|
| Assessment | Link → IPD Intake Assessment | 180 |
| Patient | Link → Patient | 160 |
| Patient Name | Data | 160 |
| Inpatient Record | Link → Inpatient Record | 160 |
| Template | Link → IPD Intake Assessment Template | 200 |
| Specialty | Link → Medical Department | 140 |
| Status | Data | 100 |
| Assessed By | Link → Healthcare Practitioner | 140 |
| Created On | Datetime | 160 |
| Completed On | Datetime | 160 |
| Completed By | Link → User | 140 |

## Roles

- Healthcare Administrator
- Nursing User
- Physician
- IPD Admission Officer

## File Location

`alcura_ipd_ext/alcura_ipd_ext/report/ipd_intake_assessment_status/`
