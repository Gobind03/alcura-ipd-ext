// Copyright (c) 2026, Alcura and contributors
// For license information, please see license.txt
//
// US-L3: Order TAT Report

frappe.query_reports["Order TAT Report"] = {
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
		{
			fieldname: "consultant",
			label: __("Consultant"),
			fieldtype: "Link",
			options: "Healthcare Practitioner",
		},
		{
			fieldname: "status",
			label: __("Status"),
			fieldtype: "Select",
			options: "\nOrdered\nAcknowledged\nIn Progress\nCompleted\nCancelled",
		},
	],

	formatter(value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);

		if (!data) return value;

		if (column.fieldname === "is_sla_breached" && data.is_sla_breached) {
			value = '<span class="indicator-pill red">BREACHED</span>';
		}

		if (column.fieldname === "tat_minutes" && data.tat_minutes != null) {
			const target = data.sla_target_minutes;
			if (target && data.tat_minutes > target) {
				value = `<span class="text-danger"><strong>${data.tat_minutes}</strong></span>`;
			}
		}

		if (column.fieldname === "urgency") {
			const colors = { STAT: "red", Emergency: "red", Urgent: "orange" };
			const color = colors[data.urgency];
			if (color) {
				value = `<span class="indicator-pill ${color}">${frappe.utils.escape_html(data.urgency)}</span>`;
			}
		}

		return value;
	},
};
