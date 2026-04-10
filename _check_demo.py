"""Check what demo data remains in the database."""
import frappe

patients = [
    "Rajan Mehta", "Lakshmi Devi", "Mohammad Rafi", "Anita Sharma",
    "Suresh Kumar", "Geeta Rani", "Vijay Patil", "Priya Menon",
    "Ramesh Yadav", "Sita Kumari", "Anil Joshi", "Fatima Begum",
    "Dinesh Gupta", "Kavya Nair", "Bharat Singh", "Vikram Malhotra",
    "Rekha Jain", "Ashok Bansal", "Meena Patel", "Rajiv Saxena",
    "Pooja Tiwari", "Harish Chandra", "Deepa Krishnan", "Sanjeev Kapoor",
    "Nandini Rao",
]

existing_patients = [p for p in patients if frappe.db.exists("Patient", p)]
print(f"Patients remaining: {len(existing_patients)}/{len(patients)}")
for p in existing_patients:
    print(f"  - {p}")

irs = frappe.get_all("Inpatient Record", filters={"patient_name": ["in", patients]}, pluck="name")
print(f"\nInpatient Records remaining: {len(irs)}")
for ir in irs:
    print(f"  - {ir}")

doctypes_to_check = [
    "Hospital Ward", "Hospital Room", "Hospital Bed",
    "Healthcare Service Unit Type", "Healthcare Service Unit",
    "Healthcare Practitioner", "Medical Department",
    "IPD Clinical Order", "IPD Bedside Chart", "IPD Chart Entry",
    "IPD IO Entry", "IPD Nursing Note", "IPD MAR Entry",
    "IPD Dispense Entry", "IPD Lab Sample", "IPD Problem List Item",
    "Admission Checklist", "IPD Discharge Advice",
    "Nursing Discharge Checklist", "Discharge Billing Checklist",
    "Bed Movement Log", "Bed Housekeeping Task",
    "Patient Payer Profile", "TPA Preauth Request",
    "Payer Eligibility Check", "Payer Billing Rule Set",
    "Room Tariff Mapping", "TPA Claim Pack",
    "Active Protocol Bundle", "Bed Reservation",
    "IPD Order SLA Config",
]

print("\n--- Record counts for demo-related DocTypes ---")
for dt in doctypes_to_check:
    try:
        count = frappe.db.count(dt)
        if count > 0:
            print(f"  {dt}: {count}")
    except Exception as e:
        print(f"  {dt}: ERROR ({e})")

# Check what the rebuild function finds
print("\n--- Testing _rebuild_tracking_from_db ---")
from alcura_ipd_ext.setup.demo_data import _rebuild_tracking_from_db
rebuilt = _rebuild_tracking_from_db()
for dt, names in rebuilt.items():
    print(f"  {dt}: {len(names)} records")
total = sum(len(v) for v in rebuilt.values())
print(f"  TOTAL rebuilt: {total}")

# Also check what _load_tracking returns
from alcura_ipd_ext.setup.demo_data import _load_tracking
loaded = _load_tracking()
print(f"\n_load_tracking result: {'has data' if loaded else 'None'}")
