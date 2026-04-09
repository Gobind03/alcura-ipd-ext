"""Generate comprehensive demo data for the Alcura IPD module.

Creates a realistic hospital scenario spanning ~14 days with 25 patients across
5 wards, producing enough volume for meaningful dashboards and reports.
"""

from __future__ import annotations

import json
import random
from datetime import timedelta

import frappe
from frappe import _
from frappe.utils import now_datetime, getdate, nowdate

DEMO_DATA_KEY = "alcura_ipd_demo_records"

# ── Reproducible random seed ────────────────────────────────────────
_RNG = random.Random(42)

# ── Master data definitions ─────────────────────────────────────────

DEPARTMENTS = [
	"Cardiology",
	"General Medicine",
	"Orthopedics",
	"General Surgery",
	"Neurology",
	"Pulmonology",
	"Internal Medicine",
]

PRACTITIONERS = [
	("Rajesh", "Sharma", "Male", "Cardiology"),
	("Priya", "Patel", "Female", "General Medicine"),
	("Amit", "Verma", "Male", "Orthopedics"),
	("Sunita", "Reddy", "Female", "General Surgery"),
	("Vikram", "Singh", "Male", "Neurology"),
	("Meera", "Iyer", "Female", "Pulmonology"),
	("Arjun", "Nair", "Male", "Internal Medicine"),
	("Kavita", "Gupta", "Female", "General Medicine"),
]

HSU_TYPES = [
	("General Ward", "General", "Multi-Bed", "Standard"),
	("Private Room", "Private", "Single", "Standard"),
	("Semi-Private Room", "Semi-Private", "Double", "Standard"),
	("ICU Bay", "ICU", "Multi-Bed", "Critical"),
	("HDU Bay", "HDU", "Multi-Bed", "High"),
]

MEDICATIONS = [
	("Paracetamol 500mg", "Oral", "Q6H", "500 mg"),
	("Ceftriaxone 1g IV", "IV", "BD", "1 g"),
	("Metformin 500mg", "Oral", "BD", "500 mg"),
	("Atorvastatin 20mg", "Oral", "OD", "20 mg"),
	("Pantoprazole 40mg", "Oral", "OD", "40 mg"),
	("Insulin Regular", "SC", "TDS", "10 units"),
	("Heparin 5000 IU", "IV", "Q6H", "5000 IU"),
	("Amoxicillin 500mg", "Oral", "TDS", "500 mg"),
	("Ondansetron 4mg", "IV", "PRN", "4 mg"),
	("Tramadol 50mg", "Oral", "Q8H", "50 mg"),
	("Metoprolol 25mg", "Oral", "BD", "25 mg"),
	("Amlodipine 5mg", "Oral", "OD", "5 mg"),
	("Furosemide 40mg", "IV", "BD", "40 mg"),
	("Enoxaparin 40mg", "SC", "OD", "40 mg"),
	("Dexamethasone 4mg", "IV", "BD", "4 mg"),
]

LAB_TESTS = [
	"Complete Blood Count",
	"Blood Sugar Fasting",
	"Renal Function Test",
	"Liver Function Test",
	"Lipid Profile",
	"Serum Electrolytes",
	"Prothrombin Time",
	"Blood Culture",
	"Urine Routine",
	"Arterial Blood Gas",
	"Cardiac Enzymes",
	"D-Dimer",
	"C-Reactive Protein",
	"HbA1c",
	"Thyroid Profile",
]

# Ward layout: (ward_code, ward_name, classification, hsu_type_idx, rooms)
# rooms: list of (room_number, num_beds)
WARD_LAYOUT = [
	("ICU", "Intensive Care Unit", "ICU", 3, [("R1", 4), ("R2", 4)]),
	("HDU", "High Dependency Unit", "HDU", 4, [("R1", 4)]),
	("GW", "General Ward", "General", 0, [("R1", 4), ("R2", 4), ("R3", 4)]),
	("PW", "Private Wing", "Private", 1, [("R1", 1), ("R2", 1), ("R3", 1), ("R4", 1)]),
	("SP", "Semi-Private Wing", "Semi-Private", 2, [("R1", 2), ("R2", 2), ("R3", 2)]),
]

PAYER_COMPANIES = [
	("Star Health Insurance", "Insurance TPA"),
	("ICICI Lombard General", "Insurance TPA"),
	("New India Assurance", "Insurance TPA"),
	("Max Bupa Health", "Insurance TPA"),
	("Infosys Technologies", "Corporate"),
	("Tata Steel Limited", "Corporate"),
]

# Patient scenarios: (first, last, sex, age, blood_group, ward_idx, room_idx,
#   bed_idx, diagnosis, dept_idx, days_admitted, payer_kind, priority,
#   expected_los, status)
# payer_kind: "Cash", "Insurance", "Corporate"
# status: "active" or "discharged"
PATIENT_SCENARIOS = [
	# ── ICU patients ────────────────────────────────────────────
	("Rajan", "Mehta", "Male", 65, "B+", 0, 0, 0,
	 "Acute Myocardial Infarction", 0, 5, "Insurance", "Emergency", 10, "active"),
	("Lakshmi", "Devi", "Female", 72, "O+", 0, 0, 1,
	 "Severe Sepsis", 6, 3, "Cash", "Emergency", 7, "active"),
	("Mohammad", "Rafi", "Male", 58, "A+", 0, 0, 2,
	 "Post-CABG Recovery", 0, 2, "Insurance", "Emergency", 14, "active"),
	("Anita", "Sharma", "Female", 45, "AB+", 0, 1, 0,
	 "Status Epilepticus", 4, 1, "Corporate", "Emergency", 5, "active"),
	# ── HDU patients ────────────────────────────────────────────
	("Suresh", "Kumar", "Male", 60, "B-", 1, 0, 0,
	 "COPD Exacerbation", 5, 7, "Insurance", "Urgent", 10, "active"),
	("Geeta", "Rani", "Female", 55, "O+", 1, 0, 1,
	 "Diabetic Ketoacidosis", 6, 2, "Cash", "Emergency", 5, "active"),
	("Vijay", "Patil", "Male", 48, "A-", 1, 0, 2,
	 "Post-Appendectomy Monitoring", 3, 3, "Insurance", "Routine", 4, "active"),
	# ── General Ward patients ───────────────────────────────────
	("Priya", "Menon", "Female", 35, "O+", 2, 0, 0,
	 "Post-Partum Hemorrhage", 1, 4, "Insurance", "Urgent", 5, "active"),
	("Ramesh", "Yadav", "Male", 68, "B+", 2, 0, 1,
	 "Community-Acquired Pneumonia", 5, 6, "Cash", "Routine", 7, "active"),
	("Sita", "Kumari", "Female", 42, "A+", 2, 0, 2,
	 "Cholecystectomy Recovery", 3, 3, "Cash", "Routine", 4, "active"),
	("Anil", "Joshi", "Male", 55, "O-", 2, 1, 0,
	 "Acute Pancreatitis", 1, 5, "Corporate", "Urgent", 8, "active"),
	("Fatima", "Begum", "Female", 62, "AB+", 2, 1, 1,
	 "Urinary Tract Infection", 6, 2, "Cash", "Routine", 3, "active"),
	("Dinesh", "Gupta", "Male", 70, "A+", 2, 1, 2,
	 "Hip Fracture - Pre-Op", 2, 8, "Insurance", "Urgent", 12, "active"),
	("Kavya", "Nair", "Female", 28, "B+", 2, 2, 0,
	 "Dengue Hemorrhagic Fever", 1, 4, "Cash", "Urgent", 5, "active"),
	("Bharat", "Singh", "Male", 50, "O+", 2, 2, 1,
	 "Severe Cellulitis", 3, 3, "Corporate", "Routine", 5, "active"),
	# ── Private Ward patients ───────────────────────────────────
	("Vikram", "Malhotra", "Male", 45, "A+", 3, 0, 0,
	 "Total Knee Replacement - Post-Op", 2, 4, "Insurance", "Routine", 7, "active"),
	("Rekha", "Jain", "Female", 52, "B-", 3, 1, 0,
	 "Laparoscopic Hysterectomy", 3, 2, "Insurance", "Routine", 4, "active"),
	("Ashok", "Bansal", "Male", 60, "O+", 3, 2, 0,
	 "Post-Coronary Angioplasty", 0, 3, "Corporate", "Urgent", 5, "active"),
	# ── Semi-Private patients ───────────────────────────────────
	("Meena", "Patel", "Female", 38, "A+", 4, 0, 0,
	 "Cesarean Section Recovery", 1, 3, "Insurance", "Routine", 5, "active"),
	("Rajiv", "Saxena", "Male", 65, "O-", 4, 1, 0,
	 "Acute Ischemic Stroke", 4, 10, "Cash", "Emergency", 14, "active"),
	("Pooja", "Tiwari", "Female", 30, "B+", 4, 2, 0,
	 "Acute Appendicitis - Post-Op", 3, 2, "Cash", "Urgent", 3, "active"),
	# ── Discharged patients ─────────────────────────────────────
	("Harish", "Chandra", "Male", 75, "A-", 2, 2, 2,
	 "Community-Acquired Pneumonia", 5, 9, "Insurance", "Routine", 7, "discharged"),
	("Deepa", "Krishnan", "Female", 40, "O+", 3, 3, 0,
	 "Laparoscopic Cholecystectomy", 3, 4, "Insurance", "Routine", 3, "discharged"),
	("Sanjeev", "Kapoor", "Male", 55, "B+", 2, 2, 3,
	 "Congestive Heart Failure", 0, 12, "Corporate", "Urgent", 10, "discharged"),
	("Nandini", "Rao", "Female", 32, "AB-", 4, 0, 1,
	 "Post-Partum Complications", 1, 5, "Cash", "Urgent", 5, "discharged"),
]

