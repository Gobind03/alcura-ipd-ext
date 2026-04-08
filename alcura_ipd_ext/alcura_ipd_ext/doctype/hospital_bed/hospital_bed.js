// Copyright (c) 2026, Alcura and contributors
// For license information, please see license.txt

frappe.ui.form.on("Hospital Bed", {
	setup(frm) {
		frm.set_query("hospital_room", () => ({
			filters: { is_active: 1 },
		}));

		frm.set_query("healthcare_service_unit", () => {
			const filters = { is_group: 0, inpatient_occupancy: 1 };
			if (frm.doc.company) {
				filters.company = frm.doc.company;
			}
			return { filters };
		});
	},

	refresh(frm) {
		frm.toggle_enable(
			[
				"hospital_ward",
				"company",
				"service_unit_type",
				"healthcare_service_unit",
			],
			false
		);

		_set_status_indicator(frm);
	},

	bed_number(frm) {
		if (frm.doc.bed_number) {
			frm.set_value("bed_number", frm.doc.bed_number.toUpperCase().trim());
		}
	},

	hospital_room(frm) {
		if (frm.doc.hospital_room) {
			frappe.db.get_value(
				"Hospital Room",
				frm.doc.hospital_room,
				["hospital_ward", "company", "service_unit_type"],
				(r) => {
					if (r) {
						frm.set_value("hospital_ward", r.hospital_ward);
						frm.set_value("company", r.company);
						frm.set_value("service_unit_type", r.service_unit_type);
					}
				}
			);
		} else {
			frm.set_value("hospital_ward", "");
			frm.set_value("company", "");
			frm.set_value("service_unit_type", "");
		}
	},
});

function _set_status_indicator(frm) {
	if (!frm.doc.is_active) {
		frm.page.set_indicator(__("Inactive"), "grey");
		return;
	}
	if (frm.doc.maintenance_hold) {
		frm.page.set_indicator(__("Maintenance"), "orange");
		return;
	}
	if (frm.doc.infection_block) {
		frm.page.set_indicator(__("Infection Block"), "red");
		return;
	}
	if (frm.doc.occupancy_status === "Reserved") {
		frm.page.set_indicator(__("Reserved"), "purple");
	} else if (frm.doc.occupancy_status === "Occupied") {
		frm.page.set_indicator(__("Occupied"), "blue");
	} else if (frm.doc.housekeeping_status === "Dirty") {
		frm.page.set_indicator(__("Dirty"), "orange");
	} else if (frm.doc.housekeeping_status === "In Progress") {
		frm.page.set_indicator(__("Cleaning"), "yellow");
	} else {
		frm.page.set_indicator(__("Available"), "green");
	}
}
