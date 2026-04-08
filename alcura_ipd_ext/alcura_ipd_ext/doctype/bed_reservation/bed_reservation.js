// Copyright (c) 2026, Alcura and contributors
// For license information, please see license.txt

frappe.ui.form.on("Bed Reservation", {
	setup(frm) {
		frm.set_query("hospital_ward", () => ({
			filters: { is_active: 1 },
		}));

		frm.set_query("hospital_room", () => {
			const filters = { is_active: 1 };
			if (frm.doc.hospital_ward) {
				filters.hospital_ward = frm.doc.hospital_ward;
			}
			return { filters };
		});

		frm.set_query("hospital_bed", () => {
			const filters = { is_active: 1, occupancy_status: "Vacant" };
			if (frm.doc.hospital_room) {
				filters.hospital_room = frm.doc.hospital_room;
			} else if (frm.doc.hospital_ward) {
				filters.hospital_ward = frm.doc.hospital_ward;
			}
			if (frm.doc.service_unit_type) {
				filters.service_unit_type = frm.doc.service_unit_type;
			}
			if (frm.doc.company) {
				filters.company = frm.doc.company;
			}
			return { filters };
		});

		frm.set_query("service_unit_type", () => ({
			filters: { inpatient_occupancy: 1 },
		}));

		frm.set_query("patient", () => ({
			filters: { status: "Active" },
		}));

		frm.set_query("payer", () => ({
			filters: { disabled: 0 },
		}));

		frm.set_query("patient_payer_profile", () => {
			const filters = { is_active: 1 };
			if (frm.doc.patient) {
				filters.patient = frm.doc.patient;
			}
			return { filters };
		});
	},

	refresh(frm) {
		_set_indicator(frm);
		_toggle_type_fields(frm);
		_add_action_buttons(frm);

		if (!frm.is_new() && frm.doc.status !== "Draft") {
			frm.disable_save();
		}
	},

	reservation_type(frm) {
		_toggle_type_fields(frm);
		if (frm.doc.reservation_type === "Room Type Hold") {
			frm.set_value("hospital_bed", "");
			frm.set_value("hospital_room", "");
			frm.set_value("bed_name", "");
		}
	},

	hospital_bed(frm) {
		if (frm.doc.hospital_bed) {
			frappe.db.get_value(
				"Hospital Bed",
				frm.doc.hospital_bed,
				["hospital_room", "hospital_ward", "service_unit_type", "company"],
				(r) => {
					if (r) {
						frm.set_value("hospital_room", r.hospital_room);
						frm.set_value("hospital_ward", r.hospital_ward);
						if (!frm.doc.service_unit_type) {
							frm.set_value("service_unit_type", r.service_unit_type);
						}
						if (!frm.doc.company) {
							frm.set_value("company", r.company);
						}
					}
				}
			);
		}
	},

	reservation_start(frm) {
		_recompute_end(frm);
	},

	timeout_minutes(frm) {
		_recompute_end(frm);
	},
});

function _set_indicator(frm) {
	const map = {
		Draft: ["Draft", "grey"],
		Active: ["Active", "blue"],
		Expired: ["Expired", "orange"],
		Cancelled: ["Cancelled", "red"],
		Consumed: ["Consumed", "green"],
	};
	const entry = map[frm.doc.status];
	if (entry) {
		frm.page.set_indicator(__(entry[0]), entry[1]);
	}
}

function _toggle_type_fields(frm) {
	const is_specific = frm.doc.reservation_type === "Specific Bed";
	frm.toggle_reqd("hospital_bed", is_specific);
	frm.toggle_reqd("service_unit_type", !is_specific);
}

function _add_action_buttons(frm) {
	if (frm.is_new() || frm.is_dirty()) return;

	if (frm.doc.status === "Draft") {
		frm.add_custom_button(__("Activate Reservation"), () => {
			frappe.confirm(
				__("Activate this reservation? The bed will be held until {0}.", [
					frm.doc.reservation_end,
				]),
				() => {
					frm.call("action_activate").then(() => frm.refresh_fields());
				}
			);
		}, __("Actions"));
		frm.change_custom_button_type(__("Activate Reservation"), __("Actions"), "primary");
	}

	if (frm.doc.status === "Active") {
		frm.add_custom_button(__("Cancel Reservation"), () => {
			_prompt_cancel(frm, false);
		}, __("Actions"));

		if (frappe.user_roles.includes("Healthcare Administrator")) {
			frm.add_custom_button(__("Override & Cancel"), () => {
				_prompt_cancel(frm, true);
			}, __("Actions"));
		}

		frm.add_custom_button(__("Mark as Consumed"), () => {
			_prompt_consume(frm);
		}, __("Actions"));
	}
}

function _prompt_cancel(frm, is_override) {
	const fields = [
		{
			fieldtype: "Small Text",
			fieldname: "reason",
			label: __("Cancellation Reason"),
			reqd: 1,
		},
	];
	if (is_override) {
		fields.push({
			fieldtype: "Small Text",
			fieldname: "override_reason",
			label: __("Override Reason"),
			reqd: 1,
		});
	}

	frappe.prompt(fields, (values) => {
		frm.call("action_cancel", {
			reason: values.reason,
			is_override: is_override ? 1 : 0,
			override_reason: values.override_reason || "",
		}).then(() => frm.refresh_fields());
	}, is_override ? __("Override & Cancel Reservation") : __("Cancel Reservation"), __("Confirm"));
}

function _prompt_consume(frm) {
	frappe.prompt(
		[
			{
				fieldtype: "Link",
				fieldname: "inpatient_record",
				label: __("Inpatient Record"),
				options: "Inpatient Record",
				reqd: 1,
			},
		],
		(values) => {
			frm.call("action_consume", {
				inpatient_record: values.inpatient_record,
			}).then(() => frm.refresh_fields());
		},
		__("Consume Reservation"),
		__("Confirm")
	);
}

function _recompute_end(frm) {
	if (frm.doc.reservation_start && frm.doc.timeout_minutes) {
		const start = frappe.datetime.str_to_obj(frm.doc.reservation_start);
		const end = frappe.datetime.add_minutes(start, frm.doc.timeout_minutes);
		frm.set_value("reservation_end", frappe.datetime.obj_to_str(end));
	}
}
