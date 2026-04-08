// Copyright (c) 2026, Alcura and contributors
// For license information, please see license.txt

frappe.query_reports["ADT Census"] = {
	filters: [
		{
			fieldname: "date",
			label: __("Date"),
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

		if (!data) return value;

		if (column.fieldname === "deaths" && data.deaths > 0) {
			value = `<span class="text-danger"><strong>${data.deaths}</strong></span>`;
		}

		if (column.fieldname === "closing_census") {
			const opening = data.opening_census || 0;
			const closing = data.closing_census || 0;
			if (closing > opening) {
				value = `<span class="text-danger"><strong>${closing}</strong></span>`;
			} else if (closing < opening) {
				value = `<span class="text-success"><strong>${closing}</strong></span>`;
			}
		}

		return value;
	},

	onload(report) {
		report.page.add_inner_button(__("Previous Day"), () => {
			const current = report.get_filter_value("date");
			report.set_filter_value("date", frappe.datetime.add_days(current, -1));
		});
		report.page.add_inner_button(__("Next Day"), () => {
			const current = report.get_filter_value("date");
			report.set_filter_value("date", frappe.datetime.add_days(current, 1));
		});
	},
};