# Frequency map: short code → minutes between doses
FREQ_MINUTES = {
	"OD": 1440, "BD": 720, "TDS": 480, "Q6H": 360, "Q8H": 480,
	"Q4H": 240, "Q12H": 720, "PRN": 0, "STAT": 0,
}

MAR_STATUSES = ["Given"] * 14 + ["Held"] * 2 + ["Missed"] * 2 + ["Delayed"] * 2

CHECKLIST_ITEMS = [
	("Photo ID Verified", "Identity", True),
	("Admission Consent Signed", "Consent", True),
	("Insurance Card Copy", "Financial", False),
	("Advance Deposit Collected", "Financial", True),
	("Allergies Documented", "Clinical", True),
	("Medication Reconciliation", "Clinical", True),
	("Personal Belongings List", "Personal", False),
	("Emergency Contact Recorded", "Personal", True),
	("Diet Preference Noted", "Personal", False),
	("DNAR / Advance Directive", "Consent", False),
]

NURSING_NOTE_TEMPLATES = [
	("Assessment", "Patient assessed on admission. Vitals stable. Oriented to time, place, and person."),
	("Intervention", "IV cannula inserted in right forearm. Site clean, no swelling."),
	("Response", "Patient reports pain reduced from 7/10 to 3/10 after analgesic administration."),
	("Handoff", "Patient stable through the shift. No acute events. Awaiting lab results."),
	("Escalation", "SpO2 dropped to 88%. O2 supplementation increased to 4L/min via nasal cannula. Physician notified."),
	("General", "Family visited. Patient ambulated with assistance for 10 minutes. Tolerating oral diet."),
	("Assessment", "Wound site inspection completed. Healing well, no signs of infection."),
	("Intervention", "Foley catheter care performed. Urine output adequate. Clear yellow."),
	("Handoff", "Night shift handover: Patient had one episode of vomiting at 0200. Anti-emetic given. Settled since."),
	("General", "Patient educated on deep breathing exercises and incentive spirometry."),
]

IO_TEMPLATES = [
	("Intake", "IV Fluid", "Normal Saline 0.9%", "IV", 500),
	("Intake", "IV Fluid", "Ringer's Lactate", "IV", 1000),
	("Intake", "Oral", "Water", "Oral", 200),
	("Intake", "Oral", "Juice", "Oral", 150),
	("Intake", "Blood Products", "Packed RBC", "IV", 350),
	("Intake", "TPN", "TPN Solution", "IV", 1000),
	("Output", "Urine", "Urine", "Catheter", 400),
	("Output", "Urine", "Urine", "Catheter", 600),
	("Output", "Drain", "Abdominal Drain", "Drain", 150),
	("Output", "Vomit", "Vomit", "Other", 100),
	("Output", "NG Aspirate", "NG Aspirate", "NG Tube", 200),
]

PROBLEM_TEMPLATES = [
	("Acute Myocardial Infarction", "I21.9", "Severe"),
	("Severe Sepsis", "A41.9", "Severe"),
	("Type 2 Diabetes Mellitus", "E11.9", "Moderate"),
	("Essential Hypertension", "I10", "Mild"),
	("COPD", "J44.1", "Moderate"),
	("Acute Kidney Injury", "N17.9", "Severe"),
	("Anemia", "D64.9", "Mild"),
	("Electrolyte Imbalance", "E87.8", "Moderate"),
	("Deep Vein Thrombosis Risk", "I82.9", "Moderate"),
	("Post-Surgical Pain", "G89.18", "Moderate"),
	("Pressure Injury Risk", "L89.90", "Mild"),
	("Fall Risk", "W19", "Moderate"),
	("Malnutrition Risk", "E46", "Mild"),
	("Urinary Tract Infection", "N39.0", "Moderate"),
	("Pneumonia", "J18.9", "Severe"),
]

# ── Tracking helpers ────────────────────────────────────────────────

_records: dict[str, list[str]] = {}


def _track(doctype: str, name: str) -> None:
	_records.setdefault(doctype, []).append(name)


def _ts(days_ago: float = 0, hours_ago: float = 0, minutes_ago: float = 0) -> str:
	"""Return a datetime string relative to now."""
	dt = now_datetime() - timedelta(days=days_ago, hours=hours_ago, minutes=minutes_ago)
	return dt.strftime("%Y-%m-%d %H:%M:%S")


def _date(days_ago: int = 0) -> str:
	d = getdate(nowdate()) - timedelta(days=days_ago)
	return d.strftime("%Y-%m-%d")


def _safe_insert(doc_dict: dict, ignore_links: bool = False) -> str | None:
	"""Insert a doc and track it.  Returns name or None on failure."""
	try:
		doc = frappe.get_doc(doc_dict)
		doc.flags.ignore_permissions = True
		doc.flags.ignore_links = ignore_links
		doc.insert()
		_track(doc.doctype, doc.name)
		return doc.name
	except Exception as e:
		frappe.log_error(
			f"Demo data: failed to create {doc_dict.get('doctype')}: {e}",
			"Demo Data Generation",
		)
		return None


# ── Master data creation ────────────────────────────────────────────

def _get_company() -> str:
	company = frappe.defaults.get_defaults().get("company")
	if not company:
		company = frappe.db.get_single_value("Global Defaults", "default_company")
	if not company:
		company = frappe.db.get_value("Company", {}, "name", order_by="creation asc")
	if not company:
		frappe.throw(_("No Company found. Please create a Company first."))
	return company


def _create_departments() -> dict[int, str]:
	"""Ensure Medical Departments exist.  Returns idx→name mapping."""
	mapping = {}
	for idx, dept_name in enumerate(DEPARTMENTS):
		if not frappe.db.exists("Medical Department", dept_name):
			_safe_insert({"doctype": "Medical Department", "department": dept_name})
		mapping[idx] = dept_name
	return mapping


def _create_practitioners(company: str) -> dict[int, str]:
	"""Create demo Healthcare Practitioners.  Returns idx→name."""
	mapping = {}
	for idx, (first, last, gender, dept) in enumerate(PRACTITIONERS):
		full = f"Dr. {first} {last}"
		existing = frappe.db.get_value(
			"Healthcare Practitioner",
			{"practitioner_name": full},
			"name",
		)
		if existing:
			mapping[idx] = existing
			continue
		name = _safe_insert({
			"doctype": "Healthcare Practitioner",
			"first_name": first,
			"last_name": last,
			"gender": gender,
			"department": dept,
			"status": "Active",
		})
		if name:
			mapping[idx] = name
	return mapping


def _create_hsu_types() -> dict[int, str]:
	"""Ensure Healthcare Service Unit Types exist with IPD classification."""
	mapping = {}
	for idx, (type_name, category, occ_class, intensity) in enumerate(HSU_TYPES):
		existing = frappe.db.get_value(
			"Healthcare Service Unit Type",
			{"healthcare_service_unit_type": type_name},
			"name",
		)
		if existing:
			mapping[idx] = existing
			continue
		name = _safe_insert({
			"doctype": "Healthcare Service Unit Type",
			"healthcare_service_unit_type": type_name,
			"inpatient_occupancy": 1,
			"ipd_room_category": category,
			"occupancy_class": occ_class,
			"nursing_intensity": intensity,
		})
		if name:
			mapping[idx] = name
	return mapping


def _create_items() -> dict[str, str]:
	"""Create Item masters for medications and charges.  Returns med_name→item_name."""
	item_map = {}
	groups_needed = {"Drug": "All Item Groups", "Services": "All Item Groups"}
	for grp, parent in groups_needed.items():
		if not frappe.db.exists("Item Group", grp):
			_safe_insert({
				"doctype": "Item Group",
				"item_group_name": grp,
				"parent_item_group": parent,
			})

	for med_name, route, freq, dose in MEDICATIONS:
		code = f"DEMO-{med_name.replace(' ', '-').upper()}"
		if frappe.db.exists("Item", code):
			item_map[med_name] = code
			continue
		name = _safe_insert({
			"doctype": "Item",
			"item_code": code,
			"item_name": med_name,
			"item_group": "Drug",
			"stock_uom": "Nos",
			"is_stock_item": 0,
		})
		if name:
			item_map[med_name] = name
	return item_map


def _create_customers() -> dict[str, str]:
	"""Create Customer records for payer companies."""
	cust_map = {}
	for cust_name, payer_type in PAYER_COMPANIES:
		if frappe.db.exists("Customer", cust_name):
			cust_map[cust_name] = cust_name
			continue
		name = _safe_insert({
			"doctype": "Customer",
			"customer_name": cust_name,
			"customer_type": "Company",
			"customer_group": frappe.db.get_single_value("Selling Settings", "customer_group")
			or "All Customer Groups",
			"territory": frappe.db.get_single_value("Selling Settings", "territory")
			or "All Territories",
		})
		if name:
			cust_map[cust_name] = name
	return cust_map


# ── Infrastructure creation ─────────────────────────────────────────

def _get_or_create_root_hsu(company: str) -> str:
	"""Find or create the top-level Healthcare Service Unit for the company."""
	root = frappe.db.get_value(
		"Healthcare Service Unit",
		{"company": company, "is_group": 1, "parent_healthcare_service_unit": ""},
		"name",
	)
	if root:
		return root
	root = frappe.db.get_value(
		"Healthcare Service Unit",
		{"company": company, "is_group": 1, "parent_healthcare_service_unit": ("is", "not set")},
		"name",
	)
	if root:
		return root
	hsu_name = f"{company} - All Service Units"
	if frappe.db.exists("Healthcare Service Unit", hsu_name):
		return hsu_name
	name = _safe_insert({
		"doctype": "Healthcare Service Unit",
		"healthcare_service_unit_name": hsu_name,
		"is_group": 1,
		"company": company,
	})
	return name or hsu_name


