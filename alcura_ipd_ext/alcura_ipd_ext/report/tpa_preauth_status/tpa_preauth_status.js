frappe.query_reports["TPA Preauth Status"] = {
	filters: [
		{
			fieldname: "status",
			label: __("Status"),
			fieldtype: "Select",
			options: "\nDraft\nSubmitted\nQuery Raised\nResubmitted\nApproved\nPartially Approved\nRejected\nClosed",
		},
		{
			fieldname: "payer_type",
			label: __("Payer Type"),
			fieldtype: "Select",
			options: "\nCorporate\nInsurance TPA\nPSU\nGovernment Scheme",
		},
		{
			fieldname: "insurance_payor",
			label: __("Insurance Payor"),
			fieldtype: "Link",
			options: "Insurance Payor",
		},
		{
			fieldname: "treating_practitioner",
			label: __("Treating Practitioner"),
			fieldtype: "Link",
			options: "Healthcare Practitioner",
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
