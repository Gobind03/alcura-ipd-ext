"""Utility functions for bed/room/ward capacity management and HSU bridging.

All HSU-creation helpers live here so that both Hospital Room and Hospital Bed
controllers can call them without circular imports.
"""

import frappe
from frappe import _


# ---------------------------------------------------------------------------
# HSU auto-creation
# ---------------------------------------------------------------------------


def create_hsu_group_for_room(
	room_name: str,
	room_number: str,
	ward_hsu: str,
	service_unit_type: str,
	company: str,
) -> str:
	"""Create an HSU *group* node representing a room under a ward's HSU.

	Returns the name of the newly created Healthcare Service Unit.
	"""
	hsu_name = f"{ward_hsu} - Room {room_number}"
	if frappe.db.exists("Healthcare Service Unit", hsu_name):
		return hsu_name

	hsu = frappe.get_doc(
		{
			"doctype": "Healthcare Service Unit",
			"healthcare_service_unit_name": hsu_name,
			"is_group": 1,
			"parent_healthcare_service_unit": ward_hsu,
			"company": company,
		}
	)
	hsu.flags.ignore_permissions = True
	hsu.flags.ignore_mandatory = True
	hsu.flags.ignore_validate = True
	hsu.insert()
	return hsu.name


def create_hsu_leaf_for_bed(
	bed_number: str,
	room_hsu: str,
	service_unit_type: str,
	company: str,
) -> str:
	"""Create an HSU *leaf* node representing a bed under a room's HSU.

	The leaf node has ``inpatient_occupancy=1`` so it participates in the
	standard admission/billing pipeline.

	Returns the name of the newly created Healthcare Service Unit.
	"""
	hsu_name = f"{room_hsu} - Bed {bed_number}"
	if frappe.db.exists("Healthcare Service Unit", hsu_name):
		return hsu_name

	if not service_unit_type:
		service_unit_type = frappe.db.get_value(
			"Healthcare Service Unit Type",
			{"inpatient_occupancy": 1},
			"name",
		)

	hsu = frappe.get_doc(
		{
			"doctype": "Healthcare Service Unit",
			"healthcare_service_unit_name": hsu_name,
			"is_group": 0,
			"parent_healthcare_service_unit": room_hsu,
			"service_unit_type": service_unit_type,
			"company": company,
		}
	)
	hsu.flags.ignore_permissions = True
	hsu.flags.ignore_mandatory = True
	hsu.flags.ignore_validate = True
	hsu.insert()
	return hsu.name


# ---------------------------------------------------------------------------
# Capacity rollup
# ---------------------------------------------------------------------------


def recompute_room_capacity(room_name: str) -> None:
	"""Recompute bed counts on a Hospital Room from its Hospital Bed children."""
	total = frappe.db.count("Hospital Bed", {"hospital_room": room_name, "is_active": 1})
	occupied = frappe.db.count(
		"Hospital Bed",
		{"hospital_room": room_name, "is_active": 1, "occupancy_status": "Occupied"},
	)
	available = total - occupied

	frappe.db.set_value(
		"Hospital Room",
		room_name,
		{"total_beds": total, "occupied_beds": occupied, "available_beds": available},
		update_modified=False,
	)


def recompute_ward_capacity(ward_name: str) -> None:
	"""Recompute bed counts on a Hospital Ward from its Hospital Bed children."""
	total = frappe.db.count("Hospital Bed", {"hospital_ward": ward_name, "is_active": 1})
	occupied = frappe.db.count(
		"Hospital Bed",
		{"hospital_ward": ward_name, "is_active": 1, "occupancy_status": "Occupied"},
	)
	available = total - occupied

	frappe.db.set_value(
		"Hospital Ward",
		ward_name,
		{"total_beds": total, "occupied_beds": occupied, "available_beds": available},
		update_modified=False,
	)


def recompute_capacity_for_bed(room_name: str, ward_name: str) -> None:
	"""Convenience wrapper: recompute both room and ward capacity."""
	if room_name:
		recompute_room_capacity(room_name)
	if ward_name:
		recompute_ward_capacity(ward_name)


# ---------------------------------------------------------------------------
# Occupancy sync  (Hospital Bed ↔ Healthcare Service Unit)
# ---------------------------------------------------------------------------


def sync_hsu_occupancy_from_bed(bed_doc) -> None:
	"""Push occupancy_status from Hospital Bed to its linked HSU."""
	if not bed_doc.healthcare_service_unit:
		return

	current = frappe.db.get_value(
		"Healthcare Service Unit", bed_doc.healthcare_service_unit, "occupancy_status"
	)
	if current != bed_doc.occupancy_status:
		frappe.db.set_value(
			"Healthcare Service Unit",
			bed_doc.healthcare_service_unit,
			"occupancy_status",
			bed_doc.occupancy_status,
			update_modified=False,
		)


def sync_bed_occupancy_from_hsu(hsu_name: str, new_status: str) -> None:
	"""Push occupancy_status from HSU back to the linked Hospital Bed.

	Called from the ``Healthcare Service Unit`` doc_events hook.
	"""
	bed_name = frappe.db.get_value("Hospital Bed", {"healthcare_service_unit": hsu_name}, "name")
	if not bed_name:
		return

	current = frappe.db.get_value("Hospital Bed", bed_name, "occupancy_status")
	if current == new_status:
		return

	frappe.db.set_value(
		"Hospital Bed",
		bed_name,
		"occupancy_status",
		new_status,
		update_modified=False,
	)

	hospital_room, hospital_ward = frappe.db.get_value(
		"Hospital Bed", bed_name, ["hospital_room", "hospital_ward"]
	)
	recompute_capacity_for_bed(hospital_room, hospital_ward)
