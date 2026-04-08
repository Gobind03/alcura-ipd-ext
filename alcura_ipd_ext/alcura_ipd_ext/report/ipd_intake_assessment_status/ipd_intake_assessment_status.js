// Copyright (c) 2026, Alcura and contributors
// For license information, please see license.txt

frappe.query_reports["IPD Intake Assessment Status"] = {
	filters: [
		{
			fieldname: "company",
			label: __("Company"),
			fieldtype: "Link",
			options: "Company",
		},
		{
			fieldname: "specialty",
			label: __("Specialty"),
			fieldtype: "Link",
			options: "Medical Department",
		},
		{
			fieldname: "status",
			label: __("Status"),
			fieldtype: "Select",
			options: "\nDraft\nIn Progress\nCompleted",
		},
		{
			fieldname: "from_date",
			label: __("From Date"),
			fieldtype: "Date",
			default: frappe.datetime.add_months(frappe.datetime.get_today(), -1),
		},
		{
			fieldname: "to_date",
			label: __("To Date"),
			fieldtype: "Date",
			default: frappe.datetime.get_today(),
		},
		{
			fieldname: "template",
			label: __("Template"),
			fieldtype: "Link",
			options: "IPD Intake Assessment Template",
		},
	],
};
