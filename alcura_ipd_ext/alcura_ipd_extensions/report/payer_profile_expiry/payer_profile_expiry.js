frappe.query_reports["Payer Profile Expiry"] = {
	filters: [
		{
			fieldname: "expiry_within_days",
			label: __("Expiry Within (Days)"),
			fieldtype: "Int",
			default: 30,
			reqd: 1,
		},
		{
			fieldname: "payer_type",
			label: __("Payer Type"),
			fieldtype: "Select",
			options: "\nCash\nCorporate\nInsurance TPA\nPSU\nGovernment Scheme",
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
			default: frappe.defaults.get_user_default("Company"),
		},
	],
};
