// Copyright (c) 2026, Alcura and contributors
// For license information, please see license.txt

frappe.query_reports["IPD Fluid Balance"] = {
	filters: [
		{
			fieldname: "inpatient_record",
			label: __("Inpatient Record"),
			fieldtype: "Link",
			options: "Inpatient Record",
			reqd: 1,
		},
		{
			fieldname: "date",
			label: __("Date"),
			fieldtype: "Date",
			default: frappe.datetime.get_today(),
		},
		{
			fieldname: "view",
			label: __("View"),
			fieldtype: "Select",
			options: "Hourly\nShift",
			default: "Hourly",
		},
	],
};
