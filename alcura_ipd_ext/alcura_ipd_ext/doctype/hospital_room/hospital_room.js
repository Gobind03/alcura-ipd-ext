// Copyright (c) 2026, Alcura and contributors
// For license information, please see license.txt

frappe.ui.form.on("Hospital Room", {
	setup(frm) {
		frm.set_query("hospital_ward", () => ({
			filters: { is_active: 1 },
		}));

		frm.set_query("service_unit_type", () => ({
			filters: { inpatient_occupancy: 1 },
		}));

		frm.set_query("healthcare_service_unit", () => {
			const filters = { is_group: 1 };
			if (frm.doc.company) {
				filters.company = frm.doc.company;
			}
			return { filters };
		});
	},

	refresh(frm) {
		frm.toggle_enable(
			["total_beds", "occupied_beds", "available_beds", "healthcare_service_unit"],
			false
		);
	},

	room_number(frm) {
		if (frm.doc.room_number) {
			frm.set_value("room_number", frm.doc.room_number.toUpperCase().trim());
		}
	},

	hospital_ward(frm) {
		if (frm.doc.hospital_ward) {
			frappe.db.get_value("Hospital Ward", frm.doc.hospital_ward, "company", (r) => {
				if (r && r.company) {
					frm.set_value("company", r.company);
				}
			});
		} else {
			frm.set_value("company", "");
		}
	},
});
