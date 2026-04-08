// Copyright (c) 2026, Alcura and contributors
// For license information, please see license.txt

frappe.query_reports["MAR Summary"] = {
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
			fieldname: "administration_status",
			label: __("Status"),
			fieldtype: "Select",
			options: "\nScheduled\nGiven\nHeld\nRefused\nMissed\nSelf-Administered",
		},
		{
			fieldname: "ward",
			label: __("Ward"),
			fieldtype: "Link",
			options: "Hospital Ward",
		},
		{
			fieldname: "from_date",
			label: __("From Date"),
			fieldtype: "Date",
			default: frappe.datetime.get_today(),
		},
		{
			fieldname: "to_date",
			label: __("To Date"),
			fieldtype: "Date",
			default: frappe.datetime.get_today(),
		},
	],
};
