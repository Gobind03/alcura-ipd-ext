// Copyright (c) 2026, Alcura and contributors
// For license information, please see license.txt
//
// US-N1: Nursing Workload by Ward

frappe.query_reports["Nursing Workload by Ward"] = {
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
			get_query: () => ({ filters: { is_active: 1 } }),
		},
	],

	formatter(value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);

		if (!data) return value;

		if (column.fieldname === "overdue_charts" && data.overdue_charts > 0) {
			value = `<span class="text-warning"><strong>${data.overdue_charts}</strong></span>`;
		}

		if (column.fieldname === "overdue_mar_count" && data.overdue_mar_count > 0) {
			value = `<span class="text-danger"><strong>${data.overdue_mar_count}</strong></span>`;
		}

		if (column.fieldname === "high_acuity_count" && data.high_acuity_count > 0) {
			value = `<span class="indicator-pill red">${data.high_acuity_count}</span>`;
		}

		if (column.fieldname === "overdue_protocol_steps" && data.overdue_protocol_steps > 0) {
			value = `<span class="text-warning"><strong>${data.overdue_protocol_steps}</strong></span>`;
		}

		if (column.fieldname === "workload_score") {
			const score = data.workload_score || 0;
			let color = "green";
			if (score >= 50) color = "red";
			else if (score >= 25) color = "orange";
			value = `<span class="indicator-pill ${color}">${score}</span>`;
		}

		return value;
	},
};
