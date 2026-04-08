// Copyright (c) 2026, Alcura and contributors
// For license information, please see license.txt
//
// US-L2: Documentation Compliance Report

frappe.query_reports["Documentation Compliance"] = {
	filters: [
		{
			fieldname: "company",
			label: __("Company"),
			fieldtype: "Link",
			options: "Company",
			default: frappe.defaults.get_user_default("Company"),
		},
		{
			fieldname: "ward",
			label: __("Ward"),
			fieldtype: "Link",
			options: "Hospital Ward",
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
			fieldname: "status",
			label: __("Status"),
			fieldtype: "Select",
			options: "\nAdmitted\nDischarge Initiated\nDischarge in Progress",
			default: "Admitted",
		},
	],

	formatter(value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);

		if (!data) return value;

		if (column.fieldname === "compliance_score") {
			const score = data.compliance_score || 0;
			if (score < 50) {
				value = `<span class="text-danger"><strong>${score}%</strong></span>`;
			} else if (score < 75) {
				value = `<span class="text-warning"><strong>${score}%</strong></span>`;
			} else {
				value = `<span class="text-success"><strong>${score}%</strong></span>`;
			}
		}

		if (column.fieldname === "progress_note_gap" && data.progress_note_gap > 1) {
			value = `<span class="indicator-pill red">${data.progress_note_gap}d</span>`;
		}

		if (column.fieldname === "has_admission_note" && !data.has_admission_note) {
			value = '<span class="indicator-pill red">MISSING</span>';
		}

		if (column.fieldname === "intake_complete" && !data.intake_complete) {
			value = '<span class="indicator-pill orange">PENDING</span>';
		}

		if (column.fieldname === "nursing_charts_ok" && !data.nursing_charts_ok) {
			value = '<span class="indicator-pill red">OVERDUE</span>';
		}

		if (column.fieldname === "overdue_charts" && data.overdue_charts > 0) {
			value = `<span class="indicator-pill red">${data.overdue_charts}</span>`;
		}

		if (
			column.fieldname === "has_discharge_summary" &&
			data.has_discharge_summary === 0
		) {
			value = '<span class="indicator-pill red">MISSING</span>';
		}

		return value;
	},
};
