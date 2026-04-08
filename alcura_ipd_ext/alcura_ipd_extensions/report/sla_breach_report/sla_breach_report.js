// Copyright (c) 2026, Alcura and contributors
// For license information, please see license.txt
//
// US-L3: SLA Breach Report

frappe.query_reports["SLA Breach Report"] = {
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
			fieldname: "order_type",
			label: __("Order Type"),
			fieldtype: "Select",
			options: "\nMedication\nLab Test\nRadiology\nProcedure",
		},
		{
			fieldname: "urgency",
			label: __("Urgency"),
			fieldtype: "Select",
			options: "\nRoutine\nUrgent\nSTAT\nEmergency",
		},
		{
			fieldname: "ward",
			label: __("Ward"),
			fieldtype: "Link",
			options: "Hospital Ward",
		},
		{
			fieldname: "department",
			label: __("Department"),
			fieldtype: "Link",
			options: "Medical Department",
		},
	],

	formatter(value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);

		if (!data) return value;

		if (column.fieldname === "delay_minutes" && data.delay_minutes > 0) {
			if (data.delay_minutes > 60) {
				value = `<span class="text-danger"><strong>${data.delay_minutes}</strong></span>`;
			} else {
				value = `<span class="text-warning"><strong>${data.delay_minutes}</strong></span>`;
			}
		}

		if (column.fieldname === "urgency") {
			const colors = { STAT: "red", Emergency: "red", Urgent: "orange" };
			const color = colors[data.urgency];
			if (color) {
				value = `<span class="indicator-pill ${color}">${frappe.utils.escape_html(data.urgency)}</span>`;
			}
		}

		if (column.fieldname === "breached_milestone" && data.breached_milestone) {
			value = `<span class="indicator-pill red">${frappe.utils.escape_html(data.breached_milestone)}</span>`;
		}

		return value;
	},
};
