// Copyright (c) 2026, Alcura and contributors
// For license information, please see license.txt

frappe.query_reports["Vitals Trend"] = {
	filters: [
		{
			fieldname: "inpatient_record",
			label: __("Inpatient Record"),
			fieldtype: "Link",
			options: "Inpatient Record",
		},
		{
			fieldname: "patient",
			label: __("Patient"),
			fieldtype: "Link",
			options: "Patient",
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
	],
};
