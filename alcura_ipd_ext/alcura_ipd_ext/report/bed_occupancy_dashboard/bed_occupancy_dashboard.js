// Copyright (c) 2026, Alcura and contributors
// For license information, please see license.txt

frappe.query_reports["Bed Occupancy Dashboard"] = {
	filters: [
		{
			fieldname: "company",
			label: __("Company"),
			fieldtype: "Link",
			options: "Company",
			default: frappe.defaults.get_user_default("Company"),
		},
		{
			fieldname: "branch",
			label: __("Branch"),
			fieldtype: "Data",
		},
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
			fieldname: "critical_care_only",
			label: __("Critical Care Only"),
			fieldtype: "Check",
			default: 0,
		},
		{
			fieldname: "group_by",
			label: __("Group By"),
			fieldtype: "Select",
			options: "Ward\nRoom Type",
			default: "Ward",
		},
	],

	formatter(value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);

		if (column.fieldname === "occupancy_pct" && data) {
			const pct = data.occupancy_pct || 0;
			if (pct > 90) {
				value = `<span class="indicator-pill red">${frappe.format(pct, { fieldtype: "Percent" })}</span>`;
			} else if (pct > 70) {
				value = `<span class="indicator-pill orange">${frappe.format(pct, { fieldtype: "Percent" })}</span>`;
			} else {
				value = `<span class="indicator-pill green">${frappe.format(pct, { fieldtype: "Percent" })}</span>`;
			}
		}

		if (column.fieldname === "ward_classification" && data) {
			const cls = data.ward_classification;
			if (cls === "ICU" || cls === "HDU") {
				value = `<span class="indicator-pill red">${__(cls)}</span>`;
			}
		}

		return value;
	},

	onload(report) {
		report.page.add_inner_button(__("Refresh"), () => {
			report.refresh();
		});
	},
};
