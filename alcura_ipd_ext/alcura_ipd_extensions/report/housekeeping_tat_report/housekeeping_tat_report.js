// Copyright (c) 2026, Alcura and contributors
// For license information, please see license.txt

frappe.query_reports["Housekeeping TAT Report"] = {
	filters: [
		{
			fieldname: "ward",
			label: __("Ward"),
			fieldtype: "Link",
			options: "Hospital Ward",
		},
		{
			fieldname: "cleaning_type",
			label: __("Cleaning Type"),
			fieldtype: "Select",
			options: "\nStandard\nDeep Clean\nIsolation Clean\nTerminal Clean",
		},
		{
			fieldname: "status",
			label: __("Status"),
			fieldtype: "Select",
			options: "\nPending\nIn Progress\nCompleted\nCancelled",
		},
		{
			fieldname: "from_date",
			label: __("From Date"),
			fieldtype: "Date",
			default: frappe.datetime.add_days(frappe.datetime.get_today(), -7),
		},
		{
			fieldname: "to_date",
			label: __("To Date"),
			fieldtype: "Date",
			default: frappe.datetime.get_today(),
		},
		{
			fieldname: "company",
			label: __("Company"),
			fieldtype: "Link",
			options: "Company",
		},
	],
};