def _create_infrastructure(company: str, root_hsu: str, hsu_types: dict) -> dict:
	"""Create wards → rooms → beds.  Returns bed lookup dict."""
	abbr = frappe.get_cached_value("Company", company, "abbr") or "DEMO"
	beds_lookup = {}

	for w_idx, (ward_code, ward_name, classification, hsu_idx, rooms) in enumerate(WARD_LAYOUT):
		ward_hsu_name = f"{root_hsu} - {ward_name}"
		if not frappe.db.exists("Healthcare Service Unit", ward_hsu_name):
			_safe_insert({
				"doctype": "Healthcare Service Unit",
				"healthcare_service_unit_name": ward_hsu_name,
				"is_group": 1,
				"parent_healthcare_service_unit": root_hsu,
				"company": company,
			})

		ward_full = f"{abbr}-{ward_code}"
		if not frappe.db.exists("Hospital Ward", ward_full):
			_safe_insert({
				"doctype": "Hospital Ward",
				"ward_code": ward_code,
				"ward_name": ward_name,
				"company": company,
				"ward_classification": classification,
				"healthcare_service_unit": ward_hsu_name,
				"is_active": 1,
			})

		hsu_type_name = hsu_types.get(hsu_idx)
		for r_idx, (room_num, num_beds) in enumerate(rooms):
			room_full = f"{ward_full}-{room_num}"
			if not frappe.db.exists("Hospital Room", room_full):
				_safe_insert({
					"doctype": "Hospital Room",
					"room_number": room_num,
					"room_name": f"{ward_name} - Room {room_num}",
					"hospital_ward": ward_full,
					"service_unit_type": hsu_type_name,
					"is_active": 1,
				})

			for b_idx in range(num_beds):
				bed_num = f"B{b_idx + 1}"
				bed_full = f"{room_full}-{bed_num}"
				if not frappe.db.exists("Hospital Bed", bed_full):
					_safe_insert({
						"doctype": "Hospital Bed",
						"bed_number": bed_num,
						"bed_label": f"{ward_code}-{room_num}-{bed_num}",
						"hospital_room": room_full,
						"is_active": 1,
					})
				beds_lookup[(w_idx, r_idx, b_idx)] = bed_full

	frappe.db.commit()
	return beds_lookup


# ── Patient and admission creation ──────────────────────────────────

def _create_patients_and_admissions(
	company: str,
	practitioners: dict,
	hsu_types: dict,
	beds: dict,
) -> tuple[list, list]:
	"""Create Patient + Inpatient Record for each scenario.

	Returns (patient_names, inpatient_record_names).
	"""
	patients = []
	ip_records = []
	now = now_datetime()

	for sc_idx, sc in enumerate(PATIENT_SCENARIOS):
		(first, last, sex, age, blood, w_idx, r_idx, b_idx,
		 diagnosis, dept_idx, days_admitted, payer_kind, priority,
		 expected_los, status) = sc

		dob = (now - timedelta(days=age * 365 + _RNG.randint(0, 180))).strftime("%Y-%m-%d")

		patient_name = frappe.db.get_value(
			"Patient",
			{"patient_name": f"{first} {last}", "sex": sex},
			"name",
		)
		if not patient_name:
			patient_name = _safe_insert({
				"doctype": "Patient",
				"first_name": first,
				"last_name": last,
				"sex": sex,
				"dob": dob,
				"blood_group": blood,
				"status": "Active",
				"custom_aadhaar_number": f"{_RNG.randint(100000000000, 999999999999)}",
				"custom_mr_number": f"MR-DEMO-{sc_idx + 1:04d}",
				"custom_emergency_contact_name": f"{_RNG.choice(['Spouse', 'Parent', 'Sibling'])} of {first}",
				"custom_emergency_contact_phone": f"+91 {_RNG.randint(7000000000, 9999999999)}",
				"custom_consent_collected": 1,
				"custom_consent_datetime": _ts(days_ago=days_admitted),
			})
		patients.append(patient_name)

		if not patient_name:
			ip_records.append(None)
			continue

		bed_key = (w_idx, r_idx, b_idx)
		bed_name = beds.get(bed_key)
		hsu_type_idx = WARD_LAYOUT[w_idx][3]
		hsu_type = hsu_types.get(hsu_type_idx)

		bed_hsu = None
		if bed_name:
			bed_hsu = frappe.db.get_value("Hospital Bed", bed_name, "healthcare_service_unit")

		admitted_dt = now - timedelta(days=days_admitted, hours=_RNG.randint(0, 12))
		dept_name = DEPARTMENTS[dept_idx]
		prac_name = practitioners.get(dept_idx) or practitioners.get(0)

		ip_status = "Admitted"
		discharged_dt = None
		if status == "discharged":
			ip_status = "Discharged"
			discharged_dt = now - timedelta(
				days=max(0, days_admitted - expected_los),
				hours=_RNG.randint(1, 8),
			)
			if discharged_dt > now:
				discharged_dt = now - timedelta(hours=_RNG.randint(4, 48))

		ir_doc_data = {
			"doctype": "Inpatient Record",
			"patient": patient_name,
			"company": company,
			"medical_department": dept_name,
			"primary_practitioner": prac_name,
			"status": ip_status,
			"scheduled_date": (admitted_dt - timedelta(hours=_RNG.randint(1, 24))).strftime("%Y-%m-%d"),
			"admitted_datetime": admitted_dt.strftime("%Y-%m-%d %H:%M:%S"),
			"expected_length_of_stay": expected_los,
			"admission_service_unit_type": hsu_type,
			"custom_admission_priority": priority,
			"custom_expected_los_days": expected_los,
			"custom_current_bed": bed_name if status == "active" else None,
			"custom_current_room": frappe.db.get_value("Hospital Bed", bed_name, "hospital_room") if bed_name else None,
			"custom_current_ward": frappe.db.get_value("Hospital Bed", bed_name, "hospital_ward") if bed_name else None,
			"custom_admission_notes": f"Admitted for {diagnosis}. {priority} priority.",
		}

		if bed_hsu:
			occ_rows = [{
				"service_unit": bed_hsu,
				"check_in": admitted_dt.strftime("%Y-%m-%d %H:%M:%S"),
			}]
			if status == "discharged" and discharged_dt:
				occ_rows[0]["check_out"] = discharged_dt.strftime("%Y-%m-%d %H:%M:%S")
				occ_rows[0]["left"] = 1
			ir_doc_data["inpatient_occupancy"] = occ_rows

		if status == "discharged" and discharged_dt:
			ir_doc_data["discharge_datetime"] = discharged_dt.strftime("%Y-%m-%d %H:%M:%S")

		ir_name = _safe_insert(ir_doc_data, ignore_links=True)
		ip_records.append(ir_name)

		if ir_name and bed_name and status == "active":
			frappe.db.set_value(
				"Hospital Bed", bed_name, "occupancy_status", "Occupied",
				update_modified=False,
			)

	frappe.db.commit()
	return patients, ip_records


# ── Clinical orders ─────────────────────────────────────────────────

def _create_clinical_orders(
	patients: list,
	ip_records: list,
	practitioners: dict,
	items: dict,
	beds: dict,
	company: str,
) -> list[dict]:
	"""Create IPD Clinical Orders for each active patient.

	Returns list of order metadata dicts for downstream MAR/dispense generation.
	"""
	all_orders = []
	now = now_datetime()

	for sc_idx, sc in enumerate(PATIENT_SCENARIOS):
		patient = patients[sc_idx]
		ir = ip_records[sc_idx]
		if not patient or not ir:
			continue

		(_, _, _, _, _, w_idx, r_idx, b_idx,
		 diagnosis, dept_idx, days_admitted, *_rest) = sc

		prac = practitioners.get(dept_idx) or practitioners.get(0)
		bed_name = beds.get((w_idx, r_idx, b_idx))
		ward_name = frappe.db.get_value("Hospital Bed", bed_name, "hospital_ward") if bed_name else None
		room_name = frappe.db.get_value("Hospital Bed", bed_name, "hospital_room") if bed_name else None

		num_med_orders = _RNG.randint(2, 5)
		med_choices = _RNG.sample(
			list(range(len(MEDICATIONS))),
			min(num_med_orders, len(MEDICATIONS)),
		)
		for med_idx in med_choices:
			med_name, route, freq, dose = MEDICATIONS[med_idx]
			item_code = items.get(med_name)
			ordered_at = now - timedelta(
				days=days_admitted, hours=_RNG.randint(0, 6),
			)
			order_status = _RNG.choice(["Active"] * 8 + ["Completed"] * 2)

			order_name = _safe_insert({
				"doctype": "IPD Clinical Order",
				"patient": patient,
				"inpatient_record": ir,
				"company": company,
				"order_type": "Medication",
				"urgency": _RNG.choice(["Routine"] * 6 + ["Urgent"] * 3 + ["STAT"]),
				"status": order_status,
				"medication_name": med_name,
				"medication_item": item_code,
				"dose": dose,
				"dose_uom": dose.split()[-1] if dose else "mg",
				"route": route,
				"frequency": freq,
				"ordered_by": "Administrator",
				"ordered_at": ordered_at.strftime("%Y-%m-%d %H:%M:%S"),
				"ordering_practitioner": prac,
				"hospital_ward": ward_name,
				"hospital_room": room_name,
				"hospital_bed": bed_name,
			}, ignore_links=True)

			if order_name:
				all_orders.append({
					"name": order_name,
					"type": "Medication",
					"patient": patient,
					"ir": ir,
					"med_name": med_name,
					"item_code": item_code,
					"dose": dose,
					"route": route,
					"freq": freq,
					"days": days_admitted,
					"ordered_at": ordered_at,
					"ward": ward_name,
					"bed": bed_name,
					"status": order_status,
				})

		num_lab_orders = _RNG.randint(1, 3)
		lab_choices = _RNG.sample(list(range(len(LAB_TESTS))), min(num_lab_orders, len(LAB_TESTS)))
		for lab_idx in lab_choices:
			lab_name = LAB_TESTS[lab_idx]
			ordered_at = now - timedelta(
				days=_RNG.randint(0, days_admitted),
				hours=_RNG.randint(0, 12),
			)
			order_name = _safe_insert({
				"doctype": "IPD Clinical Order",
				"patient": patient,
				"inpatient_record": ir,
				"company": company,
				"order_type": "Lab Test",
				"urgency": _RNG.choice(["Routine"] * 5 + ["Urgent"] * 3 + ["STAT"] * 2),
				"status": _RNG.choice(["Active", "Completed", "Completed"]),
				"lab_test_name": lab_name,
				"ordered_by": "Administrator",
				"ordered_at": ordered_at.strftime("%Y-%m-%d %H:%M:%S"),
				"ordering_practitioner": prac,
				"hospital_ward": ward_name,
				"hospital_room": room_name,
				"hospital_bed": bed_name,
			}, ignore_links=True)

			if order_name:
				all_orders.append({
					"name": order_name,
					"type": "Lab Test",
					"patient": patient,
					"ir": ir,
					"lab_name": lab_name,
					"days": days_admitted,
					"ordered_at": ordered_at,
					"ward": ward_name,
					"bed": bed_name,
				})

	frappe.db.commit()
	return all_orders


