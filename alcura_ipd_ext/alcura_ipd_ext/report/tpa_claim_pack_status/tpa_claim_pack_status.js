frappe.query_reports["TPA Claim Pack Status"] = {
	filters: [
		{
			fieldname: "status",
			label: __("Status"),
			fieldtype: "Select",
			options: "\nDraft\nIn Review\nSubmitted\nAcknowledged\nSettled\nDisputed",
		},
		{
			fieldname: "insurance_payor",
			label: __("Insurance Payor"),
			fieldtype: "Link",
			options: "Insurance Payor",
		},
		{
			fieldname: "company",
			label: __("Company"),
			fieldtype: "Link",
			options: "Company",
			default: frappe.defaults.get_user_default("company"),
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
};
