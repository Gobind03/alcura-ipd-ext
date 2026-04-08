// Copyright (c) 2026, Alcura and contributors
// For license information, please see license.txt

frappe.query_reports["Live Bed Board"] = {
	filters: [
		{
			fieldname: "ward",
			label: __("Ward"),
			fieldtype: "Link",
			options: "Hospital Ward",
			get_query: () => ({ filters: { is_active: 1 } }),
		},
		{
			fieldname: "room_type",
			label: __("Room Type"),
			fieldtype: "Link",
			options: "Healthcare Service Unit Type",
			get_query: () => ({ filters: { inpatient_occupancy: 1 } }),
		},
		{
			fieldname: "floor",
			label: __("Floor"),
			fieldtype: "Data",
		},
		{
			fieldname: "critical_care_only",
			label: __("Critical Care Only"),
			fieldtype: "Check",
			default: 0,
		},
		{
			fieldname: "gender",
			label: __("Gender"),
			fieldtype: "Select",
			options: "\nAll\nMale Only\nFemale Only",
			default: "",
		},
		{
			fieldname: "isolation_only",
			label: __("Isolation Only"),
			fieldtype: "Check",
			default: 0,
		},
		{
			fieldname: "payer_type",
			label: __("Payer Type"),
			fieldtype: "Select",
			options: "\nCash\nCorporate\nTPA",
			default: "",
			on_change: function () {
				const payer_type = frappe.query_report.get_filter_value("payer_type");
				const payer_filter = frappe.query_report.get_filter("payer");
				if (payer_type === "Corporate" || payer_type === "TPA") {
					payer_filter.df.hidden = 0;
					payer_filter.refresh();
				} else {
					frappe.query_report.set_filter_value("payer", "");
					payer_filter.df.hidden = 1;
					payer_filter.refresh();
				}
			},
		},
		{
			fieldname: "payer",
			label: __("Payer"),
			fieldtype: "Link",
			options: "Customer",
			hidden: 1,
			get_query: () => ({
				filters: { disabled: 0 },
			}),
		},
		{
			fieldname: "show_unavailable",
			label: __("Show Unavailable"),
			fieldtype: "Check",
			default: 0,
		},
	],

	formatter: function (value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);

		if (column.fieldname === "availability" && data) {
			const avail = data.availability;
			if (avail === "Available") {
				value = `<span class="indicator-pill green">${__("Available")}</span>`;
			} else if (avail === "Occupied") {
				value = `<span class="indicator-pill red">${__("Occupied")}</span>`;
			} else if (avail === "Maintenance") {
				value = `<span class="indicator-pill orange">${__("Maintenance")}</span>`;
			} else if (avail === "Infection Block") {
				value = `<span class="indicator-pill red">${__("Infection Block")}</span>`;
			} else if (avail === "Dirty") {
				value = `<span class="indicator-pill orange">${__("Dirty")}</span>`;
			} else if (avail === "Cleaning") {
				value = `<span class="indicator-pill yellow">${__("Cleaning")}</span>`;
			}
		}

		if (column.fieldname === "housekeeping_status" && data) {
			const hs = data.housekeeping_status;
			if (hs === "Clean") {
				value = `<span class="indicator-pill green">${__("Clean")}</span>`;
			} else if (hs === "Dirty") {
				value = `<span class="indicator-pill orange">${__("Dirty")}</span>`;
			} else if (hs === "In Progress") {
				value = `<span class="indicator-pill yellow">${__("In Progress")}</span>`;
			}
		}

		if (column.fieldname === "payer_eligible" && data) {
			if (data.payer_eligible === "Yes") {
				value = `<span class="indicator-pill green">${__("Yes")}</span>`;
			} else if (data.payer_eligible === "No") {
				value = `<span class="indicator-pill red">${__("No")}</span>`;
			}
		}

		return value;
	},

	onload: function (report) {
		report.page.add_inner_button(__("Refresh"), function () {
			report.refresh();
		});
	},
};
