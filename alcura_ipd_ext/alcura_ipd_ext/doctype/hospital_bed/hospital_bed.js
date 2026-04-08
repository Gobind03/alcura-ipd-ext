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
		_add_housekeeping_buttons(frm);
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

function _add_housekeeping_buttons(frm) {
	if (frm.is_new() || frm.is_dirty()) return;
	if (frm.doc.occupancy_status !== "Vacant") return;

	if (frm.doc.housekeeping_status === "Dirty") {
		frm.add_custom_button(__("Start Cleaning"), () => {
			frappe.call({
				method: "alcura_ipd_ext.api.discharge.start_cleaning",
				args: { task_name: _get_active_task_name(frm) },
				freeze: true,
				freeze_message: __("Starting cleaning..."),
				callback(r) {
					if (r.message) {
						frappe.show_alert({ message: __("Cleaning started."), indicator: "blue" });
						frm.reload_doc();
					}
				},
				error() {
					frappe.msgprint(__("No active housekeeping task found. Create one from the Bed Housekeeping Task list."));
				},
			});
		}, __("Housekeeping"));
	}

	if (frm.doc.housekeeping_status === "In Progress") {
		frm.add_custom_button(__("Complete Cleaning"), () => {
			frappe.call({
				method: "alcura_ipd_ext.api.discharge.complete_cleaning",
				args: { task_name: _get_active_task_name(frm) },
				freeze: true,
				freeze_message: __("Completing cleaning..."),
				callback(r) {
					if (r.message) {
						frappe.show_alert({
							message: __("Cleaning completed. Bed is now available."),
							indicator: "green",
						});
						frm.reload_doc();
					}
				},
				error() {
					frappe.msgprint(__("No active housekeeping task found."));
				},
			});
		}, __("Housekeeping"));
	}

	if (frm.doc.housekeeping_status === "Dirty" || frm.doc.housekeeping_status === "In Progress") {
		frm.add_custom_button(__("View Housekeeping Task"), () => {
			frappe.set_route("List", "Bed Housekeeping Task", {
				hospital_bed: frm.doc.name,
				status: ["in", ["Pending", "In Progress"]],
			});
		}, __("Housekeeping"));
	}
}

function _get_active_task_name(frm) {
	let task_name = null;
	frappe.call({
		method: "frappe.client.get_value",
		args: {
			doctype: "Bed Housekeeping Task",
			filters: {
				hospital_bed: frm.doc.name,
				status: ["in", ["Pending", "In Progress"]],
			},
			fieldname: "name",
		},
		async: false,
		callback(r) {
			if (r.message) {
				task_name = r.message.name;
			}
		},
	});
	return task_name;
}
