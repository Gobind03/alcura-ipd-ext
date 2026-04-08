# Report: Nursing Risk Summary

## Purpose

Provide a ward-level overview of nursing risk indicators for all currently admitted patients. Helps nursing supervisors and charge nurses identify high-risk patients requiring immediate care interventions.

## Type

Script Report (server-side Python query, client-side JS formatters)

## Reference DocType

Inpatient Record

## Filters

| Filter | Type | Description |
|--------|------|-------------|
| Company | Link → Company | Filter by company |
| Ward | Link → Hospital Ward | Filter by ward |
| Risk Type | Select | Fall Risk / Pressure Injury / Nutrition / Allergy |
| Minimum Risk Level | Select | High / Moderate / Low — shows patients at or above this level |
| Consultant | Link → Healthcare Practitioner | Filter by primary consultant |

## Columns

| Column | Type | Width |
|--------|------|-------|
| Patient | Link → Patient | 120 |
| Patient Name | Data | 160 |
| Inpatient Record | Link → Inpatient Record | 140 |
| Ward | Link → Hospital Ward | 120 |
| Room | Data | 100 |
| Bed | Data | 100 |
| Consultant | Link → Healthcare Practitioner | 140 |
| Fall Risk | Data (with colored badge) | 100 |
| Pressure Risk | Data (with colored badge) | 110 |
| Nutrition Risk | Data (with colored badge) | 110 |
| Allergy | Check | 80 |
| Allergy Details | Data | 160 |
| Last Updated | Datetime | 140 |

## Visual Formatting

Risk levels are displayed as colored indicator pills:
- **Red**: High, Very High, ALLERGY
- **Orange**: Moderate, Medium
- **Green**: Low, No Risk
- **Blue**: Low (Braden)

## Data Source

Queries `Inpatient Record` where `status = "Admitted"`, reading custom risk flag fields.

## Risk Filtering Logic

When a "Minimum Risk Level" is selected:
- The report shows only patients whose risk in the selected type meets or exceeds the threshold
- When no specific type is selected, patients matching ANY risk at the threshold are shown

## Roles

- Healthcare Administrator
- Nursing User
- Physician

## Location

- IPD Desk workspace → Reports section
- Direct URL: `/app/query-report/Nursing Risk Summary`
