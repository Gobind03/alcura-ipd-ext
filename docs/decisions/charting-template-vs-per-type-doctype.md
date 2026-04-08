# ADR: Template-Driven Parameter Charts vs. Per-Type DocTypes

## Status

Accepted

## Context

US-E4 requires charting for vitals, intake-output, medication administration, nursing notes, glucose, pain, ventilator parameters, and fluid balance. The question is whether to create one doctype per chart type, use a fully generic EAV model, or find a middle ground.

## Options Considered

### Option A: One DocType per chart type

Create `IPD Vital Entry`, `IPD Glucose Entry`, `IPD Pain Entry`, `IPD Ventilator Entry`, etc. each with specific fields.

- Pros: Strong typing, specific validations, simple queries
- Cons: DocType proliferation; adding neuro checks or wound assessment requires code changes; high maintenance cost

### Option B: Fully generic EAV model

One `IPD Chart Entry` with a child `IPD Chart Observation` holding parameter name + value.

- Pros: Maximum flexibility; new chart types via templates only
- Cons: Loses type safety for structurally different charts (I/O, MAR, notes); awkward UX for line-item or narrative data; complex reporting

### Option C: Hybrid (selected)

Use template-driven parameter recording for charts that share the "record N parameters at a point in time" pattern (Vitals, Glucose, Pain, Ventilator). Use dedicated doctypes for structurally distinct charts (I/O, MAR, Nursing Notes).

- Pros: New parameter charts need only a template; structurally distinct charts get proper fields and validation; balanced maintainability
- Cons: Three entry-layer doctypes plus the parameter model; slightly more initial work

## Decision

**Option C — Hybrid approach.**

Charts sharing the parameter-recording pattern use `IPD Chart Entry` + `IPD Chart Observation`. I/O, MAR, and Nursing Notes get dedicated doctypes because their data structures are fundamentally different (volume-per-line-item, task-execution, narrative).

## Consequences

- Adding Vitals, Glucose, Pain, or Ventilator variants requires only a new IPD Chart Template
- I/O, MAR, and Nursing Notes have purpose-built validation and UX
- Reports for parameter charts use a unified query model; other charts have their own reports
- The total number of new doctypes is 8 (manageable)