# ── MAR entries ─────────────────────────────────────────────────────

def _create_mar_entries(orders: list[dict]) -> None:
	"""Create MAR entries for medication orders — multiple doses per order."""
	now = now_datetime()
	for order in orders:
		if order["type"] != "Medication":
			continue
		freq = order.get("freq", "BD")
		interval = FREQ_MINUTES.get(freq, 720)
		if interval == 0:
			_safe_insert({
				"doctype": "IPD MAR Entry",
				"patient": order["patient"],
				"inpatient_record": order["ir"],
				"medication_name": order["med_name"],
				"medication_item": order.get("item_code"),
				"dose": order["dose"],
				"route": order["route"],
				"scheduled_time": order["ordered_at"].strftime("%Y-%m-%d %H:%M:%S"),
				"administration_status": "Given",
				"administered_at": (order["ordered_at"] + timedelta(minutes=_RNG.randint(5, 30))).strftime("%Y-%m-%d %H:%M:%S"),
				"administered_by": "Administrator",
				"shift": _get_shift(order["ordered_at"].hour),
				"clinical_order": order["name"],
				"ward": order.get("ward"),
				"bed": order.get("bed"),
			}, ignore_links=True)
			continue

		start = order["ordered_at"]
		num_doses = min(int((order["days"] * 1440) / interval), 20)
		for d in range(num_doses):
			sched_time = start + timedelta(minutes=interval * d)
			if sched_time > now:
				break
			status = _RNG.choice(MAR_STATUSES)
			admin_at = None
			delay_min = 0
			if status == "Given":
				admin_at = sched_time + timedelta(minutes=_RNG.randint(0, 15))
			elif status == "Delayed":
				delay_min = _RNG.randint(15, 60)
				admin_at = sched_time + timedelta(minutes=delay_min)
				status = "Delayed"

			doc_data = {
				"doctype": "IPD MAR Entry",
				"patient": order["patient"],
				"inpatient_record": order["ir"],
				"medication_name": order["med_name"],
				"medication_item": order.get("item_code"),
				"dose": order["dose"],
				"route": order["route"],
				"scheduled_time": sched_time.strftime("%Y-%m-%d %H:%M:%S"),
				"administration_status": status,
				"shift": _get_shift(sched_time.hour),
				"clinical_order": order["name"],
				"ward": order.get("ward"),
				"bed": order.get("bed"),
			}
			if admin_at:
				doc_data["administered_at"] = admin_at.strftime("%Y-%m-%d %H:%M:%S")
				doc_data["administered_by"] = "Administrator"
			if status == "Delayed":
				doc_data["delay_minutes"] = delay_min
				doc_data["delay_reason"] = _RNG.choice([
					"Patient was in radiology",
					"Medication not available on floor",
					"Patient was sleeping",
					"Nurse attending emergency",
				])
			elif status == "Held":
				doc_data["hold_reason"] = _RNG.choice([
					"NPO for procedure",
					"Low blood pressure",
					"Physician order to hold",
					"Patient nauseous",
				])
			elif status == "Missed":
				pass

			_safe_insert(doc_data, ignore_links=True)

	frappe.db.commit()


def _get_shift(hour: int) -> str:
	if 6 <= hour < 14:
		return "Morning"
	if 14 <= hour < 22:
		return "Afternoon"
	return "Night"


# ── Lab samples ─────────────────────────────────────────────────────

def _create_lab_samples(orders: list[dict]) -> None:
	"""Create IPD Lab Sample for each lab order."""
	for order in orders:
		if order["type"] != "Lab Test":
			continue
		collected = _RNG.random() > 0.2
		coll_status = "Collected" if collected else "Pending"
		sample_data = {
			"doctype": "IPD Lab Sample",
			"clinical_order": order["name"],
			"patient": order["patient"],
			"inpatient_record": order["ir"],
			"lab_test_name": order["lab_name"],
			"sample_type": _RNG.choice(["Blood", "Serum", "Urine", "Plasma"]),
			"collection_status": coll_status,
			"ward": order.get("ward"),
			"bed": order.get("bed"),
			"is_fasting_sample": 1 if "Fasting" in order["lab_name"] else 0,
		}
		if collected:
			coll_time = order["ordered_at"] + timedelta(minutes=_RNG.randint(15, 120))
			sample_data["collected_by"] = "Administrator"
			sample_data["collected_at"] = coll_time.strftime("%Y-%m-%d %H:%M:%S")
			sample_data["collection_site"] = _RNG.choice([
				"Left antecubital fossa", "Right antecubital fossa",
				"Left hand dorsum", "Right hand dorsum",
			])
			if _RNG.random() > 0.3:
				sample_data["status"] = "Handed Off"
				sample_data["handed_off_by"] = "Administrator"
				sample_data["handed_off_at"] = (coll_time + timedelta(minutes=_RNG.randint(5, 30))).strftime("%Y-%m-%d %H:%M:%S")
				sample_data["transport_mode"] = _RNG.choice(["Runner", "Pneumatic Tube", "Manual"])
		_safe_insert(sample_data, ignore_links=True)
	frappe.db.commit()


# ── Dispense entries ────────────────────────────────────────────────

def _create_dispense_entries(orders: list[dict]) -> None:
	"""Create IPD Dispense Entry for medication orders."""
	for order in orders:
		if order["type"] != "Medication" or order.get("status") != "Active":
			continue
		if _RNG.random() < 0.3:
			continue
		disp_time = order["ordered_at"] + timedelta(minutes=_RNG.randint(20, 90))
		_safe_insert({
			"doctype": "IPD Dispense Entry",
			"clinical_order": order["name"],
			"patient": order["patient"],
			"inpatient_record": order["ir"],
			"medication_name": order["med_name"],
			"medication_item": order.get("item_code"),
			"dose": order["dose"],
			"dispensed_qty": _RNG.randint(1, 10),
			"dispense_type": _RNG.choice(["Full"] * 3 + ["Partial"]),
			"dispensed_at": disp_time.strftime("%Y-%m-%d %H:%M:%S"),
			"dispensed_by": "Administrator",
			"ward": order.get("ward"),
			"bed": order.get("bed"),
		}, ignore_links=True)
	frappe.db.commit()


# ── Bedside charts and entries ──────────────────────────────────────

