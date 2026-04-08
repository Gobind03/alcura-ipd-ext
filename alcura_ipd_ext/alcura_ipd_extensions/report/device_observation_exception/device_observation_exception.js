// Copyright (c) 2026, Alcura and contributors
// For license information, please see license.txt
//
// US-N3: Device Observation Exception Report

frappe.query_reports["Device Observation Exception"] = {
	filters: [
		{
			fieldname: "from_date",
			label: __("From Date"),
			fieldtype: "Date",
			default: frappe.datetime.add_days(frappe.datetime.get_today(), -1),
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
			fieldname: "exception_type",
			label: __("Exception Type"),
			fieldtype: "Select",
			options: [
				"",
				"Connectivity Failure",
				"Missing Observation",
				"Unacknowledged Abnormal",
			].join("\n"),
		},
		{
			fieldname: "ward",
			label: __("Ward"),
			fieldtype: "Link",
			options: "Hospital Ward",
		},
		{
			fieldname: "patient",
			label: __("Patient"),
			fieldtype: "Link",
			options: "Patient",
		},
		{
			fieldname: "device_type",
			label: __("Device Type"),
			fieldtype: "Data",
		},
	],

	formatter(value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);

		if (!data) return value;

		if (column.fieldname === "exception_type") {
			const colors = {
				"Connectivity Failure": "red",
				"Missing Observation": "orange",
				"Unacknowledged Abnormal": "red",
			};
			const plain = $("<div>").html(value).text().trim();
			const color = colors[plain] || "grey";
			value = `<span class="indicator-pill ${color}">${plain}</span>`;
		}

		return value;
	},
};
