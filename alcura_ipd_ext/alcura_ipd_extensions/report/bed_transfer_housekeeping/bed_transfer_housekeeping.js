// Copyright (c) 2026, Alcura and contributors
// For license information, please see license.txt

frappe.query_reports["Bed Transfer and Housekeeping"] = {
	filters: [
		{
			fieldname: "from_date",
			label: __("From Date"),
			fieldtype: "Date",
			default: frappe.datetime.add_days(frappe.datetime.get_today(), -7),
			reqd: 1,
		},
		{
			fieldname: "to_date",
			label: __("To Date"),
			fieldtype: "Date",
			default: frappe.datetime.get_today(),
			reqd: 1,
		},
		{
			fieldname: "ward",
			label: __("Ward"),
			fieldtype: "Link",
			options: "Hospital Ward",
			get_query: () => ({ filters: { is_active: 1 } }),
		},
		{
			fieldname: "consultant",
			label: __("Consultant"),
			fieldtype: "Link",
			options: "Healthcare Practitioner",
		},
		{
			fieldname: "movement_type",
			label: __("Movement Type"),
			fieldtype: "Select",
			options: "All\nTransfer\nDischarge",
			default: "All",
		},
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
	],

	formatter(value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);

		if (column.fieldname === "movement_type" && data) {
			const mt = data.movement_type;
			if (mt === "Transfer") {
				value = `<span class="indicator-pill blue">${__("Transfer")}</span>`;
			} else if (mt === "Discharge") {
				value = `<span class="indicator-pill orange">${__("Discharge")}</span>`;
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
