frappe.query_reports["IPD Interim Bill"] = {
	filters: [
		{
			fieldname: "inpatient_record",
			label: __("Inpatient Record"),
			fieldtype: "Link",
			options: "Inpatient Record",
			reqd: 1,
		},
		{
			fieldname: "as_of_date",
			label: __("As of Date"),
			fieldtype: "Date",
			default: frappe.datetime.get_today(),
		},
	],
};
