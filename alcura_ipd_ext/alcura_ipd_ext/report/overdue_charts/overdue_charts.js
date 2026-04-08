// Copyright (c) 2026, Alcura and contributors
// For license information, please see license.txt

frappe.query_reports["Overdue Charts"] = {
	filters: [
		{
			fieldname: "ward",
			label: __("Ward"),
			fieldtype: "Link",
			options: "Hospital Ward",
		},
		{
			fieldname: "company",
			label: __("Company"),
			fieldtype: "Link",
			options: "Company",
		},
		{
			fieldname: "grace_minutes",
			label: __("Grace Period (min)"),
			fieldtype: "Int",
			default: 0,
		},
	],
};
