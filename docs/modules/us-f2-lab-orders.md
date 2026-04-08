# US-F2: Place Lab Test Orders Digitally

## Purpose

Enable doctors to request laboratory investigations from the inpatient workflow for prompt lab and nursing processing with SLA milestone tracking.

## Scope

- Lab order creation with test, sample type, urgency, fasting, collection instructions
- SLA milestones: Ordered → Acknowledged → Sample Collected → Received in Lab → Result Published
- Status synchronization with standard Lab Test doctype
- Critical result acknowledgment support

## Reused Doctypes

- **Lab Test Template** — linked via `lab_test_template`
- **Lab Test** — linked via `linked_lab_test` for result tracking
- **Patient Encounter** — source via `lab_test_prescription` child table

## New/Extended Doctypes

- **IPD Clinical Order** — `order_type = "Lab Test"` with lab-specific fields

## Fields (Lab-specific)

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| lab_test_template | Link (Lab Test Template) | No | Standard template link |
| lab_test_name | Data | Yes | Test name |
| sample_type | Data | No | e.g., Blood, Urine |
| is_fasting_required | Check | No | Fasting requirement flag |
| collection_instructions | Small Text | No | Special collection notes |
| linked_lab_test | Link (Lab Test) | No | Read-only, set when Lab Test created |

## SLA Milestones (Default — Lab Test STAT)

| Milestone | Target (min) | Escalation Role |
|-----------|-------------|-----------------|
| Acknowledged | 10 | Laboratory User |
| Sample Collected | 30 | Nursing User |
| Result Published | 120 | Healthcare Administrator |

## Integration: Lab Test Events

When a `Lab Test` document is submitted and linked to a Clinical Order:
- The `lab_test_events.on_submit` handler records a "Result Published" milestone
- This advances the SLA and may trigger completion

## Test Cases

- Lab order creation with validation
- PE lab_test_prescription auto-creates orders
- SLA milestones created for lab orders
- Lab Test submission records milestone on linked order
