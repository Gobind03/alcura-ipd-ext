# US-F4: Maintain a Live Work Queue per Department

## Purpose

Provide pharmacists, lab technicians, and nurses with real-time task queues of pending inpatient orders for sequential action within TAT.

## Scope

- Three custom Frappe Pages: Pharmacy Queue, Lab Queue, Nurse Station Queue
- Server-driven filtered data via `api/department_queue.py`
- SLA color-coded indicators
- One-click actions for acknowledge, dispense, sample collected, etc.
- Auto-refresh every 30 seconds + realtime event subscription

## Queue Pages

### Pharmacy Queue (`/app/pharmacy-queue`)
- **Filters:** Ward, Urgency, Status
- **Shows:** Medication orders in actionable states
- **Actions:** Acknowledge, Mark Dispensed
- **Roles:** Pharmacy User, Healthcare Administrator

### Lab Queue (`/app/lab-queue`)
- **Filters:** Ward, Urgency, Status
- **Shows:** Lab Test orders
- **Actions:** Acknowledge, Sample Collected, Result Published
- **Roles:** Laboratory User, Healthcare Administrator

### Nurse Station Queue (`/app/nurse-station-queue`)
- **Filters:** Ward, Status
- **Shows:** ALL order types grouped by patient/bed
- **Actions:** Acknowledge, Open linked order/chart
- **Roles:** Nursing User, Healthcare Administrator

## SLA Color Bands

| Color | Condition |
|-------|-----------|
| Green | > 50% of SLA window remaining |
| Yellow | 20–50% remaining |
| Orange | < 20% remaining |
| Red | Overdue or breached |
| Grey | No SLA target configured |

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `get_pharmacy_queue` | GET | Medication orders with filters |
| `get_lab_queue` | GET | Lab orders with filters |
| `get_nurse_station_queue` | GET | All orders by ward |

All endpoints return enriched data with `elapsed_minutes`, `sla_remaining_minutes`, and `sla_color`.

## Test Cases

- Queue returns correct order types
- SLA enrichment adds color bands
- Empty queue returns empty list
- Ward filter works correctly
