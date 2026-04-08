// Copyright (c) 2026, Alcura and contributors
// For license information, please see license.txt
//
// US-E3: IPD Consultation Notes report filters

frappe.query_reports["IPD Consultation Notes"] = {
	filters: [
		{
			fieldname: "company",
			label: __("Company"),
			fieldtype: "Link",
			options: "Company",
			default: frappe.defaults.get_user_default("Company"),
		},
		{
			fieldname: "patient",
			label: __("Patient"),
			fieldtype: "Link",
			options: "Patient",
		},
		{
			fieldname: "practitioner",
			label: __("Practitioner"),
			fieldtype: "Link",
			options: "Healthcare Practitioner",
		},
		{
			fieldname: "medical_department",
			label: __("Department"),
			fieldtype: "Link",
			options: "Medical Department",
		},
		{
			fieldname: "note_type",
			label: __("Note Type"),
			fieldtype: "Select",
			options: "\nAdmission Note\nProgress Note\nProcedure Note\nConsultation Note\nDischarge Summary",
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
		},
		{
			fieldname: "to_date",
			label: __("To Date"),
			fieldtype: "Date",
		},
	],

	formatter(value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);

		if (column.fieldname === "note_type" && value) {
			const plain = $("<div>").html(value).text().trim();
			const color_map = {
				"Admission Note": "blue",
				"Progress Note": "green",
				"Procedure Note": "orange",
				"Consultation Note": "purple",
				"Discharge Summary": "grey",
			};
			const color = color_map[plain] || "grey";
			value = `<span class="indicator-pill ${color}">${plain}</span>`;
		}

		if (column.fieldname === "docstatus") {
			const plain = $("<div>").html(value).text().trim();
			if (plain === "Draft") {
				value = '<span class="indicator-pill orange">Draft</span>';
			} else if (plain === "Submitted") {
				value = '<span class="indicator-pill blue">Submitted</span>';
			}
		}

		return value;
	},
};
