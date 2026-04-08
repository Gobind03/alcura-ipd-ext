# Clinical Order Subsystem — Architecture Overview

## Purpose

The Clinical Order subsystem provides a unified digital ordering, tracking, and SLA monitoring layer for all inpatient clinical orders. It covers medication prescriptions (US-F1), laboratory investigations (US-F2), radiology and procedure requests (US-F3), real-time departmental work queues (US-F4), and configurable SLA escalation (US-F5).

## Scope

- All orders placed during an active inpatient admission
- Covers order types: Medication, Lab Test, Radiology, Procedure
- Lifecycle from Draft → Ordered → Acknowledged → In Progress → Completed/Cancelled
- SLA tracking with configurable milestones per order type and urgency
- Real-time queues for Pharmacy, Lab, and Nurse Station departments
- Scheduler-driven SLA breach detection and escalation notifications
- Integration with existing Patient Encounter prescription workflow

## Data Model

### New Custom Doctypes

| Doctype | Type | Purpose |
|---------|------|---------|
| IPD Clinical Order | Main | Unified order record for all order types |
| IPD Order SLA Milestone | Child Table | SLA milestone tracking per order |
| IPD Order SLA Config | Main | SLA target configuration per type/urgency |
| IPD SLA Milestone Target | Child Table | Individual milestone targets within config |

### Custom Fields on Standard Doctypes

| Doctype | Field | Purpose |
|---------|-------|---------|
| Patient Encounter | `custom_has_ipd_orders` | Flag when orders auto-created from prescriptions |
| Inpatient Record | `custom_active_medication_orders` | Aggregate count of active medication orders |
| Inpatient Record | `custom_active_lab_orders` | Aggregate count of active lab orders |
| Inpatient Record | `custom_active_procedure_orders` | Aggregate count of active procedure orders |
| Inpatient Record | `custom_pending_orders_count` | Count of orders awaiting action |
| IPD MAR Entry | `clinical_order` | Link back to originating clinical order |

## Integration Points

### Patient Encounter → Clinical Orders

When a Patient Encounter linked to an Inpatient Record is submitted, the `on_submit` hook in `patient_encounter_events.py` auto-creates IPD Clinical Orders from:
- `drug_prescription` rows → Medication orders
- `lab_test_prescription` rows → Lab Test orders
- `procedure_prescription` rows → Procedure orders

### Lab Test → Clinical Order Status Sync

When a Lab Test linked to a Clinical Order is submitted, the `lab_test_events.py` handler records a "Result Published" milestone on the order.

### SLA Scheduler

A cron job runs every 5 minutes (`check_order_sla_breaches`) to detect orders past their SLA target and trigger escalation notifications.

## Service Layer

| Module | Responsibility |
|--------|---------------|
| `services/clinical_order_service.py` | CRUD, status transitions, PE integration, IR count aggregation |
| `services/order_sla_service.py` | SLA initialization, milestone advancement, breach detection |
| `services/order_notification_service.py` | Notification Log creation, realtime events, deduplication |

## API Layer

| Module | Endpoints |
|--------|-----------|
| `api/clinical_order.py` | Create/transition/cancel/hold/resume orders, record milestones |
| `api/department_queue.py` | Pharmacy/Lab/Nurse Station queue data with SLA enrichment |

## Department Queue Pages

Three custom Frappe Pages provide live work queues:
- **Pharmacy Queue** — Medication orders, one-click acknowledge/dispense
- **Lab Queue** — Lab orders with sample collection and result publishing milestones
- **Nurse Station Queue** — All order types grouped by patient/bed

All queues feature:
- SLA color-coded indicators (green/yellow/orange/red)
- Auto-refresh every 30 seconds + realtime event subscription
- Urgency-prioritized sorting
- Role-based access control

## Reports

| Report | Purpose |
|--------|---------|
| Order TAT Report | Turnaround time analysis with averages |
| SLA Breach Report | Breached orders with milestone details |

## Database Indexes

The IPD Clinical Order doctype has indexes on:
- `patient`, `inpatient_record`, `order_type`, `urgency`, `status`
- `target_department`, `ward`, `bed`, `ordering_practitioner`
- `ordered_at`, `current_sla_target_at`, `is_sla_breached`