def _create_charting_data(patients: list, ip_records: list, beds: dict) -> None:
	"""Create IPD Bedside Charts and Chart Entries with observations."""
	now = now_datetime()

	vitals_template = frappe.db.get_value(
		"IPD Chart Template", {"template_name": "General Ward Vitals"}, "name"
	)
	icu_template = frappe.db.get_value(
		"IPD Chart Template", {"template_name": "ICU Comprehensive Vitals"}, "name"
	)

	for sc_idx, sc in enumerate(PATIENT_SCENARIOS):
		patient = patients[sc_idx]
		ir = ip_records[sc_idx]
		if not patient or not ir:
			continue

		(_, _, _, _, _, w_idx, r_idx, b_idx,
		 _, _, days_admitted, _, _, _, status) = sc

		if status == "discharged":
			continue

		bed_name = beds.get((w_idx, r_idx, b_idx))
		ward_name = frappe.db.get_value("Hospital Bed", bed_name, "hospital_ward") if bed_name else None

		is_icu = w_idx in (0, 1)
		template = icu_template if is_icu else vitals_template
		freq_min = 60 if is_icu else 240

		if not template:
			continue

		chart_name = _safe_insert({
			"doctype": "IPD Bedside Chart",
			"patient": patient,
			"inpatient_record": ir,
			"chart_template": template,
			"status": "Active",
			"frequency_minutes": freq_min,
			"started_at": _ts(days_ago=days_admitted),
			"started_by": "Administrator",
			"ward": ward_name,
			"bed": bed_name,
		}, ignore_links=True)

		if not chart_name:
			continue

		params = frappe.get_all(
			"IPD Chart Template Parameter",
			filters={"parent": template},
			fields=["parameter_name", "min_value", "max_value", "uom", "parameter_type"],
			order_by="display_order asc",
		)

		num_entries = min(int((days_admitted * 1440) / freq_min), 30)
		total_created = 0
		for e_idx in range(num_entries):
			entry_time = now - timedelta(
				days=days_admitted,
			) + timedelta(minutes=freq_min * e_idx)
			if entry_time > now:
				break

			missed = _RNG.random() < 0.08
			if missed:
				continue

			observations = []
			for p in params:
				if p.parameter_type in ("Numeric", None, ""):
					low = float(p.min_value or 30)
					high = float(p.max_value or 200)
					mid = (low + high) / 2
					spread = (high - low) * 0.3
					val = round(_RNG.gauss(mid, spread), 1)
					val = max(low * 0.8, min(high * 1.2, val))
					is_crit = val < low * 0.9 or val > high * 1.1
					observations.append({
						"parameter_name": p.parameter_name,
						"numeric_value": val,
						"uom": p.uom or "",
						"is_critical": 1 if is_crit else 0,
					})
				elif p.parameter_type == "Select":
					observations.append({
						"parameter_name": p.parameter_name,
						"select_value": _RNG.choice(["Normal", "Abnormal", "Not Assessed"]),
					})
				elif p.parameter_type == "Text":
					observations.append({
						"parameter_name": p.parameter_name,
						"text_value": _RNG.choice(["WNL", "Unremarkable", "See notes"]),
					})

			entry_name = _safe_insert({
				"doctype": "IPD Chart Entry",
				"bedside_chart": chart_name,
				"patient": patient,
				"inpatient_record": ir,
				"entry_datetime": entry_time.strftime("%Y-%m-%d %H:%M:%S"),
				"recorded_by": "Administrator",
				"observations": observations,
			}, ignore_links=True)
			if entry_name:
				total_created += 1

		if total_created:
			frappe.db.set_value(
				"IPD Bedside Chart", chart_name,
				{"total_entries": total_created, "missed_count": max(0, num_entries - total_created)},
				update_modified=False,
			)

	frappe.db.commit()


# ── Nursing notes ───────────────────────────────────────────────────

def _create_nursing_notes(patients: list, ip_records: list, beds: dict) -> None:
	now = now_datetime()
	for sc_idx, sc in enumerate(PATIENT_SCENARIOS):
		patient = patients[sc_idx]
		ir = ip_records[sc_idx]
		if not patient or not ir:
			continue
		days_admitted = sc[10]
		bed_name = beds.get((sc[5], sc[6], sc[7]))
		ward = frappe.db.get_value("Hospital Bed", bed_name, "hospital_ward") if bed_name else None

		num_notes = _RNG.randint(2, 5)
		for n in range(num_notes):
			cat, text = _RNG.choice(NURSING_NOTE_TEMPLATES)
			note_dt = now - timedelta(
				days=_RNG.randint(0, days_admitted),
				hours=_RNG.randint(0, 23),
			)
			_safe_insert({
				"doctype": "IPD Nursing Note",
				"patient": patient,
				"inpatient_record": ir,
				"note_datetime": note_dt.strftime("%Y-%m-%d %H:%M:%S"),
				"category": cat,
				"urgency": _RNG.choice(["Routine"] * 8 + ["Urgent"] * 2),
				"note_text": f"<p>{text}</p>",
				"recorded_by": "Administrator",
				"ward": ward,
				"bed": bed_name,
			}, ignore_links=True)
	frappe.db.commit()


# ── IO entries ──────────────────────────────────────────────────────

def _create_io_entries(patients: list, ip_records: list, beds: dict) -> None:
	"""Create IO entries for ICU/HDU patients."""
	now = now_datetime()
	for sc_idx, sc in enumerate(PATIENT_SCENARIOS):
		w_idx = sc[5]
		if w_idx > 1:
			continue
		patient = patients[sc_idx]
		ir = ip_records[sc_idx]
		if not patient or not ir:
			continue
		days_admitted = sc[10]
		bed_name = beds.get((w_idx, sc[6], sc[7]))
		ward = frappe.db.get_value("Hospital Bed", bed_name, "hospital_ward") if bed_name else None

		num_entries = _RNG.randint(4, 8)
		for _ in range(num_entries):
			io = _RNG.choice(IO_TEMPLATES)
			io_type, fluid_cat, fluid_name, route, base_vol = io
			vol = base_vol + _RNG.randint(-50, 100)
			entry_dt = now - timedelta(
				days=_RNG.randint(0, days_admitted),
				hours=_RNG.randint(0, 23),
			)
			_safe_insert({
				"doctype": "IPD IO Entry",
				"patient": patient,
				"inpatient_record": ir,
				"entry_datetime": entry_dt.strftime("%Y-%m-%d %H:%M:%S"),
				"io_type": io_type,
				"fluid_category": fluid_cat,
				"fluid_name": fluid_name,
				"route": route,
				"volume_ml": max(10, vol),
				"recorded_by": "Administrator",
				"ward": ward,
				"bed": bed_name,
			}, ignore_links=True)
	frappe.db.commit()


# ── Problem list ────────────────────────────────────────────────────

def _create_problem_list(patients: list, ip_records: list, practitioners: dict, company: str) -> None:
	for sc_idx, sc in enumerate(PATIENT_SCENARIOS):
		patient = patients[sc_idx]
		ir = ip_records[sc_idx]
		if not patient or not ir:
			continue
		dept_idx = sc[9]
		days_admitted = sc[10]
		prac = practitioners.get(dept_idx)

		desc, icd, severity = sc[8], "", "Moderate"
		matching = [p for p in PROBLEM_TEMPLATES if p[0].lower() in desc.lower()]
		if matching:
			desc, icd, severity = matching[0]

		_safe_insert({
			"doctype": "IPD Problem List Item",
			"patient": patient,
			"inpatient_record": ir,
			"company": company,
			"problem_description": desc,
			"icd_code": icd,
			"severity": severity,
			"status": "Active",
			"onset_date": _date(days_admitted),
			"added_by": prac,
			"added_on": _ts(days_ago=days_admitted),
		}, ignore_links=True)

		if _RNG.random() > 0.5:
			extra = _RNG.choice(PROBLEM_TEMPLATES)
			_safe_insert({
				"doctype": "IPD Problem List Item",
				"patient": patient,
				"inpatient_record": ir,
				"company": company,
				"problem_description": extra[0],
				"icd_code": extra[1],
				"severity": extra[2],
				"status": _RNG.choice(["Active", "Monitoring"]),
				"onset_date": _date(_RNG.randint(0, days_admitted)),
				"added_by": prac,
				"added_on": _ts(days_ago=_RNG.randint(0, days_admitted)),
			}, ignore_links=True)

	frappe.db.commit()


# ── Admission checklists ───────────────────────────────────────────

def _create_admission_checklists(patients: list, ip_records: list, company: str) -> None:
	template = frappe.db.get_value("Admission Checklist Template", {}, "name")

	for sc_idx, sc in enumerate(PATIENT_SCENARIOS):
		patient = patients[sc_idx]
		ir = ip_records[sc_idx]
		if not patient or not ir:
			continue
		days_admitted = sc[10]
		if days_admitted < 1:
			continue
		if _RNG.random() > 0.7 and sc_idx > 10:
			continue

		entries = []
		all_done = True
		for label, category, mandatory in CHECKLIST_ITEMS:
			done = _RNG.random() > 0.15
			if not done:
				all_done = False
			entries.append({
				"item_label": label,
				"category": category,
				"is_mandatory": 1 if mandatory else 0,
				"status": "Completed" if done else "Pending",
				"completed_by": "Administrator" if done else None,
				"completed_on": _ts(days_ago=days_admitted - 0.5) if done else None,
			})

		checklist_name = _safe_insert({
			"doctype": "Admission Checklist",
			"inpatient_record": ir,
			"patient": patient,
			"template_used": template,
			"status": "Complete" if all_done else "Incomplete",
			"company": company,
			"checklist_entries": entries,
			"completed_by": "Administrator" if all_done else None,
			"completed_on": _ts(days_ago=days_admitted - 0.5) if all_done else None,
		}, ignore_links=True)

		if checklist_name:
			frappe.db.set_value(
				"Inpatient Record", ir,
				"custom_admission_checklist", checklist_name,
				update_modified=False,
			)

	frappe.db.commit()


# ── Payer profiles and eligibility ──────────────────────────────────

