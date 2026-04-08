// Copyright (c) 2026, Alcura and contributors
// For license information, please see license.txt
//
// US-N2: Incident and Critical Alert Report

frappe.query_reports["Incident Alert Report"] = {
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
			fieldname: "incident_type",
			label: __("Incident Type"),
			fieldtype: "Select",
			options: [
				"",
				"Fall Risk",
				"Pressure Risk",
				"Nutrition Risk",
				"Missed Medication",
				"Critical Observation",
				"SLA Breach",
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
			fieldname: "severity",
			label: __("Severity"),
			fieldtype: "Select",
			options: "\nHigh\nMedium\nLow",
		},
	],

	formatter(value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);

		if (!data) return value;

		if (column.fieldname === "severity") {
			const colors = { High: "red", Medium: "orange", Low: "blue" };
			const plain = $("<div>").html(value).text().trim();
			const color = colors[plain] || "grey";
			value = `<span class="indicator-pill ${color}">${plain}</span>`;
		}

		if (column.fieldname === "incident_type") {
			const colors = {
				"Fall Risk": "red",
				"Pressure Risk": "red",
				"Nutrition Risk": "orange",
				"Missed Medication": "orange",
				"Critical Observation": "red",
				"SLA Breach": "yellow",
			};
			const plain = $("<div>").html(value).text().trim();
			const color = colors[plain] || "grey";
			value = `<span class="indicator-pill ${color}">${plain}</span>`;
		}

		if (column.fieldname === "status") {
			const colors = { Open: "red", Closed: "green", Resolved: "green" };
			const plain = $("<div>").html(value).text().trim();
			const color = colors[plain] || "grey";
			value = `<span class="indicator-pill ${color}">${plain}</span>`;
		}

		return value;
	},
};
