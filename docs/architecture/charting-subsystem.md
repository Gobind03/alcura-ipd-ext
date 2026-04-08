# Charting Subsystem Architecture

## Overview

The bedside charting subsystem provides continuous clinical documentation for inpatients. It covers vitals, intake-output, medication administration, nursing notes, glucose monitoring, pain assessment, ventilator parameters, and derived fluid balance.

## Three-Layer Architecture

### 1. Template Layer

**IPD Chart Template** + **IPD Chart Template Parameter** define what to chart — parameters, frequencies, validation ranges, and critical thresholds. Templates are hospital-configurable; adding a new chart type (e.g., neuro checks) requires only a new template, not code changes.

### 2. Schedule Layer

**IPD Bedside Chart** links a template to an active admission (Inpatient Record). It tracks:
- Frequency (overridable from template default)
- Lifecycle status (Active / Paused / Discontinued)
- Last entry timestamp (for overdue calculation)
- Ward and bed (denormalized for efficient queries)

### 3. Entry Layer

Entries are grouped by structural similarity:

| Model | Chart Types | Why Separate |
|-------|-------------|-------------|
| IPD Chart Entry + IPD Chart Observation | Vitals, Glucose, Pain, Ventilator | All follow "record N parameters at a point in time" |
| IPD IO Entry | Intake-Output | Volume-per-line-item; structurally different |
| IPD MAR Entry | Medication Administration | Task-execution against medication orders |
| IPD Nursing Note | Nursing Notes | Narrative free-text with categorization |

## Correction/Addendum Model

Clinical records are never deleted or silently overwritten:
- Original entry stays, marked `status = "Corrected"` (or "Amended" for notes)
- A new entry is created with `is_correction = True` and `corrects_entry` linking to the original
- Both entries retain their original timestamps and user attribution

## Overdue Detection

Overdue status is computed dynamically: `now() > last_entry_at + frequency_minutes`. A scheduled task (every 15 min) sends notifications for charts overdue beyond the grace period. The Nurse Station dashboard computes overdue in real-time.

## Fluid Balance

Fluid Balance is computed from I/O entries (sum intake - sum output) over time windows. It is not a stored doctype — computed via API and report.

## Data Flow

```
IPD Chart Template (master definition)
    ↓
IPD Bedside Chart (per-admission schedule)
    ↓
IPD Chart Entry (each recording session)
    ↓
IPD Chart Observation (individual parameter values)
```

For I/O, MAR, and Nursing Notes, entries link directly to Inpatient Record without an intermediate schedule, since these are event-driven rather than frequency-based.

## Indexes

All entry doctypes index: `patient`, `inpatient_record`, `ward`, `entry_datetime`, `status`.
IPD Bedside Chart additionally indexes: `chart_type`, `status`.

## Standard DocType Integration

- **Inpatient Record**: Custom fields for charting section (active/overdue counts, last vitals timestamp)
- **Standard Vital Signs**: NOT reused for continuous monitoring (OPD-oriented, no frequency/correction model). Optional sync is a future enhancement.
- **Patient Encounter drug_prescription**: MAR entries reference medication names but do not formally link to prescription lines (deferred to future story).

## Module Boundary

All charting doctypes belong to module `Alcura IPD Extensions`. They depend on:
- `Patient` (standard)
- `Inpatient Record` (standard)
- `Hospital Ward`, `Hospital Bed` (custom, from US-A stories)
- `User` (standard)