def _create_payer_data(
	patients: list,
	ip_records: list,
	company: str,
	customers: dict,
) -> None:
	"""Create Patient Payer Profiles and Payer Eligibility Checks."""
	ins_companies = [c for c, t in PAYER_COMPANIES if t == "Insurance TPA"]
	corp_companies = [c for c, t in PAYER_COMPANIES if t == "Corporate"]

	for sc_idx, sc in enumerate(PATIENT_SCENARIOS):
		patient = patients[sc_idx]
		ir = ip_records[sc_idx]
		if not patient or not ir:
			continue
		payer_kind = sc[11]
		days_admitted = sc[10]

		if payer_kind == "Cash":
			pp_name = _safe_insert({
				"doctype": "Patient Payer Profile",
				"patient": patient,
				"payer_type": "Cash",
				"company": company,
				"valid_from": _date(days_admitted + 30),
				"is_active": 1,
			}, ignore_links=True)
		elif payer_kind == "Insurance":
			payer_company = _RNG.choice(ins_companies)
			customer = customers.get(payer_company)
			pp_name = _safe_insert({
				"doctype": "Patient Payer Profile",
				"patient": patient,
				"payer_type": "Insurance TPA",
				"company": company,
				"payer": customer,
				"valid_from": _date(days_admitted + 365),
				"valid_to": _date(-365 + days_admitted),
				"sum_insured": _RNG.choice([300000, 500000, 1000000, 2000000]),
				"balance_available": _RNG.randint(100000, 1500000),
				"room_category_entitlement": _RNG.choice(["General", "Semi-Private", "Private"]),
				"preauth_required": 1,
				"co_pay_percent": _RNG.choice([0, 10, 20]),
				"policy_number": f"POL-{_RNG.randint(100000, 999999)}",
				"member_id": f"MEM-{_RNG.randint(10000, 99999)}",
				"is_active": 1,
			}, ignore_links=True)
		else:
			payer_company = _RNG.choice(corp_companies)
			customer = customers.get(payer_company)
			pp_name = _safe_insert({
				"doctype": "Patient Payer Profile",
				"patient": patient,
				"payer_type": "Corporate",
				"company": company,
				"payer": customer,
				"valid_from": _date(days_admitted + 365),
				"is_active": 1,
				"employer_name": payer_company,
			}, ignore_links=True)

		if pp_name:
			frappe.db.set_value(
				"Inpatient Record", ir,
				"custom_patient_payer_profile", pp_name,
				update_modified=False,
			)

		if pp_name and payer_kind != "Cash":
			_safe_insert({
				"doctype": "Payer Eligibility Check",
				"patient": patient,
				"patient_payer_profile": pp_name,
				"inpatient_record": ir,
				"company": company,
				"verification_status": _RNG.choice(["Verified"] * 8 + ["Pending"] * 2),
				"verified_by": "Administrator",
				"verified_on": _ts(days_ago=days_admitted),
				"approved_amount": _RNG.randint(100000, 1000000),
				"approved_room_category": _RNG.choice(["General", "Semi-Private", "Private"]),
				"approved_duration_days": _RNG.randint(5, 14),
			}, ignore_links=True)

	frappe.db.commit()


# ── TPA preauth requests ───────────────────────────────────────────

def _create_preauth_requests(
	patients: list,
	ip_records: list,
	practitioners: dict,
	company: str,
) -> None:
	for sc_idx, sc in enumerate(PATIENT_SCENARIOS):
		patient = patients[sc_idx]
		ir = ip_records[sc_idx]
		if not patient or not ir or sc[11] != "Insurance":
			continue

		payer_profile = frappe.db.get_value(
			"Patient Payer Profile", {"patient": patient, "payer_type": "Insurance TPA"}, "name"
		)
		if not payer_profile:
			continue

		days_admitted = sc[10]
		diagnosis = sc[8]
		dept_idx = sc[9]
		prac = practitioners.get(dept_idx)

		preauth_status = _RNG.choice(["Approved"] * 6 + ["Pending"] * 2 + ["Partially Approved"] * 2)
		requested_amt = _RNG.choice([100000, 200000, 300000, 500000])
		approved_amt = requested_amt if preauth_status == "Approved" else int(requested_amt * _RNG.uniform(0.5, 0.9))

		preauth_name = _safe_insert({
			"doctype": "TPA Preauth Request",
			"patient": patient,
			"inpatient_record": ir,
			"patient_payer_profile": payer_profile,
			"company": company,
			"primary_diagnosis": diagnosis,
			"treating_practitioner": prac,
			"department": DEPARTMENTS[dept_idx],
			"admission_type": sc[12] if sc[12] in ("Emergency", "Planned") else "Planned",
			"estimated_cost": requested_amt * 1.2,
			"requested_amount": requested_amt,
			"approved_amount": approved_amt if preauth_status != "Pending" else 0,
			"expected_los_days": sc[13],
			"status": preauth_status,
			"preauth_reference_number": f"PA-{_RNG.randint(10000, 99999)}" if preauth_status != "Pending" else "",
			"valid_from": _date(days_admitted) if preauth_status != "Pending" else None,
			"valid_to": _date(-30) if preauth_status != "Pending" else None,
			"responses": [{
				"response_type": "Response",
				"response_text": f"<p>Pre-authorization {'approved' if preauth_status == 'Approved' else 'under review'} for {diagnosis}.</p>",
				"response_by": "Administrator",
				"response_datetime": _ts(days_ago=days_admitted - 0.5),
			}],
		}, ignore_links=True)

		if preauth_name and ir:
			frappe.db.set_value(
				"Inpatient Record", ir,
				"custom_preauth_request", preauth_name,
				update_modified=False,
			)

	frappe.db.commit()


# ── Protocol bundles ────────────────────────────────────────────────

def _create_protocol_bundles(patients: list, ip_records: list) -> None:
	"""Activate protocol bundles for ICU/HDU patients."""
	protocol_names = frappe.get_all(
		"Monitoring Protocol Bundle",
		filters={"is_active": 1},
		pluck="name",
		limit=5,
	)
	if not protocol_names:
		return

	for sc_idx, sc in enumerate(PATIENT_SCENARIOS):
		w_idx = sc[5]
		if w_idx > 1:
			continue
		patient = patients[sc_idx]
		ir = ip_records[sc_idx]
		if not patient or not ir or sc[14] == "discharged":
			continue

		days_admitted = sc[10]
		proto = _RNG.choice(protocol_names)

		steps = frappe.get_all(
			"Protocol Bundle Step",
			filters={"parent": proto},
			fields=["step_name", "step_type", "sequence", "is_mandatory"],
			order_by="sequence asc",
		)

		trackers = []
		compliance_total = 0
		compliance_done = 0
		for step in steps:
			completed = _RNG.random() > 0.2
			compliance_total += 1
			if completed:
				compliance_done += 1
			trackers.append({
				"step_name": step.step_name,
				"step_type": step.step_type,
				"sequence": step.sequence,
				"is_mandatory": step.is_mandatory,
				"status": "Completed" if completed else _RNG.choice(["Pending", "Due", "Missed"]),
				"due_at": _ts(days_ago=_RNG.randint(0, days_admitted)),
				"completed_at": _ts(days_ago=_RNG.randint(0, days_admitted)) if completed else None,
				"completed_by": "Administrator" if completed else None,
			})

		score = round((compliance_done / compliance_total) * 100, 1) if compliance_total else 0

		_safe_insert({
			"doctype": "Active Protocol Bundle",
			"protocol_bundle": proto,
			"patient": patient,
			"inpatient_record": ir,
			"status": "Active",
			"compliance_score": score,
			"activated_at": _ts(days_ago=days_admitted),
			"activated_by": "Administrator",
			"step_trackers": trackers,
		}, ignore_links=True)

	frappe.db.commit()


# ── Bed movement logs & housekeeping ────────────────────────────────

def _create_operational_data(
	patients: list,
	ip_records: list,
	beds: dict,
	company: str,
) -> None:
	"""Create Bed Movement Logs and Bed Housekeeping Tasks."""
	for sc_idx, sc in enumerate(PATIENT_SCENARIOS):
		patient = patients[sc_idx]
		ir = ip_records[sc_idx]
		if not patient or not ir:
			continue

		bed_name = beds.get((sc[5], sc[6], sc[7]))
		ward = frappe.db.get_value("Hospital Bed", bed_name, "hospital_ward") if bed_name else None
		room = frappe.db.get_value("Hospital Bed", bed_name, "hospital_room") if bed_name else None
		days_admitted = sc[10]
		status = sc[14]

		hsu = frappe.db.get_value("Hospital Bed", bed_name, "healthcare_service_unit") if bed_name else None

		_safe_insert({
			"doctype": "Bed Movement Log",
			"movement_type": "Admission",
			"movement_datetime": _ts(days_ago=days_admitted),
			"inpatient_record": ir,
			"patient": patient,
			"to_bed": bed_name,
			"to_room": room,
			"to_ward": ward,
			"to_service_unit": hsu,
			"performed_by": "Administrator",
			"performed_on": _ts(days_ago=days_admitted),
			"company": company,
		}, ignore_links=True)

		if status == "discharged":
			discharge_days = max(0, days_admitted - sc[13])
			_safe_insert({
				"doctype": "Bed Movement Log",
				"movement_type": "Discharge",
				"movement_datetime": _ts(days_ago=discharge_days),
				"inpatient_record": ir,
				"patient": patient,
				"from_bed": bed_name,
				"from_room": room,
				"from_ward": ward,
				"from_service_unit": hsu,
				"source_bed_action": "Mark Dirty",
				"performed_by": "Administrator",
				"performed_on": _ts(days_ago=discharge_days),
				"company": company,
			}, ignore_links=True)

			hk_completed = _RNG.random() > 0.3
			_safe_insert({
				"doctype": "Bed Housekeeping Task",
				"hospital_bed": bed_name,
				"status": "Completed" if hk_completed else "Pending",
				"trigger_event": "Discharge",
				"inpatient_record": ir,
				"cleaning_type": _RNG.choice(["Standard"] * 3 + ["Deep Clean"]),
				"created_on": _ts(days_ago=discharge_days),
				"started_on": _ts(days_ago=discharge_days, hours_ago=-0.5) if hk_completed else None,
				"completed_on": _ts(days_ago=discharge_days, hours_ago=-1) if hk_completed else None,
				"sla_target_minutes": 60,
				"sla_breached": 0 if hk_completed else (1 if _RNG.random() > 0.5 else 0),
				"turnaround_minutes": _RNG.randint(30, 90) if hk_completed else 0,
				"assigned_to": "Administrator",
				"started_by": "Administrator" if hk_completed else None,
				"completed_by": "Administrator" if hk_completed else None,
			}, ignore_links=True)

	frappe.db.commit()


# ── Discharge flow ──────────────────────────────────────────────────

