// Copyright (c) 2026, Alcura and contributors
// For license information, please see license.txt

frappe.query_reports["Payer Eligibility Check Summary"] = {
	filters: [
		{
			fieldname: "verification_status",
			label: __("Status"),
			fieldtype: "Select",
			options: "\nPending\nVerified\nConditional\nRejected\nExpired",
		},
		{
			fieldname: "payer_type",
			label: __("Payer Type"),
			fieldtype: "Select",
			options: "\nCash\nCorporate\nInsurance TPA\nPSU\nGovernment Scheme",
		},
		{
			fieldname: "company",
			label: __("Company"),
			fieldtype: "Link",
			options: "Company",
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

		if (column.fieldname === "verification_status" && data) {
			const colors = {
				Pending: "orange",
				Verified: "green",
				Conditional: "blue",
				Rejected: "red",
				Expired: "grey",
			};
			const color = colors[data.verification_status] || "grey";
			value = `<span class="indicator-pill ${color}">${value}</span>`;
		}

		return value;
	},
};
