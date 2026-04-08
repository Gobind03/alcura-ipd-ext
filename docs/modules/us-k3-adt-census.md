# US-K3: ADT Census Report

## Purpose

Provide medical superintendents with a daily ADT (Admission-Discharge-Transfer) report so that census and patient flow are monitored with operational accuracy.

## Scope

- Daily census showing opening count, admissions, transfers, discharges, deaths, closing count
- Per-ward breakdown
- Consultant filter for practitioner-specific views
- Stacked bar chart visualization
- Date navigation (previous/next day)

## Reused Standard DocTypes

| DocType | Usage |
|---------|-------|
| Bed Movement Log | Source for all ADT movement counts |
| Inpatient Record | Patient admission context, consultant linkage |
| Hospital Ward | Ward dimension and filtering |
| IPD Discharge Advice | Death classification (discharge_type = 'Death') |
| Healthcare Practitioner | Consultant filter |

## New Custom DocTypes

None.

## Fields Added

None.

## Workflow States

N/A — read-only report.

## Permissions

| Role | Access |
|------|--------|
| Healthcare Administrator | Read |
| Nursing User | Read |
| Physician | Read |

## Validation Logic

- Date is required
- Opening census uses last BML entry before midnight (excluding discharge entries)
- Closing = opening + admissions + transfers_in - transfers_out - discharges
- Deaths are a subset of discharges (via IPD Discharge Advice.discharge_type = 'Death')
- Same-day movements are counted in both relevant categories

## Notifications

None.

## Reporting Impact

- New report: **ADT Census**
- Added to IPD Desk and IPD Operations workspaces

## Test Cases

See `docs/testing/us-k3-tests.md`

## Assumptions

- Opening census is determined by the last BML entry before midnight of the census date
- If a patient's last BML before midnight is a Discharge, they are NOT counted in opening census
- Deaths are identified via IPD Discharge Advice with `discharge_type = 'Death'` and `docstatus != 2`
- Consultant filter uses `ordered_by_practitioner` on BML for day movements and `primary_practitioner` on IR for opening census
- The report shows a single day; multi-day ranges are not currently supported (navigate day-by-day)

## Open Questions

- Should a date range mode be added for weekly/monthly census summaries?
- Should LAMA (Leave Against Medical Advice) be tracked as a separate column alongside Deaths?
- Is there a standard "cause of discharge" field on Inpatient Record that should be used instead of IPD Discharge Advice?
