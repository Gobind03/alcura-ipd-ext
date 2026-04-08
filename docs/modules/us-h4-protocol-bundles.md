# US-H4: Protocol-Based Monitoring Bundles

## Purpose

Allow intensivists to activate care protocol bundles (sepsis, post-op,
cardiac, stroke, DKA, ventilator) that auto-generate required tasks,
labs, observations, and track compliance consistently.

## Scope

- Define protocol bundles with typed steps (Observation, Lab, Medication, Procedure, Task, Assessment)
- Activate bundles per admission with computed due times
- Track step completion, skipping, and missed status
- Weighted compliance scoring
- Auto-start observation charts from bundle steps
- Scheduled overdue detection and notification
- Protocol Compliance Report

## Reused Custom DocTypes

| DocType | Usage |
|---------|-------|
| IPD Chart Template | Referenced by Observation steps |
| IPD Bedside Chart | Auto-started from bundle activation |

## New Custom DocTypes

### Monitoring Protocol Bundle

Master configuration for a care protocol.

| Field | Type | Notes |
|-------|------|-------|
| bundle_name | Data | Unique primary key |
| bundle_code | Data | Unique short code |
| category | Select | Sepsis/Post-Op/Cardiac/Stroke/DKA/Ventilator/Burns/Custom |
| is_active | Check | |
| duration_hours | Int | 0 = indefinite |
| compliance_target_pct | Percent | Default 100 |
| description | Text Editor | |
| activation_triggers | Small Text | Documentation field |
| steps | Table (Protocol Bundle Step) | |

### Protocol Bundle Step (child table)

| Field | Type | Notes |
|-------|------|-------|
| step_name | Data | Unique within bundle |
| step_type | Select | Observation/Lab Order/Medication Order/Procedure Order/Task/Assessment |
| sequence | Int | Unique within bundle |
| is_mandatory | Check | |
| due_within_minutes | Int | From activation time |
| recurrence_minutes | Int | 0 = one-time |
| chart_template | Link | For Observation type |
| lab_test_template | Link | For Lab Order type |
| medication_item | Link | For Medication Order type |
| procedure_template | Link | For Procedure Order type |
| instructions | Small Text | |
| compliance_weight | Float | Default 1.0 |

### Active Protocol Bundle

| Field | Type | Notes |
|-------|------|-------|
| protocol_bundle | Link | Required |
| patient | Link | Required |
| inpatient_record | Link | Required |
| status | Select | Active/Completed/Discontinued/Expired |
| compliance_score | Percent | Read-only, computed |
| activated_at/by | Datetime/User | |
| completed_at | Datetime | |
| discontinued_at/by | Datetime/User | |
| discontinuation_reason | Small Text | |
| step_trackers | Table (Protocol Step Tracker) | |

### Protocol Step Tracker (child table)

| Field | Type | Notes |
|-------|------|-------|
| step_name | Data | |
| step_type | Data | |
| sequence | Int | |
| is_mandatory | Check | |
| status | Select | Pending/Due/Completed/Missed/Skipped |
| due_at | Datetime | |
| completed_at/by | Datetime/User | |
| linked_document_type | Link (DocType) | |
| linked_document | Dynamic Link | |
| notes | Small Text | |

## Service: `protocol_bundle_service.py`

| Function | Purpose |
|----------|---------|
| activate_bundle | Create active bundle with step trackers |
| complete_step | Mark step done, update compliance |
| skip_step | Mark step skipped with reason |
| check_overdue_steps | Flag missed steps |
| compute_compliance | Weighted percentage |
| discontinue_bundle | Stop tracking |
| get_active_bundles_for_ir | List with compliance summaries |
| check_all_active_bundles | Scheduled scan |

## API Endpoints (protocol_bundle.py)

| Endpoint | Purpose |
|----------|---------|
| activate | Activate bundle for admission |
| complete_step | Complete a step |
| skip_step | Skip a step |
| discontinue | Discontinue bundle |
| get_bundles_for_ir | List bundles |
| get_compliance_report | Filtered compliance data |

## Report: Protocol Compliance Report

Script report with filters: Protocol Bundle, Status, Ward, From/To Date.
Columns: Bundle, Protocol, Category, Patient, Ward, Status, Compliance %, Steps counts.

## Scheduled Task

`check_protocol_compliance` runs every 15 minutes via scheduler:
- Scans all Active bundles
- Marks overdue steps as Missed
- Recomputes compliance scores
- Sends notifications for breaches

## Permissions

| Role | Protocol Bundle | Active Bundle |
|------|-----------------|---------------|
| Healthcare Administrator | Full | Read/Write |
| ICU Administrator | Create/Read/Write | Create/Read/Write |
| Physician | Read | Create/Read/Write |
| Nursing User | Read | Read/Write |

## Test Cases

See `tests/test_protocol_bundle_service.py`:
- Bundle validation (empty steps, duplicate names, duplicate sequences)
- Activation (creates trackers, blocks duplicates, auto-starts charts)
- Step completion (complete, block double-complete, skip, skip requires reason)
- Compliance scoring (full and partial)
- Overdue detection (steps marked missed)
- Discontinue (with reason, requires reason)
- Query (bundles for IR)

## Open Questions / Assumptions

- Recurrence steps are not yet fully implemented (one-time tracking only in v1)
- Compliance weights are relative, not absolute percentages
- Skipped non-mandatory steps count toward compliance
- Bundle auto-completion occurs when all steps reach terminal state
