# Lab Sample Lifecycle

## Overview

Tracks the physical lab sample from creation through collection, transport, lab receipt, and result publication. Supports recollection on bad sample condition and critical result acknowledgment.

## Status Flow

```
Pending → Collected → In Transit → Received → Processing → Completed
                                             ↳ Rejected (bad condition)
                                               → New sample created (Pending)
```

## Lifecycle Steps

### 1. Sample Creation

- Triggered automatically when a Lab Test order is placed (`place_order`)
- Creates IPD Lab Sample with `status = "Pending"`, `collection_status = "Pending"`
- Auto-generates a unique barcode

### 2. Collection

- Nurse/phlebotomist records collection at bedside
- Sets: `collected_by`, `collected_at`, `collection_site`
- Updates: `status = "Collected"`, `collection_status = "Collected"`
- Records SLA milestone: "Sample Collected"

### 3. Handoff/Transport

- Sample handler records handoff for transport
- Sets: `handed_off_by`, `handed_off_at`, `transport_mode`
- Updates: `status = "In Transit"`
- Records SLA milestone: "Sample Handed Off"

### 4. Lab Receipt

- Lab technician receives sample and assesses condition
- Sets: `received_by`, `received_at`, `sample_condition`
- Updates: `status = "Received"`
- Records SLA milestone: "Sample Received"
- **If condition != Acceptable**: triggers automatic recollection

### 5. Recollection Flow

When sample condition is unacceptable:
1. Original sample marked: `collection_status = "Recollection Needed"`, `status = "Rejected"`
2. New sample created with `parent_sample` linking to original
3. Nursing User notified about recollection
4. New sample starts fresh lifecycle at "Pending"

### 6. Result Publication

- When Lab Test is submitted in ERPNext:
  - Linked sample updated to `status = "Completed"`
  - Critical value detection runs
  - If critical: `is_critical_result = 1`, notification sent

### 7. Critical Result Acknowledgment

- Requires explicit acknowledgment by physician/nurse
- Sets: `critical_result_acknowledged_by`, `critical_result_acknowledged_at`
- Critical result UI shown prominently with red indicator

## SLA Milestones

1. Acknowledged
2. Sample Collected
3. Sample Handed Off
4. Sample Received in Lab
5. Result Published

## Notification Events

| Event | Recipients |
|-------|-----------|
| Sample collected | Lab User (realtime) |
| Bad sample condition | Nursing User (recollection alert) |
| Critical result | Ordering practitioner, Nursing, Physician |
