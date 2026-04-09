# Alcura IPD Extensions — User Manual

**Version:** 1.0  
**Application:** Alcura IPD Extensions for ERPNext Healthcare v16  
**Audience:** Doctors (Physicians), Nurses, Admission Officers, Pharmacy Staff, Lab Technicians, TPA/Billing Desk, Housekeeping Staff, and Healthcare Administrators

---

## Table of Contents

1. [Introduction](#1-introduction)
2. [System Roles and Access](#2-system-roles-and-access)
3. [Setup and Configuration (Admin)](#3-setup-and-configuration)
4. [Module A — Ward, Room & Bed Setup](#4-module-a--ward-room--bed-setup)
5. [Module B — Bed Management](#5-module-b--bed-management)
6. [Module C — Patient Registration & Payer Profiles](#6-module-c--patient-registration--payer-profiles)
7. [Module D — Admission Workflow](#7-module-d--admission-workflow)
8. [Module E — Clinical Documentation](#8-module-e--clinical-documentation)
9. [Module F — Clinical Orders](#9-module-f--clinical-orders)
10. [Module G — Pharmacy & Medication Administration](#10-module-g--pharmacy--medication-administration)
11. [Module H — ICU & Device Monitoring](#11-module-h--icu--device-monitoring)
12. [Module I — TPA, Billing & Claims](#12-module-i--tpa-billing--claims)
13. [Module J — Discharge Journey](#13-module-j--discharge-journey)
14. [Module K & L — Dashboards & Reports](#14-modules-k--l--dashboards--reports)
15. [Print Formats & Labels](#15-print-formats--labels)
16. [Automated System Jobs](#16-automated-system-jobs)
17. [Quick Reference by Role](#17-quick-reference-by-role)

---

## 1. Introduction

Alcura IPD Extensions is a comprehensive Inpatient Department (IPD) management system built on top of ERPNext Healthcare. It extends the standard healthcare module with:

- Physical ward/room/bed modeling with real-time occupancy tracking
- End-to-end admission, transfer, and discharge (ADT) workflows
- Nursing intake assessments and risk scoring
- Bedside charting (vitals, I/O, pain, glucose, ventilator)
- Unified clinical orders (medication, lab, radiology, procedure) with SLA tracking
- Pharmacy dispensing and Medication Administration Record (MAR)
- Lab sample lifecycle tracking with critical result alerts
- ICU monitoring profiles, device observation feeds, and protocol bundles
- Payer/insurance eligibility, TPA pre-authorization, and claim packs
- Discharge billing checklists and nursing discharge checklists
- Housekeeping task management with SLA monitoring
- Operational dashboards and compliance reports

The system is designed for Indian hospital workflows and supports Aadhaar, PAN, and ABHA ID validation on patient records.

---

## 2. System Roles and Access

The application uses the following roles. Each user may have one or more roles assigned.

| Role | Description | Typical Users |
|------|-------------|---------------|
| **Physician** | Doctors — order entry, progress notes, discharge advice | Consultants, Residents |
| **Nursing User** | Nurses — charting, MAR, intake assessments, checklists | Staff Nurses, Charge Nurses |
| **Healthcare Administrator** | Full administrative access to all IPD modules | Hospital Admin, IT Admin |
| **IPD Admission Officer** | Admission desk — bed allocation, checklists, patient registration | Front Desk, Admission Staff |
| **Pharmacy User** | Medication dispensing, stock verification, substitutions | Pharmacists |
| **Laboratory User** | Lab sample receipt, processing, result publication | Lab Technicians |
| **TPA Desk User** | Insurance eligibility, pre-authorization, claim packs | TPA Coordinators |
| **IPD Billing User** | Billing checklists, interim bills, tariff management | Billing Clerks |
| **ICU Administrator** | ICU monitoring profiles, protocol bundles, device mappings | ICU In-charge |
| **Device Integration User** | Device observation feed management | Biomedical Engineering |

### Access Summary

| Area | Physician | Nursing User | Admission Officer | Pharmacy | Lab | TPA Desk | Billing |
|------|-----------|-------------|-------------------|----------|-----|----------|---------|
| Patient Records | Read/Write | Read | Read/Write | Read | Read | Read | Read |
| Inpatient Record | Read | Read | Read | Read | Read | Read | Read |
| Clinical Orders | Create/Edit | Read | — | Read/Edit | Read/Edit | — | — |
| Charting | Read | Create/Edit | — | — | — | — | — |
| MAR | Read | Create/Edit | — | — | — | — | — |
| Pharmacy Dispense | Read | Read | — | Create/Edit | — | — | — |
| Lab Samples | Read | Create/Edit | — | — | Create/Edit | — | — |
| Bed Management | Read | Read/Write | Read/Write | — | — | — | — |
| Payer Profiles | Read | Read | Read/Write | — | — | Read/Write | Read |
| TPA Preauth | Read | — | — | — | — | Create/Edit | — |
| Discharge Advice | Create/Edit | Read | — | — | — | — | — |
| Billing Checklist | Read | — | — | — | — | — | Read/Edit |

---

## 3. Setup and Configuration

> **Audience:** Healthcare Administrator

### 3.1 Installation

The application is installed via the Frappe bench:

```
bench install-app alcura_ipd_ext
bench migrate
```

On installation, the system automatically:
- Creates all custom roles (IPD Admission Officer, TPA Desk User, etc.)
- Adds custom fields to standard doctypes (Patient, Patient Encounter, Inpatient Record, etc.)
- Seeds default intake assessment templates (General Medical, Surgical, Pediatric, Obstetric, ICU)
- Seeds default charting templates (General Ward Vitals, ICU Vitals, Glucose, Pain, Ventilator)
- Seeds ICU monitoring profiles

### 3.2 Initial Configuration Checklist

After installation, an administrator must configure:

1. **Hospital Wards** — Create ward records for each physical ward (General, ICU, HDU, etc.)
2. **Room Types** — Configure Healthcare Service Unit Types with IPD Room Category (General, Semi-Private, Private, Deluxe, Suite, ICU, HDU, etc.)
3. **Rooms & Beds** — Create Hospital Room and Hospital Bed records within each ward
4. **Room Tariff Mappings** — Set up tariff rates per room type, payer type, and date range
5. **IPD Bed Policy** — Configure reservation TTL, enforcement levels, buffer beds
6. **Admission Checklist Templates** — Define mandatory and optional admission tasks
7. **IPD Order SLA Config** — Set SLA targets for each order type and urgency level
8. **Payer Billing Rule Sets** — Define billing split rules per payer
9. **Monitoring Protocol Bundles** — Configure care protocols for ICU (Sepsis, Ventilator, DKA, etc.)

### 3.3 IPD Bed Policy

The IPD Bed Policy controls system-wide bed management rules:

| Setting | Options | Description |
|---------|---------|-------------|
| Reservation TTL | Minutes | How long a bed reservation stays active before auto-expiry |
| Enforcement Level | Strict / Advisory / Ignore | Controls whether eligibility checks gate admission |
| Buffer Beds | Number | Beds kept in reserve per ward for emergencies |
| Auto-mark Dirty on Discharge | Yes/No | Automatically creates housekeeping task on bed vacate |

---

## 4. Module A — Ward, Room & Bed Setup

> **Audience:** Healthcare Administrator

### 4.1 Hospital Ward

A ward represents a physical/operational unit in the hospital.

**To create a ward:**
1. Navigate to **Hospital Ward** list → **+ Add Hospital Ward**
2. Fill in: Ward Name, Ward Code (alphanumeric, unique per company), Ward Classification
3. Select the Company and optionally link to a Healthcare Service Unit group node
4. Save

**Ward Classifications:** General, Semi-Private, Private, Deluxe, Suite, ICU, CICU, MICU, NICU, PICU, SICU, HDU, Burns, Isolation

**Auto-flags:**
- Selecting any ICU variant, HDU, or Burns automatically sets `Is Critical Care = Yes`
- The system suggests isolation support based on classification

**Constraints:**
- Ward code must be alphanumeric with optional hyphens (no spaces or special characters)
- Ward code must be unique within the company
- If linked to a Healthcare Service Unit, it must be a group node

### 4.2 Room Types (Healthcare Service Unit Type)

Room types are configured on the standard Healthcare Service Unit Type with IPD-specific extensions.

**IPD fields added:**
- **IPD Room Category** — Required when inpatient occupancy is enabled
- **Occupancy Class** — Classification for reporting
- **Critical Care Flag** — Auto-set for ICU types
- **Nursing Intensity** — Suggested staffing ratio

### 4.3 Hospital Room

Rooms sit within wards and have a defined bed capacity.

**To create a room:**
1. Navigate to **Hospital Room** → **+ Add Hospital Room**
2. Select the Ward, Room Type, and set bed capacity
3. Save

### 4.4 Hospital Bed

Beds are the atomic unit of occupancy tracking.

**Bed statuses:**
- **Vacant** — Available for allocation
- **Reserved** — Held by a reservation
- **Occupied** — Patient admitted
- **Dirty** — Post-discharge, awaiting cleaning
- **Under Maintenance** — Temporarily unavailable

**Housekeeping status:** Clean / Dirty / In Progress

Bed status changes are automatically synchronized with the Healthcare Service Unit occupancy.

### 4.5 Room Tariff Mapping

Tariffs define per-room-type charges differentiated by payer.

**To create a tariff mapping:**
1. Navigate to **Room Tariff Mapping** → **+ Add**
2. Select Room Type, Company, Payer Type (Cash/Corporate/TPA)
3. For Corporate/TPA, select the specific Payer (Customer)
4. Set Valid From and optionally Valid To dates
5. Select the Price List
6. Add tariff items (Room Rent, Nursing Charge, ICU Monitoring, etc.) with rates and billing frequencies
7. Save

**Constraints:**
- At least one tariff item is required
- No duplicate charge types within the same mapping
- Date ranges must not overlap for the same room type + payer combination
- The system uses row-level locking to prevent race conditions in overlap detection

**Tariff Resolution Priority:**
1. Exact payer match (room type + payer type + specific payer)
2. Generic payer type match (room type + payer type, no specific payer)
3. Cash fallback

---

## 5. Module B — Bed Management

> **Audience:** Nursing User, IPD Admission Officer, Healthcare Administrator

### 5.1 Live Bed Board

The **Bed Board** provides a real-time visual overview of bed occupancy across the hospital.

**To access:** Navigate to the **IPD Operations** workspace → **Live Bed Board**

The board displays:
- Beds color-coded by status (Vacant, Reserved, Occupied, Dirty, Maintenance)
- Patient name, admission date, and consultant for occupied beds
- Ward and room grouping
- Filterable by ward, room type, and status

**Summary view** shows aggregate counts per ward: total beds, occupied, vacant, reserved, dirty.

### 5.2 Bed Reservation

Reservations allow holding a bed (or a room type) for an upcoming admission.

**To create a reservation:**
1. From the Inpatient Record or Bed Board, click **Reserve Bed**
2. Choose reservation type:
   - **Specific Bed** — Locks a particular bed
   - **Room Type Hold** — Reserves capacity of a room type without locking a specific bed
3. Set the reservation end time
4. Click **Activate Reservation**

**Reservation Lifecycle:**

```
Draft → Active → Expired (auto, by scheduler)
                → Cancelled (manual)
                → Consumed (when patient is admitted)
```

**Constraints:**
- Only Vacant beds can be reserved (for Specific Bed type)
- The system uses database row-level locking to prevent two users from reserving the same bed simultaneously
- Active reservations automatically expire based on the configured TTL (checked every 5 minutes)
- Only Healthcare Administrators can override-cancel an active reservation held by another user
- Room Type Hold reservations account for configured buffer beds

**Who can do what:**

| Action | Roles |
|--------|-------|
| Activate Reservation | Nursing User, Healthcare Administrator |
| Cancel Reservation | Nursing User, Healthcare Administrator |
| Override Cancel (another user's) | Healthcare Administrator only |

### 5.3 Bed Allocation

Bed allocation assigns a patient to a specific bed during admission.

**To allocate a bed:**
1. Open the Inpatient Record (status: Admission Scheduled)
2. Click **Allocate Bed**
3. The system shows available beds filtered by requested ward/room type
4. If a reservation exists, it is automatically consumed
5. Select the bed and confirm

**Pre-allocation checks:**
- If an admission checklist exists and is Incomplete, a confirmation prompt is shown (you may proceed, but the system warns you)
- If the IPD Bed Policy enforcement level is "Strict" and the patient is non-Cash without a Verified/Conditional eligibility check, allocation is blocked
- If enforcement is "Advisory", a warning is shown but allocation proceeds

### 5.4 Bed Transfer

Transfers move a patient from one bed to another within the hospital.

**To transfer a patient:**
1. Open the Inpatient Record (status: Admitted)
2. Click **Transfer Bed**
3. Select the destination bed
4. Provide a transfer reason
5. Confirm the transfer

**What happens on transfer:**
- A **Bed Movement Log** is created recording the from/to beds, reason, and timestamp
- The original bed is marked Vacant (or Dirty if auto-mark is enabled)
- The new bed is marked Occupied
- Ward/room capacity rollups are updated
- If a housekeeping task is configured, one is created for the vacated bed

---

## 6. Module C — Patient Registration & Payer Profiles

> **Audience:** IPD Admission Officer, Healthcare Receptionist, TPA Desk User

### 6.1 Patient Registration (Enhanced)

The standard Patient doctype is enhanced with Indian-specific fields:

| Field | Validation |
|-------|-----------|
| **Aadhaar Number** | Must be exactly 12 digits |
| **PAN Number** | Must match format: 5 letters + 4 digits + 1 letter (e.g., ABCDE1234F) |
| **ABHA Number** | Must be exactly 14 digits |
| **Mobile Number** | Must be 10 digits starting with 6, 7, 8, or 9 |

**Additional fields:** Emergency contact details, consent timestamp, default payer profile link.

**Duplicate Detection:** The system provides a `check_patient_duplicates` API that can be called to check for potential duplicate patient records before registration.

### 6.2 Patient Payer Profile

A Payer Profile captures the patient's payment/insurance information. Multiple profiles can exist per patient (e.g., one Insurance TPA and one Corporate backup).

**Payer Types:**
1. **Cash** — Self-paying patient; no payer details needed
2. **Corporate** — Employer-sponsored coverage; requires a Customer (payer) link
3. **Insurance TPA** — Third-party administrator insurance; requires Insurance Payor link
4. **PSU** — Public Sector Undertaking coverage; requires a Customer (payer) link
5. **Government Scheme** — Government health scheme (Ayushman Bharat, CGHS, etc.)

**To create a profile:**
1. Navigate to **Patient Payer Profile** → **+ Add**
2. Select the Patient and Payer Type
3. Fill in payer-specific details (policy number, member ID, validity dates)
4. Set coverage details: sum insured, balance available, sub-limits, room category entitlement
5. Configure billing rules: pre-auth required, co-pay %, deductible amount
6. Save

**Constraints:**
- Valid From must be before Valid To (when set)
- Insurance TPA type requires an Insurance Payor
- Corporate/PSU type requires a Customer (payer)
- The system warns on expired active profiles and duplicate active profiles

**Expiry Notifications:** A daily scheduler job checks for profiles expiring within the next 7 days and sends in-app alerts to TPA Desk Users and Healthcare Administrators.

### 6.3 Payer Eligibility Check

Before admission, insurance/TPA coverage should be verified.

**To run an eligibility check:**
1. From the Inpatient Record (Admission Scheduled), click **Check Eligibility**
2. Or navigate to **Payer Eligibility Check** → **+ Add**
3. Select the Patient, Payer Profile, and optionally the Inpatient Record
4. The check is created with status **Pending**

**Verification statuses:**

| Status | Meaning | Color |
|--------|---------|-------|
| **Pending** | Awaiting verification from TPA/payer | Orange |
| **Verified** | Coverage confirmed — admission can proceed | Green |
| **Conditional** | Approved with conditions (co-pay, sub-limits, exclusions) | Blue |
| **Rejected** | Coverage denied | Red |
| **Expired** | Previously valid verification has lapsed | Grey |

**Status transitions (TPA Desk User or Healthcare Administrator):**
- Pending → Verified, Conditional, or Rejected
- Conditional → Verified (conditions met) or Rejected
- Verified/Conditional → Expired (validity lapsed)
- Rejected/Expired → Pending (re-verification)

**Enforcement levels** (configured in IPD Bed Policy):
- **Strict:** Admission blocked for non-Cash patients without a Verified/Conditional check
- **Advisory:** Warning shown but admission allowed
- **Ignore:** No check performed

**Side effects of status changes:**
- Audit trail (user + timestamp) recorded on every transition
- Timeline comments added to the Patient and Inpatient Record
- Rejection triggers in-app notification to Healthcare Receptionist and TPA Desk User

---

## 7. Module D — Admission Workflow

> **Audience:** Physician, IPD Admission Officer, Nursing User

### 7.1 Admission Order

The admission process starts when a doctor places an admission order during a Patient Encounter.

**To order an admission:**
1. Open a **Patient Encounter**
2. In the IPD Admission section, set:
   - Admission Priority: Routine / Urgent / Emergency
   - Requested Ward
   - Expected Length of Stay (days)
   - Admission Reason
3. Submit the encounter

**What happens on submit:**
- An **Inpatient Record** is created with status "Admission Scheduled"
- The requesting encounter, priority, ward, and LOS are recorded on the IR
- A banner on the IR shows the admission order details with priority color coding (Emergency = red, Urgent = orange, Routine = blue)

### 7.2 Admission Checklist

The admission checklist ensures all mandatory pre-admission tasks are completed.

**To create a checklist:**
1. From the Inpatient Record, click **Create Admission Checklist**
2. Select a checklist template
3. The checklist is created with items from the template, status = "Incomplete"

**Checklist item actions:**

| Action | Who | Description |
|--------|-----|-------------|
| Complete Item | Admission Officer, Nursing User, Healthcare Administrator | Marks a specific task as done |
| Waive Item | Healthcare Administrator only | Waives a mandatory item (requires `can_override = 1` on template) |

**Checklist lifecycle:**

```
Incomplete → Complete (all mandatory items done, no waivers)
           → Overridden (all mandatory items resolved, at least one waived)
```

**Constraints:**
- Once Complete or Overridden, the checklist cannot be further modified
- Waiver actions create audit comments on the checklist document
- The checklist status is synced to the Inpatient Record (`custom_checklist_status`)
- If checklist is Incomplete when bed allocation is attempted, a confirmation prompt is shown

### 7.3 Admission Kit Labels

Once a patient is admitted, labels and identifiers can be printed.

**Available print formats:**
- **IPD Wristband Label** — Patient identification wristband with QR code and allergy markers
- **IPD Bed Tag** — Bed identification card
- **IPD File Cover** — Patient file cover sheet

**To print:**
1. From the Inpatient Record (Admitted status), click **Print Labels**
2. Select the desired label format
3. Print from the browser

Labels include QR code/barcode generation and allergy alert indicators (auto-populated from intake assessment data).

---

## 8. Module E — Clinical Documentation

> **Audience:** Physician, Nursing User

### 8.1 Intake Assessment

Intake assessments capture structured clinical information when a patient is admitted.

**Types of assessments:**
- **Structured Form Assessment** — Template-driven forms with sections and fields (e.g., General Medical Intake, Surgical Intake)
- **Scored Assessment** — Standardized scoring tools (e.g., Glasgow Coma Scale, Braden Scale, Morse Fall Scale)

**To create an intake assessment:**
1. From the Inpatient Record, click **Start Intake Assessment**
2. Select the appropriate template (auto-suggested based on ward specialty)
3. Fill in the structured fields
4. Complete any linked scored assessments
5. Click **Complete Assessment**

**Assessment lifecycle:**

```
Draft → In Progress (on first save with data) → Completed (explicit action)
```

**Constraints:**
- Completion requires all mandatory fields to be filled
- Only one assessment per IR per template (no duplicates)
- Completed assessments are immutable
- Template version is snapshotted at creation time

**What happens on completion:**
- Allergy data is extracted and synced to the Inpatient Record (`custom_allergy_alert`, `custom_allergy_summary`)
- If scored assessments are submitted, nursing risk flags are recalculated:
  - **Fall Risk** (from Morse Fall Scale)
  - **Pressure Injury Risk** (from Braden Scale)
  - **Nutritional Risk** (from MUST/MNA)
- High-risk indicators generate ToDo alerts for nursing staff
- Risk banners appear on the Inpatient Record form

### 8.2 Nursing Admission Assessment

The nursing assessment extends intake with detailed sections:

- **History & Chief Complaints** — Presenting complaints, history of present illness
- **Vital Signs** — Initial vitals capture
- **Pain Assessment** — Location, intensity, character
- **Allergies** — Known allergies and details
- **Mobility & Fall Risk** — Current mobility, assistive devices, fall history
- **Skin Assessment** — Skin integrity, wounds, pressure areas
- **Diet & Nutrition** — Current diet, dietary restrictions, swallowing difficulty, feeding assistance
- **Elimination** — Bowel pattern, bladder function, catheters
- **Device Lines & Access** — IV access, central lines, arterial lines, nasogastric tubes, drains

### 8.3 Consultant Admission Notes

Doctors create structured admission notes via Patient Encounters linked to the Inpatient Record.

**To create an admission note:**
1. From the Inpatient Record, click **Add Admission Note** or **Add Progress Note**
2. The system opens a Patient Encounter pre-linked to the IR
3. Fill in clinical findings, assessment, and plan
4. Add any clinical orders (medications, labs, etc.) in the prescription tables
5. Submit the encounter

**On encounter submit:**
- IPD Clinical Orders are automatically created from the prescription tables
- The encounter is linked to the Inpatient Record timeline

### 8.4 Bedside Charts

Bedside charts provide structured recording of patient observations over time.

**Chart types (pre-configured templates):**
- **General Ward Vitals** — Temperature, heart rate, blood pressure, respiratory rate, SpO2
- **ICU Vitals** — Extended vitals with additional hemodynamic parameters
- **Glucose Monitoring** — Blood glucose with insulin dose tracking
- **Pain Assessment** — Pain scale scores with location and intervention
- **Ventilator Monitoring** — Ventilator settings and patient response parameters

**To start a chart:**
1. From the Inpatient Record (Admitted), click **Start Chart**
2. Select the chart template
3. Set the recording frequency (in minutes)
4. The chart becomes active for the patient

**To record an observation:**
1. Open the active chart or click **Record Entry** from the IR
2. Enter parameter values for the current observation
3. Save the entry

**Features:**
- **Critical Value Detection** — Values outside the template's critical thresholds are auto-flagged; real-time alerts and in-app notifications are sent to the nursing station and attending physician
- **Overdue Detection** — The system checks every 15 minutes for charts past their scheduled recording time; missed observations increment a `missed_count` and trigger alerts
- **Correction Model** — Original entries cannot be edited; instead, a correction entry is created that links to the original, with a mandatory correction reason
- **Trend Visualization** — Observation trends can be viewed as time-series charts (single parameter or multi-parameter)
- **Fluid Balance** — For I/O charts, the system computes daily, hourly, and shift-wise fluid balance (Intake minus Output)

**Chart statuses:**
- **Active** — Accepting new observations
- **Paused** — Temporarily suspended (e.g., patient in surgery)
- **Discontinued** — Permanently stopped

**Constraints:**
- Entries cannot be recorded on Paused or Discontinued charts
- Entry datetime cannot be in the future (5-minute tolerance)
- Double corrections (correcting a correction) are blocked
- Each observation parameter has min/max validation ranges from the template

### 8.5 Intake/Output (I/O) Recording

**Fluid categories:**
- **Intake:** IV Fluid, Oral, Blood Products, TPN
- **Output:** Urine, Drain, Vomit, Stool, Blood Loss, NG Aspirate, Other

**Routes:** IV, Oral, NG Tube, Catheter, Drain, Stoma, Other

**Fluid balance computation:**
- **Daily balance** = Sum(Intake) - Sum(Output) for the calendar day
- **Shift-wise:** Morning (06:00–14:00), Afternoon (14:00–22:00), Night (22:00–06:00)
- **Hourly:** Grouped by hour for detailed monitoring

### 8.6 Nursing Notes

Free-text nursing documentation with structure.

**To create a nursing note:**
1. From the Inpatient Record, click **Add Nursing Note**
2. Select category: Assessment, Intervention, Response, Handoff, Escalation, General, Other
3. Select urgency: Routine, Urgent, Critical
4. Enter the note text
5. Save

**Critical urgency** notes trigger a real-time `critical_nursing_note` event visible to all users viewing the patient's record.

**Addendum model:** Original notes cannot be edited after save. Instead, create an addendum (linked to original) with a mandatory reason.

### 8.7 Problem List

Doctors maintain an active problem list per admission for use during rounds.

**To add a problem:**
1. From the Inpatient Record, click **Add Problem**
2. Enter the problem description, severity (Mild/Moderate/Severe), onset date
3. Optionally add an ICD-10 code
4. Save — the problem is auto-assigned to the current practitioner with a timestamp

**To resolve a problem:**
1. Click **Resolve** on an active problem
2. Enter resolution notes
3. The system records the resolving practitioner and timestamp

**Problem ordering:** Problems can be prioritized by sequence number (lower = higher priority).

**Active problem count** is maintained on the Inpatient Record and displayed in banners.

### 8.8 Doctor Progress Notes and Round Notes

**Progress Notes** are created as Patient Encounters linked to the Inpatient Record. Each encounter can include:
- Clinical findings and assessment
- Updated plan
- New clinical orders
- Active problem snapshot

**Round Notes** provide a summarized view for ward rounds:
- `get_census` — Patient census for a ward/practitioner
- `get_round_summary` — Clinical summary per patient (vitals, active problems, pending orders, latest notes)
- `create_round_note` — Quick progress note from the round sheet

---

## 9. Module F — Clinical Orders

> **Audience:** Physician, Nursing User, Pharmacy User, Laboratory User

### 9.1 Unified Clinical Order System

All inpatient orders are managed through a single **IPD Clinical Order** doctype with four order types:

| Order Type | Target Department | Created By |
|------------|-------------------|------------|
| **Medication** | Pharmacy | Physician |
| **Lab Test** | Laboratory | Physician |
| **Radiology** | Radiology | Physician |
| **Procedure** | Relevant department | Physician |

**Urgency levels:** Routine, Urgent, STAT, Emergency

### 9.2 Creating Orders

**Method 1 — From Patient Encounter:**
1. In a Patient Encounter linked to the IR, add items to the Drug Prescription, Lab Test Prescription, or Procedure Prescription tables
2. On submit, IPD Clinical Orders are automatically created for each prescription item

**Method 2 — Direct API:**
- `create_medication_order` / `create_lab_order` / `create_procedure_order`

### 9.3 Order Lifecycle

```
Draft → Ordered → Acknowledged → In Progress → Completed
  │        │           │              │
  │        │           │              ├→ Cancelled (with reason)
  │        │           │              └→ On Hold (with reason)
  │        │           ├→ Completed
  │        │           ├→ Cancelled
  │        │           └→ On Hold
  │        ├→ In Progress (skip acknowledge)
  │        ├→ Cancelled
  │        └→ On Hold
  └→ Cancelled

On Hold → Ordered / Acknowledged / In Progress / Cancelled (resume)
```

**Terminal states:** Completed, Cancelled — no further transitions.

**Audit trail:** Each transition records the timestamp and user (`ordered_at/by`, `acknowledged_at/by`, `completed_at/by`, `cancelled_at/by`).

**Constraints:**
- Cancellation always requires a reason
- Hold requires a hold_reason
- Only valid transitions are allowed (enforced server-side)
- The Inpatient Record must be in Admitted or Admission Scheduled status

### 9.4 SLA Tracking

Each order type + urgency combination has configurable SLA milestones (e.g., "Medication STAT must be Acknowledged within 5 minutes, Dispensed within 15 minutes").

**How SLA works:**
1. When an order moves to "Ordered", SLA milestones are initialized from the matching SLA Config
2. The `current_sla_target_at` field tracks the next milestone deadline
3. A scheduler job (every 5 minutes) checks for breaches
4. On breach: `is_sla_breached` flag is set, `sla_breach_count` incremented, and escalation notifications sent to the configured role

**Default SLA configurations** are seeded on install for all order type / urgency combinations.

### 9.5 Department Queues

Ancillary departments have queue views to manage incoming orders:

- **Pharmacy Queue** — Pending medication orders for dispensing
- **Lab Queue** — Pending lab orders for sample collection
- **Nurse Station Queue** — Orders relevant to the nursing station

Each queue shows order urgency, SLA status, patient location (ward/bed), and time since order.

---

## 10. Module G — Pharmacy & Medication Administration

> **Audience:** Pharmacy User, Nursing User, Physician

### 10.1 Pharmacy Dispensing

**Workflow:**

```
Order Placed → Acknowledged → Stock Verified → Dispensed → Completed
                                              ↘ Substitution Requested
                                                → Approved → Dispensed
                                                → Rejected → Original item
```

**To dispense a medication:**
1. Open the **Pharmacy Queue** or the Clinical Order
2. Verify stock availability (`verify_stock`)
3. Click **Dispense** — enter quantity, batch number, warehouse
4. For partial dispenses, a new dispense entry is created; the order shows "Partially Dispensed"
5. When total dispensed quantity matches ordered quantity, the order becomes "Fully Dispensed"

**Substitution flow:**
1. If the prescribed medication is unavailable, the pharmacist clicks **Substitute**
2. The order is put **On Hold**; `substitution_status` = "Requested"
3. The ordering doctor receives a notification
4. Doctor **approves** or **rejects** the substitution
5. On approval: the pharmacist can dispense the substitute item
6. On rejection: the original medication must be sourced

**Dispense Return:**
- A dispensed entry can be returned (e.g., patient discharged before administration)
- Sets the dispense entry status to "Returned"
- Recalculates order dispense totals

**Audit fields:** `dispensed_by`, `dispensed_at`, `verified_by`, `verified_at`, `substitution_approved_by`, `substitution_approved_at`

### 10.2 Medication Administration Record (MAR)

The MAR tracks whether scheduled medications were actually given to patients.

**Entry generation:**
When a medication order is placed (non-PRN), the system auto-generates MAR entries based on the frequency:

| Frequency | Scheduled Times |
|-----------|----------------|
| OD (Once Daily) | 08:00 |
| BD (Twice Daily) | 08:00, 20:00 |
| TDS (Three Times Daily) | 06:00, 14:00, 22:00 |
| QID (Four Times Daily) | 06:00, 12:00, 18:00, 00:00 |
| Q4H (Every 4 Hours) | Every 4 hours from 00:00 |
| STAT | Single entry at order time |
| PRN (As Needed) | No auto-generation; created manually |

**Administration statuses:**

| Status | Color | Description |
|--------|-------|-------------|
| Scheduled | Grey | Medication due, not yet given |
| Given | Green | Successfully administered |
| Self-Administered | Green | Patient self-administered |
| Held | Yellow | Temporarily held (reason required) |
| Refused | Dark Grey | Patient refused (reason required) |
| Delayed | Orange | Given late (reason + delay minutes recorded) |
| Missed | Red | Not given within grace period (auto-set by scheduler) |

**To administer a medication:**
1. Open the **MAR Board** (filtered by ward, date, shift)
2. Find the patient row and scheduled time slot
3. Click on the Scheduled (grey) pill
4. Select the action: Given, Held, Refused, Delayed
5. For Held/Refused/Delayed: provide the required reason
6. Confirm — the pill color updates

**PRN medications:**
- Click **Add PRN Entry** on the MAR Board
- Select the PRN medication order
- Record the administration details

**Overdue detection:** Every 15 minutes, the scheduler marks Scheduled entries past their time + 60 minutes as "Missed" and fires real-time alerts.

**Shift boundaries:**

| Shift | Start | End |
|-------|-------|-----|
| Morning | 06:00 | 14:00 |
| Afternoon | 14:00 | 22:00 |
| Night | 22:00 | 06:00 (next day) |

**MAR Board display:** A grid with patient rows (sorted by bed) and time-slot columns. Color-coded pills show the status of each medication at each time.

### 10.3 Lab Sample Lifecycle

> **Audience:** Nursing User, Laboratory User, Physician

Lab samples are tracked from creation through to result publication.

**Lifecycle:**

```
Pending → Collected → In Transit → Received → Processing → Completed
                                             ↘ Rejected (bad condition)
                                               → New sample (Pending)
```

**Step-by-step:**

1. **Creation** — Automatic when a Lab Test order is placed. A unique barcode is generated.
2. **Collection** — Nurse/phlebotomist records bedside collection (who, when, site). SLA milestone "Sample Collected" recorded.
3. **Handoff** — Sample handler records transport (mode: Manual/Pneumatic Tube/Runner). SLA milestone "Sample Handed Off".
4. **Receipt** — Lab technician receives and assesses sample condition (Acceptable/Hemolyzed/Clotted/Insufficient/Contaminated). SLA milestone "Sample Received".
5. **Recollection** — If condition is unacceptable, original sample is marked "Rejected", a new sample is auto-created with a parent link, and nursing is notified.
6. **Result Publication** — When the Lab Test is submitted in ERPNext, the linked sample is marked "Completed". Critical values trigger automatic detection and prominent alerts.
7. **Critical Result Acknowledgment** — Must be explicitly acknowledged by a physician or nurse. Records acknowledging user and timestamp.

**Collection Queue:** The `get_collection_queue` API provides a filterable list of samples pending collection, sorted by urgency.

---

## 11. Module H — ICU & Device Monitoring

> **Audience:** ICU Administrator, Nursing User, Physician, Device Integration User

### 11.1 ICU Monitoring Profiles

Monitoring profiles auto-apply specific chart templates when a patient is admitted to a particular unit type.

**Example:** When a patient is admitted to an ICU bed, the system can automatically activate:
- ICU Vitals chart (every 60 minutes)
- Ventilator Monitoring chart (every 120 minutes)
- Glucose Monitoring chart (every 240 minutes)

**To configure:**
1. Navigate to **ICU Monitoring Profile** → **+ Add**
2. Select the unit type (e.g., ICU, MICU, NICU)
3. Add chart templates with frequencies
4. Save

Default profiles are seeded on install.

### 11.2 Device Observation Feed

External medical devices (monitors, ventilators, infusion pumps) can feed observations into the system.

**To submit device data:**
1. The device integration sends data via `ingest_observation` API
2. Each feed batch is validated against a **Device Observation Mapping** that maps device parameters to chart template parameters
3. Validated observations are recorded as chart entries
4. Pending validations can be reviewed via `get_pending_validations`

**Device Observation Mapping** defines:
- Device identifier → Chart template
- Device parameter name → Chart parameter name
- Unit conversion rules

### 11.3 Protocol Bundles

Protocol bundles define structured care protocols (e.g., Sepsis 1-Hour Bundle, Ventilator Weaning Protocol).

**To configure a protocol:**
1. Navigate to **Monitoring Protocol Bundle** → **+ Add**
2. Enter bundle name, category, and compliance target
3. Add steps with:
   - Step name and description
   - Sequence number
   - Target completion time (minutes from activation)
   - Weight (for compliance score calculation)
4. Save

**To activate a protocol for a patient:**
1. From the Inpatient Record, activate the protocol
2. The system creates an **Active Protocol Bundle** with a step tracker for each step
3. Steps can be: Completed, Skipped (with reason), or Missed (auto by scheduler)

**Compliance monitoring:**
- Every 15 minutes, the scheduler checks for missed protocol steps
- A compliance score is computed based on step completion and weights
- Protocol compliance reports are available for audit

**Constraints:**
- At least one step is required per bundle
- No duplicate step names or sequence numbers
- Timing and weight values must be non-negative
- Compliance target must be between 0 and 100

---

## 12. Module I — TPA, Billing & Claims

> **Audience:** TPA Desk User, IPD Billing User, Healthcare Administrator

### 12.1 TPA Pre-Authorization

Pre-auth requests are sent to insurers/TPAs before or during admission for cost approval.

**To create a pre-auth request:**
1. From the Inpatient Record, click **Create Pre-Auth Request**
2. Or navigate to **TPA Preauth Request** → **+ Add**
3. Fill in: patient, payer profile, primary diagnosis, treating practitioner, requested amount
4. Save (status: Draft)

**Lifecycle:**

```
Draft → Submitted → Query Raised ↔ Resubmitted → Approved / Partially Approved / Rejected
                                                    ↓
                                                  Closed
```

| State | Description |
|-------|-------------|
| Draft | Initial creation, not yet sent |
| Submitted | Sent to TPA for review |
| Query Raised | TPA has requested additional information |
| Resubmitted | Hospital responded to query |
| Approved | Full amount approved |
| Partially Approved | Lesser amount approved |
| Rejected | Request denied |
| Closed | Final state after settlement |

**Query-Response cycle:**
- When TPA raises a query, hospital staff add a Response entry to the `responses` child table
- The request is then resubmitted
- This cycle can repeat multiple times

**Audit:** Every status change records user, timestamp, and creates timeline comments on the Patient and Inpatient Record.

### 12.2 Payer Billing Rule Sets

Billing rules define how charges are split between payer and patient.

**Rule types:**
- **Non-Payable** — Item/group not covered by payer
- **Co-Pay Override** — Custom co-pay percentage for specific items
- **Sub-Limit** — Maximum amount for specific items/groups
- **Package Inclusion** — Item included in package rate
- **Excluded Consumable** — Specific consumables excluded from coverage
- **Room Rent Cap** — Maximum room rent payable by payer

**Resolution priority:**
1. Specific payer match (payer type + specific payer/insurer) takes priority
2. Generic payer type match (payer type only)
3. Date range validation: active within current dates

### 12.3 Interim Bills

The `get_interim_bill` API generates a point-in-time billing summary for the patient's current stay, split between payer and patient share based on applicable billing rules.

The `get_bill_split` API computes the payer vs. patient liability for individual charges.

### 12.4 Discharge Billing Checklist

The billing checklist ensures all financial and clinical gates are cleared before final billing.

**Auto-check items (refreshed on demand):**
- Pending medication orders
- Pending lab samples
- Unposted procedures
- Room rent charges
- Discharge summary availability
- TPA pre-auth status (for insured patients)

**Statuses:**

```
Pending → In Progress → Cleared
                      → Overridden (with authorized override)
```

**Override flow:**
1. User clicks "Override All"
2. Prompted for override reason (mandatory)
3. Override records: user, datetime, reason
4. Status set to "Overridden" — discharge billing can proceed

**Who can override:** Healthcare Administrator or authorized billing users.

### 12.5 TPA Claim Pack

After discharge, claim documents are bundled and submitted to the TPA/insurer.

**To create a claim pack:**
1. From the Inpatient Record, click **Create Claim Pack**
2. The system auto-generates a document checklist:
   - Final Bill
   - Bill Break-Up
   - Discharge Summary
   - Investigation Reports
   - Pre-Auth Approval Letter
   - Indoor Case Papers
   - Consent Forms
   - Photo ID
3. Each document has `is_available` and `is_mandatory` flags
4. Attach files to each document row
5. Submit for internal review

**Lifecycle:**

```
Draft → In Review → Submitted → Acknowledged → Settled
                                              → Disputed → Submitted (re-submit)
```

**Settlement tracking:** Settlement amount, date, reference, disallowance amount, and disallowance reason.

---

## 13. Module J — Discharge Journey

> **Audience:** Physician, Nursing User, IPD Admission Officer, IPD Billing User

The discharge journey coordinates three interconnected workflows.

### 13.1 Discharge Advice (Doctor)

**To initiate discharge:**
1. From the Inpatient Record (Admitted), click **Raise Discharge Advice**
2. Fill in:
   - Expected discharge date/time
   - Discharge type: Normal / LAMA / Against Medical Advice / Transfer / Death / Absconded
   - Condition at discharge
   - Primary diagnosis
   - Discharge medications (prescriptions to take home)
   - Follow-up instructions
   - Warning signs requiring immediate return
3. Click **Submit Advice**

**Lifecycle:**

```
Draft → Advised → Acknowledged (by nursing/desk) → Completed
      → Cancelled (requires reason)
```

**Constraints:**
- Only one active (non-cancelled, non-completed) advice per Inpatient Record
- Cancellation requires a reason
- IR must be in Admitted or Discharge Scheduled status

**Notifications on advice submission:** Nursing, Billing, Pharmacy, and TPA (for insured patients) are all notified via in-app and real-time alerts.

### 13.2 Nursing Discharge Checklist

When discharge advice is raised, the nursing team completes a structured checklist.

**To create the nursing checklist:**
1. After acknowledging the discharge advice, click **Create Nursing Checklist**
2. The system generates 15 standard items

**Standard items (9 mandatory):**
1. IV line and cannula removal
2. Catheter/drain removal (if applicable)
3. Medication counseling and reconciliation
4. Pharmacy receipt for discharge medications
5. Home-care instructions provided
6. Warning signs education
7. Patient belongings returned
8. Final vitals recorded
9. Wristband removal
10. Discharge papers signed

**Additional items (6 optional):**
11. Drain removal confirmation
12. Diet instructions
13. Follow-up appointment scheduled
14. Valuables check
15. Escort arrangement
16. Transport arrangement

**Item actions:**

| Action | Description | Who |
|--------|-------------|-----|
| Complete | Mark item as Done | Nursing User |
| Not Applicable | Item doesn't apply | Nursing User |
| Skip | Skip with mandatory reason | Nursing User |
| Sign Off | Complete the entire checklist | Nursing User (validates all mandatory items done) |
| Verify | Senior nurse verification | Senior Nursing User |

**Lifecycle:**

```
Pending → In Progress → Completed (via sign-off) → Verified (optional)
```

### 13.3 Bed Vacate & Housekeeping

Once all discharge steps are complete, the bed is vacated.

**"Ready to vacate" criteria (all must be true):**
- Discharge advice is Acknowledged or Completed
- Billing checklist is Cleared or Overridden
- Nursing checklist is Completed

**To vacate the bed:**
1. From the Inpatient Record, click **Vacate Bed**
2. The system:
   - Creates a **Bed Movement Log** (discharge entry)
   - Marks the bed as **Dirty**
   - Creates a **Bed Housekeeping Task** (if auto-mark policy is enabled)
   - Clears bed fields on the Inpatient Record
   - Updates ward/room capacity rollups
   - Sends real-time notifications to admission officers and nursing

### 13.4 Housekeeping Task

**Lifecycle:**

```
Pending → In Progress (cleaning started) → Completed (cleaning done, bed = Clean)
        → Cancelled
```

**To manage housekeeping:**
1. Open the Bed Housekeeping Task
2. Click **Start Cleaning** — status changes to In Progress, bed housekeeping status = "In Progress"
3. Click **Complete Cleaning** — status changes to Completed, bed marked Clean and Available

**SLA monitoring:** A scheduler job (every 15 minutes) checks for housekeeping tasks past their SLA deadline and sends breach notifications to Healthcare Administrators and Nursing.

### 13.5 Aggregate Discharge Status

The `get_discharge_status` API returns a unified view of all discharge components:

```json
{
  "advice": {"name": "DDA-2026-00001", "status": "Acknowledged"},
  "billing_checklist": {"name": "DBC-2026-00001", "status": "Cleared"},
  "nursing_checklist": {"name": "NDC-2026-00001", "status": "Completed"},
  "ready_to_vacate": true
}
```

This status is displayed as a banner on the Inpatient Record form, giving all stakeholders a single view of discharge progress.

---

## 14. Modules K & L — Dashboards & Reports

> **Audience:** Healthcare Administrator, Nursing User, Physician

### 14.1 IPD Operations Workspace

The **IPD Operations** workspace provides centralized access to all operational views:

**Shortcuts:**
- Bed Occupancy Dashboard
- Live Bed Board
- ADT Census
- Transfer & Housekeeping Report
- Nursing Workload
- Incident Alert Report
- Device Exception Report

### 14.2 Reports

| Report | Description | Audience |
|--------|-------------|----------|
| **Bed Occupancy Dashboard** | Real-time occupancy by ward, room type, with trend | Admin, Nursing |
| **Transfer & Housekeeping** | Bed transfers and housekeeping turnaround times | Admin |
| **ADT Census** | Admissions, Discharges, Transfers for a date range | Admin |
| **Doctor Census** | Patient load per consultant | Admin, Physician |
| **Documentation Compliance** | Progress note completion rates | Admin |
| **Order TAT** | Order turnaround times by type and urgency | Admin, Pharmacy, Lab |
| **ICU Protocol Compliance** | Protocol bundle completion and compliance scores | ICU Admin |
| **Nursing Workload** | Patient-to-nurse ratios and charting load | Nursing Admin |
| **Incident Alert Report** | Critical events (critical values, missed meds, SLA breaches) | Admin |
| **Device Exception Report** | Device feed errors and rejected observations | Biomedical, ICU Admin |

### 14.3 Protocol Compliance Report

Detailed drilldown report for care protocol adherence:
- Bundle-level compliance scores
- Step-level completion status
- Time-to-completion vs. target
- Missed step analysis

---

## 15. Print Formats & Labels

| Format | DocType | Content |
|--------|---------|---------|
| **IPD Wristband Label** | Inpatient Record | Patient name, MR number, DOB, blood group, allergy alerts, QR code |
| **IPD Bed Tag** | Inpatient Record | Patient name, bed number, ward, consultant, admission date |
| **IPD File Cover** | Inpatient Record | Full patient demographics, admission details, payer information |
| **IPD Interim Bill** | Inpatient Record | Itemized charges, payer split, running total |

Labels support:
- QR code and barcode generation (via Jinja helpers)
- Allergy marker indicators (auto-populated from intake data)
- Standard label printer formatting

---

## 16. Automated System Jobs

The following background jobs run automatically:

| Schedule | Job | Description |
|----------|-----|-------------|
| Every 5 min | **Expire Bed Reservations** | Auto-expires active reservations past their end time; releases beds back to Vacant |
| Every 5 min | **Check Order SLA Breaches** | Flags overdue clinical orders; sends escalation notifications |
| Every 15 min | **Check Overdue Charts** | Identifies bedside charts past their scheduled observation time; increments missed count; sends alerts |
| Every 15 min | **Mark Overdue MAR Entries** | Changes Scheduled MAR entries to Missed if 60+ minutes overdue; fires real-time alerts |
| Every 15 min | **Check Protocol Compliance** | Flags missed protocol steps; sends compliance breach notifications |
| Every 15 min | **Check Housekeeping SLA** | Flags housekeeping tasks past their SLA deadline; sends notifications |
| Daily | **Notify Expiring Payer Profiles** | Alerts TPA Desk and Healthcare Administrator about payer profiles expiring within 7 days |

---

## 17. Quick Reference by Role

### For Doctors (Physicians)

**Your daily workflow:**
1. **Morning Rounds** — Use Round Sheet (`get_census`, `get_round_summary`) to review your patient list
2. **Problem List** — Review and update active problems for each patient
3. **Progress Notes** — Create Patient Encounters linked to the IR for documentation
4. **Orders** — Place medication, lab, radiology, and procedure orders from the encounter
5. **Review Results** — Check lab results, acknowledge critical values
6. **Substitution Approvals** — Approve or reject pharmacy substitution requests
7. **Discharge** — Raise discharge advice when ready; fill in discharge medications and follow-up instructions

**Key actions available from the Inpatient Record:**
- Add Admission Note / Progress Note
- Add Problem / Resolve Problem
- Create Round Note
- Place Orders (Medication, Lab, Radiology, Procedure)
- Raise Discharge Advice
- View Charts, I/O Balance, MAR

### For Nurses (Nursing Users)

**Your daily workflow:**
1. **Shift Handover** — Review nursing notes (Handoff category), active charts, pending medications
2. **Intake Assessments** — Complete admission assessments for new patients
3. **Charting** — Record vitals and observations per chart frequency
4. **I/O Monitoring** — Record fluid intake and output
5. **MAR** — Administer scheduled medications; record status (Given/Held/Refused)
6. **Lab Samples** — Collect samples, record collection, hand off for transport
7. **Nursing Notes** — Document assessments, interventions, and escalations
8. **Risk Monitoring** — Review and recalculate patient risk flags (fall, pressure, nutrition)
9. **Discharge** — Complete the nursing discharge checklist when discharge advice is raised

**Key screens:**
- **MAR Board** — Ward-level medication administration grid
- **Charting Dashboard** — Active charts, overdue alerts, observation trends
- **Collection Queue** — Pending lab samples for collection
- **Nurse Station Queue** — Incoming orders relevant to nursing

### For Admission Officers (IPD Admission Officer)

**Your daily workflow:**
1. **Monitor Bed Board** — Track real-time bed availability across wards
2. **Manage Reservations** — Create, activate, and cancel bed reservations
3. **Process Admissions** — Create admission checklists, allocate beds
4. **Verify Eligibility** — Initiate eligibility checks for insured patients
5. **Print Labels** — Generate wristbands, bed tags, and file covers
6. **Process Discharges** — Vacate beds, assign housekeeping tasks
7. **Patient Registration** — Register new patients with demographic and ID details

### For Pharmacy Staff (Pharmacy Users)

**Your daily workflow:**
1. **Pharmacy Queue** — Review incoming medication orders
2. **Stock Verification** — Check availability before dispensing
3. **Dispensing** — Dispense medications (full or partial)
4. **Substitutions** — Request substitutions for unavailable medications; process approvals
5. **Returns** — Process medication returns for discharged patients

### For Lab Staff (Laboratory Users)

**Your daily workflow:**
1. **Lab Queue** — Review incoming lab test orders
2. **Sample Receipt** — Receive samples, assess condition
3. **Recollection** — Flag bad samples for recollection
4. **Result Entry** — Enter results in Lab Test; critical values auto-flagged
5. **Acknowledge Orders** — Acknowledge incoming orders

### For TPA Desk (TPA Desk Users)

**Your daily workflow:**
1. **Eligibility Checks** — Process pending eligibility verifications
2. **Pre-Auth Requests** — Submit, track, and respond to TPA queries
3. **Claim Packs** — Assemble discharge claim documents
4. **Payer Profiles** — Manage patient payer profiles, monitor expiry

### For Billing Staff (IPD Billing Users)

**Your daily workflow:**
1. **Interim Bills** — Generate interim bills for long-stay patients
2. **Discharge Billing Checklist** — Clear financial gates before final billing
3. **Bill Split** — Review payer vs. patient liability
4. **Tariff Management** — Maintain room tariff mappings

---

## Appendix A: Key Constraints and Business Rules Summary

| Area | Constraint |
|------|-----------|
| Bed Reservation | Row-level database locking prevents double-booking; auto-expires per policy TTL |
| Bed Allocation | Blocked if Strict eligibility enforcement and no verified check (non-Cash patients) |
| Admission Checklist | Complete/Overridden checklists are immutable; only Healthcare Admin can waive items |
| Intake Assessment | One per IR per template; completed assessments are immutable; mandatory fields enforced |
| Chart Entries | Cannot record on paused/discontinued charts; no future-dated entries; corrections only (no edits) |
| Nursing Notes | No edits after save — addendum model only |
| Clinical Orders | Valid transitions enforced server-side; cancellation requires reason; SLA auto-tracked |
| MAR | Hold/Refusal requires reason; overdue entries auto-marked Missed after 60 min |
| Lab Samples | Bad condition triggers auto-recollection; critical results require explicit acknowledgment |
| Pharmacy Dispense | Substitution requires doctor approval; cannot dispense against cancelled/draft orders |
| Protocol Bundles | Steps auto-flagged missed by scheduler; compliance score auto-computed |
| Eligibility Check | Status transitions enforced server-side; only TPA Desk/Admin can change status |
| TPA Preauth | Query-response cycle can repeat; all transitions audited |
| Discharge Advice | Only one active advice per IR; cancellation requires reason |
| Nursing Discharge | Sign-off validates all mandatory items; skip requires reason |
| Discharge Billing | Override requires reason and authorization |
| Bed Vacate | Requires advice acknowledged + billing cleared + nursing completed |
| Housekeeping | SLA monitored every 15 min; completion transitions bed to Clean/Available |
| Patient Registration | Aadhaar (12 digits), PAN (format validated), ABHA (14 digits), Mobile (10 digits, starts 6-9) |
| Room Tariff | No overlapping date ranges for same room type + payer; at least one tariff item required |

## Appendix B: Notification Events

| Event | Recipients | Method |
|-------|-----------|--------|
| Order Created | Target department + Nursing | In-app |
| Order SLA Breach | Escalation role | In-app |
| Critical Chart Value | Nursing + Attending Physician | Real-time + In-app |
| Overdue Chart | Nursing station | Real-time |
| MAR Missed | Nursing station | Real-time |
| Critical Lab Result | Ordering Practitioner + Nursing + Physician | In-app |
| Bad Sample (Recollection) | Nursing | In-app |
| Substitution Requested | Ordering Practitioner + Physicians | In-app |
| Discharge Advice Submitted | Nursing + Billing + Pharmacy + TPA | In-app + Real-time |
| Discharge Advice Acknowledged | Advising Consultant | In-app |
| Bed Vacated | Admission Officers + Nursing | In-app + Real-time |
| Housekeeping SLA Breach | Healthcare Admin + Nursing | In-app |
| Eligibility Rejected | Receptionist + TPA Desk | In-app |
| Payer Profile Expiring | TPA Desk + Healthcare Admin | In-app |
| Critical Nursing Note | All viewers of patient record | Real-time |
| Protocol Step Missed | Nursing + ICU Admin | In-app |
| Reservation Expired | Reserving User | Real-time |

## Appendix C: Glossary

| Term | Definition |
|------|-----------|
| **ADT** | Admission, Discharge, Transfer |
| **IR** | Inpatient Record — the core document tracking a patient's hospital stay |
| **MAR** | Medication Administration Record |
| **I/O** | Intake/Output (fluid balance monitoring) |
| **SLA** | Service Level Agreement — time targets for order fulfillment |
| **TPA** | Third Party Administrator (insurance intermediary) |
| **HSU** | Healthcare Service Unit (ERPNext standard for facility locations) |
| **PRN** | Pro Re Nata — medication given as needed |
| **STAT** | Immediately (highest urgency) |
| **LAMA** | Leave Against Medical Advice |
| **GCS** | Glasgow Coma Scale |
| **ICU** | Intensive Care Unit |
| **HDU** | High Dependency Unit |
| **OD/BD/TDS/QID** | Once/Twice/Three times/Four times daily |
| **Q4H** | Every 4 hours |

---

*This manual covers Alcura IPD Extensions v1.x. For technical API documentation, refer to the `docs/` folder in the application source code.*