def _create_discharge_data(
	patients: list,
	ip_records: list,
	practitioners: dict,
	company: str,
) -> None:
	"""Create discharge advice, billing & nursing checklists for discharged patients."""
	for sc_idx, sc in enumerate(PATIENT_SCENARIOS):
		if sc[14] != "discharged":
			continue
		patient = patients[sc_idx]
		ir = ip_records[sc_idx]
		if not patient or not ir:
			continue

		days_admitted = sc[10]
		dept_idx = sc[9]
		prac = practitioners.get(dept_idx)
		diagnosis = sc[8]
		discharge_days = max(0, days_admitted - sc[13])

		advice_name = _safe_insert({
			"doctype": "IPD Discharge Advice",
			"inpatient_record": ir,
			"patient": patient,
			"consultant": prac,
			"company": company,
			"status": "Completed",
			"expected_discharge_datetime": _ts(days_ago=discharge_days, hours_ago=2),
			"actual_discharge_datetime": _ts(days_ago=discharge_days),
			"discharge_type": "Normal",
			"condition_at_discharge": _RNG.choice(["Improved", "Unchanged"]),
			"primary_diagnosis": diagnosis,
			"discharge_medications": "<p>Continue prescribed medications as per discharge summary.</p>",
			"follow_up_instructions": "<p>Review in OPD after 7 days. Report to ER if symptoms worsen.</p>",
			"follow_up_date": _date(-7),
			"follow_up_practitioner": prac,
			"diet_instructions": "<p>Normal diet. Avoid spicy food for 1 week.</p>",
			"warning_signs": "<p>High fever, breathlessness, severe pain, bleeding.</p>",
			"advised_by": "Administrator",
			"advised_on": _ts(days_ago=discharge_days, hours_ago=4),
		}, ignore_links=True)

		billing_items = [
			("All charges posted", "Financial", "Cleared"),
			("Outstanding balance settled", "Financial",
			 _RNG.choice(["Cleared"] * 4 + ["Pending"])),
			("TPA claim pack prepared", "TPA",
			 "Cleared" if sc[11] == "Insurance" else "Not Applicable"),
			("Final bill reviewed by doctor", "Clinical", "Cleared"),
			("Pharmacy returns processed", "Administrative", "Cleared"),
			("Diet charges reconciled", "Financial", "Cleared"),
		]
		dbc_name = _safe_insert({
			"doctype": "Discharge Billing Checklist",
			"inpatient_record": ir,
			"patient": patient,
			"company": company,
			"status": "Cleared",
			"items": [{
				"check_name": name,
				"check_category": cat,
				"check_status": st,
				"cleared_by": "Administrator" if st == "Cleared" else None,
				"cleared_on": _ts(days_ago=discharge_days) if st == "Cleared" else None,
			} for name, cat, st in billing_items],
		}, ignore_links=True)

		nursing_items = [
			("IV cannula removed", "Line Removal", True),
			("Foley catheter removed", "Line Removal", False),
			("Discharge medications explained", "Medication", True),
			("Wound care instructions given", "Patient Education", False),
			("Follow-up appointment confirmed", "Other", True),
			("Patient belongings returned", "Other", True),
		]
		ndc_name = _safe_insert({
			"doctype": "Nursing Discharge Checklist",
			"inpatient_record": ir,
			"patient": patient,
			"discharge_advice": advice_name,
			"status": "Completed",
			"items": [{
				"item_name": name,
				"item_category": cat,
				"is_mandatory": 1 if mandatory else 0,
				"item_status": "Done",
				"completed_by": "Administrator",
				"completed_on": _ts(days_ago=discharge_days),
			} for name, cat, mandatory in nursing_items],
			"handover_notes": "<p>Patient discharged in stable condition. All lines removed. Medications and instructions explained.</p>",
			"completed_by": "Administrator",
			"completed_on": _ts(days_ago=discharge_days),
		}, ignore_links=True)

		if advice_name:
			frappe.db.set_value(
				"Inpatient Record", ir,
				"custom_discharge_advice", advice_name,
				update_modified=False,
			)
		if dbc_name:
			frappe.db.set_value(
				"Inpatient Record", ir,
				"custom_discharge_checklist", dbc_name,
				update_modified=False,
			)
		if ndc_name:
			frappe.db.set_value(
				"Inpatient Record", ir,
				"custom_nursing_discharge_checklist", ndc_name,
				update_modified=False,
			)

	frappe.db.commit()


# ── TPA Claim Packs ────────────────────────────────────────────────

def _create_claim_packs(patients: list, ip_records: list, company: str) -> None:
	for sc_idx, sc in enumerate(PATIENT_SCENARIOS):
		if sc[14] != "discharged" or sc[11] != "Insurance":
			continue
		patient = patients[sc_idx]
		ir = ip_records[sc_idx]
		if not patient or not ir:
			continue

		payer_profile = frappe.db.get_value(
			"Patient Payer Profile", {"patient": patient}, "name"
		)
		preauth = frappe.db.get_value(
			"TPA Preauth Request", {"inpatient_record": ir}, "name"
		)
		discharge_days = max(0, sc[10] - sc[13])

		_safe_insert({
			"doctype": "TPA Claim Pack",
			"inpatient_record": ir,
			"patient": patient,
			"patient_payer_profile": payer_profile,
			"company": company,
			"tpa_preauth_request": preauth,
			"status": _RNG.choice(["Submitted", "In Review"]),
			"submission_date": _date(discharge_days),
			"submission_reference": f"CLM-{_RNG.randint(10000, 99999)}",
			"submission_mode": "Online",
			"documents": [
				{"document_type": "Final Bill", "is_mandatory": 1, "is_available": 1, "description": "Final hospital bill"},
				{"document_type": "Discharge Summary", "is_mandatory": 1, "is_available": 1, "description": "Discharge summary report"},
				{"document_type": "Investigation Reports", "is_mandatory": 1, "is_available": 1, "description": "All lab and imaging reports"},
				{"document_type": "Bill Break-Up", "is_mandatory": 0, "is_available": 1, "description": "Itemized billing"},
				{"document_type": "Pre-Auth Copy", "is_mandatory": 0, "is_available": 1 if preauth else 0, "description": "Pre-authorization letter"},
			],
		}, ignore_links=True)

	frappe.db.commit()


# ── SLA configs ─────────────────────────────────────────────────────

def _create_sla_configs() -> None:
	"""Create IPD Order SLA Config entries."""
	configs = [
		("Medication", "Routine", [("Acknowledged", 30), ("Dispensed", 60), ("Administered", 120)]),
		("Medication", "Urgent", [("Acknowledged", 15), ("Dispensed", 30), ("Administered", 60)]),
		("Medication", "STAT", [("Acknowledged", 5), ("Dispensed", 15), ("Administered", 30)]),
		("Lab Test", "Routine", [("Acknowledged", 30), ("Sample Collected", 60), ("Result Available", 240)]),
		("Lab Test", "Urgent", [("Acknowledged", 15), ("Sample Collected", 30), ("Result Available", 120)]),
		("Lab Test", "STAT", [("Acknowledged", 5), ("Sample Collected", 15), ("Result Available", 60)]),
		("Procedure", "Routine", [("Acknowledged", 30), ("Scheduled", 120), ("Completed", 480)]),
		("Procedure", "Urgent", [("Acknowledged", 15), ("Scheduled", 60), ("Completed", 240)]),
	]

	for order_type, urgency, milestones in configs:
		existing = frappe.db.get_value(
			"IPD Order SLA Config",
			{"order_type": order_type, "urgency": urgency},
			"name",
		)
		if existing:
			continue
		_safe_insert({
			"doctype": "IPD Order SLA Config",
			"order_type": order_type,
			"urgency": urgency,
			"is_active": 1,
			"milestones": [
				{"milestone": m, "sequence": idx + 1, "target_minutes": mins}
				for idx, (m, mins) in enumerate(milestones)
			],
		})
	frappe.db.commit()


# ── Room tariff mappings ────────────────────────────────────────────

def _create_room_tariffs(hsu_types: dict, company: str, customers: dict) -> None:
	"""Create Room Tariff Mappings for different payer types."""
	price_list = frappe.db.get_value("Price List", {"selling": 1}, "name")
	if not price_list:
		return

	room_items = {}
	for type_name in ["General Ward", "Private Room", "Semi-Private Room", "ICU Bay", "HDU Bay"]:
		code = f"DEMO-ROOM-{type_name.replace(' ', '-').upper()}"
		if not frappe.db.exists("Item", code):
			_safe_insert({
				"doctype": "Item",
				"item_code": code,
				"item_name": f"{type_name} - Room Rent",
				"item_group": "Services",
				"stock_uom": "Nos",
				"is_stock_item": 0,
			})
		room_items[type_name] = code

	tariff_rates = {
		"General Ward": 1500,
		"Semi-Private Room": 3000,
		"Private Room": 6000,
		"ICU Bay": 8000,
		"HDU Bay": 5000,
	}

	for type_idx, type_name in hsu_types.items():
		hsu_type_display = HSU_TYPES[type_idx][0]
		rate = tariff_rates.get(hsu_type_display, 2000)
		item_code = room_items.get(hsu_type_display)
		if not item_code:
			continue

		existing = frappe.db.get_value(
			"Room Tariff Mapping",
			{"room_type": type_name, "payer_type": "Cash", "company": company},
			"name",
		)
		if existing:
			continue

		_safe_insert({
			"doctype": "Room Tariff Mapping",
			"room_type": type_name,
			"company": company,
			"payer_type": "Cash",
			"valid_from": _date(365),
			"price_list": price_list,
			"is_active": 1,
			"tariff_items": [{
				"charge_type": "Room Rent",
				"item_code": item_code,
				"rate": rate,
				"uom": "Nos",
				"billing_frequency": "Per Day",
			}],
		}, ignore_links=True)

	frappe.db.commit()


# ── Billing rule sets ──────────────────────────────────────────────

def _create_billing_rules(company: str, customers: dict) -> None:
	for cust_name, payer_type in PAYER_COMPANIES[:2]:
		customer = customers.get(cust_name)
		if not customer:
			continue
		existing = frappe.db.get_value(
			"Payer Billing Rule Set",
			{"payer": customer, "company": company},
			"name",
		)
		if existing:
			continue

		_safe_insert({
			"doctype": "Payer Billing Rule Set",
			"rule_set_name": f"{cust_name} - Standard Rules",
			"company": company,
			"payer_type": payer_type,
			"payer": customer,
			"valid_from": _date(365),
			"is_active": 1,
			"rules": [
				{
					"rule_type": "Co-Pay Override",
					"applies_to": "Charge Category",
					"charge_category": "Room Rent",
					"co_pay_percent": 10,
				},
				{
					"rule_type": "Room Rent Cap",
					"applies_to": "Charge Category",
					"charge_category": "Room Rent",
					"cap_amount": 5000,
				},
			],
		}, ignore_links=True)

	frappe.db.commit()


# ── Bed reservations ───────────────────────────────────────────────

def _create_bed_reservations(beds: dict, company: str) -> None:
	"""Create a few active and expired bed reservations."""
	vacant_beds = []
	for key, bed_name in beds.items():
		occ = frappe.db.get_value("Hospital Bed", bed_name, "occupancy_status")
		if occ == "Vacant":
			vacant_beds.append((key, bed_name))

	for i, (key, bed_name) in enumerate(vacant_beds[:3]):
		room = frappe.db.get_value("Hospital Bed", bed_name, "hospital_room")
		ward = frappe.db.get_value("Hospital Bed", bed_name, "hospital_ward")
		status = "Active" if i == 0 else "Expired"

		_safe_insert({
			"doctype": "Bed Reservation",
			"reservation_type": "Specific Bed",
			"status": status,
			"company": company,
			"hospital_bed": bed_name,
			"hospital_room": room,
			"hospital_ward": ward,
			"reservation_start": _ts(hours_ago=_RNG.randint(1, 48)),
			"timeout_minutes": 120,
			"notes": f"Demo reservation #{i + 1}",
			"reserved_by": "Administrator",
			"reserved_on": _ts(hours_ago=_RNG.randint(1, 48)),
		}, ignore_links=True)

	frappe.db.commit()


# ── IPD Bed Policy defaults ────────────────────────────────────────

def _set_bed_policy_defaults() -> None:
	"""Ensure the singleton IPD Bed Policy has sensible values."""
	try:
		doc = frappe.get_doc("IPD Bed Policy")
		doc.flags.ignore_permissions = True
		doc.save()
	except Exception:
		pass


# ══════════════════════════════════════════════════════════════════
#  ENTRY POINTS
# ══════════════════════════════════════════════════════════════════

@frappe.whitelist()
def generate_demo_data() -> dict:
	"""Generate comprehensive demo data for the IPD module.

	Creates patients, admissions, clinical orders, charting, nursing,
	payer/billing, protocols, and discharge data for demonstration.
	"""
	global _records
	_records = {}

	existing = frappe.cache().get_value(DEMO_DATA_KEY)
	if existing:
		frappe.throw(
			_("Demo data already exists. Please clear it before generating new data."),
			exc=frappe.ValidationError,
		)

	frappe.flags.mute_emails = True
	frappe.flags.mute_notifications = True

	_RNG.seed(42)

	company = _get_company()

	frappe.publish_progress(5, title=_("Generating Demo Data"), description=_("Creating master data..."))
	departments = _create_departments()
	practitioners = _create_practitioners(company)
	items = _create_items()
	hsu_types = _create_hsu_types()
	customers = _create_customers()
	_create_sla_configs()

	frappe.publish_progress(15, title=_("Generating Demo Data"), description=_("Building hospital infrastructure..."))
	root_hsu = _get_or_create_root_hsu(company)
	beds = _create_infrastructure(company, root_hsu, hsu_types)

	frappe.publish_progress(25, title=_("Generating Demo Data"), description=_("Creating patients and admissions..."))
	patients, ip_records = _create_patients_and_admissions(
		company, practitioners, hsu_types, beds,
	)

	frappe.publish_progress(35, title=_("Generating Demo Data"), description=_("Creating admission checklists..."))
	_create_admission_checklists(patients, ip_records, company)

	frappe.publish_progress(40, title=_("Generating Demo Data"), description=_("Creating clinical orders..."))
	orders = _create_clinical_orders(patients, ip_records, practitioners, items, beds, company)

	frappe.publish_progress(50, title=_("Generating Demo Data"), description=_("Creating MAR entries..."))
	_create_mar_entries(orders)

	frappe.publish_progress(60, title=_("Generating Demo Data"), description=_("Creating lab samples and dispense entries..."))
	_create_lab_samples(orders)
	_create_dispense_entries(orders)

	frappe.publish_progress(70, title=_("Generating Demo Data"), description=_("Creating bedside charts..."))
	_create_charting_data(patients, ip_records, beds)

	frappe.publish_progress(75, title=_("Generating Demo Data"), description=_("Creating nursing notes and IO entries..."))
	_create_nursing_notes(patients, ip_records, beds)
	_create_io_entries(patients, ip_records, beds)
	_create_problem_list(patients, ip_records, practitioners, company)

	frappe.publish_progress(80, title=_("Generating Demo Data"), description=_("Creating payer and billing data..."))
	_create_payer_data(patients, ip_records, company, customers)
	_create_preauth_requests(patients, ip_records, practitioners, company)

	frappe.publish_progress(85, title=_("Generating Demo Data"), description=_("Creating protocol bundles..."))
	_create_protocol_bundles(patients, ip_records)

	frappe.publish_progress(90, title=_("Generating Demo Data"), description=_("Creating operational data..."))
	_create_operational_data(patients, ip_records, beds, company)
	_create_bed_reservations(beds, company)
	_create_room_tariffs(hsu_types, company, customers)
	_create_billing_rules(company, customers)

	frappe.publish_progress(95, title=_("Generating Demo Data"), description=_("Creating discharge data..."))
	_create_discharge_data(patients, ip_records, practitioners, company)
	_create_claim_packs(patients, ip_records, company)

	_set_bed_policy_defaults()

	frappe.cache().set_value(DEMO_DATA_KEY, json.dumps(_records))
	frappe.db.commit()

	frappe.flags.mute_emails = False
	frappe.flags.mute_notifications = False

	total = sum(len(v) for v in _records.values())
	frappe.publish_progress(100, title=_("Generating Demo Data"), description=_("Done!"))

	return {
		"message": f"Demo data generated successfully: {total} records across {len(_records)} doctypes.",
		"summary": {dt: len(names) for dt, names in _records.items()},
	}


@frappe.whitelist()
def clear_demo_data() -> dict:
	"""Remove all demo data created by generate_demo_data."""
	cached = frappe.cache().get_value(DEMO_DATA_KEY)
	if not cached:
		frappe.throw(
			_("No demo data tracking found. Nothing to clear."),
			exc=frappe.ValidationError,
		)

	records: dict[str, list[str]] = json.loads(cached)

	deletion_order = [
		"TPA Claim Pack",
		"Nursing Discharge Checklist",
		"Discharge Billing Checklist",
		"IPD Discharge Advice",
		"Active Protocol Bundle",
		"Bed Reservation",
		"Bed Housekeeping Task",
		"Bed Movement Log",
		"Payer Eligibility Check",
		"TPA Preauth Request",
		"Payer Billing Rule Set",
		"Room Tariff Mapping",
		"Patient Payer Profile",
		"IPD Chart Entry",
		"IPD Bedside Chart",
		"IPD IO Entry",
		"IPD Nursing Note",
		"IPD Problem List Item",
		"IPD Dispense Entry",
		"IPD Lab Sample",
		"IPD MAR Entry",
		"IPD Clinical Order",
		"Admission Checklist",
		"Inpatient Record",
		"Patient",
		"Hospital Bed",
		"Hospital Room",
		"Hospital Ward",
		"Healthcare Service Unit",
		"Healthcare Practitioner",
		"Medical Department",
		"Item",
		"Item Group",
		"Customer",
		"IPD Order SLA Config",
	]

	deleted = 0
	total_records = sum(len(v) for v in records.values())

	frappe.flags.mute_emails = True
	frappe.flags.mute_notifications = True

	for doctype in deletion_order:
		names = records.get(doctype, [])
		for name in names:
			try:
				if frappe.db.exists(doctype, name):
					frappe.delete_doc(
						doctype, name,
						force=True,
						ignore_permissions=True,
						delete_permanently=True,
					)
					deleted += 1
			except Exception as e:
				frappe.log_error(
					f"Demo data cleanup: failed to delete {doctype}/{name}: {e}",
					"Demo Data Cleanup",
				)

		if names:
			frappe.db.commit()

	remaining = [dt for dt in records if dt not in deletion_order]
	for doctype_key in remaining:
		for name in records[doctype_key]:
			try:
				if frappe.db.exists(doctype_key, name):
					frappe.delete_doc(
						doctype_key, name,
						force=True,
						ignore_permissions=True,
						delete_permanently=True,
					)
					deleted += 1
			except Exception:
				pass
		frappe.db.commit()

	frappe.cache().delete_value(DEMO_DATA_KEY)
	frappe.db.commit()

	frappe.flags.mute_emails = False
	frappe.flags.mute_notifications = False

	return {"message": f"Cleared {deleted} of {total_records} demo records."}
