frappe.query_reports["Protocol Compliance Report"] = {
	filters: [
		{
			fieldname: "protocol_bundle",
			label: __("Protocol Bundle"),
			fieldtype: "Link",
			options: "Monitoring Protocol Bundle",
		},
		{
			fieldname: "status",
			label: __("Status"),
			fieldtype: "Select",
			options: "\nActive\nCompleted\nDiscontinued\nExpired",
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
			default: frappe.datetime.add_months(frappe.datetime.get_today(), -1),
		},
		{
			fieldname: "to_date",
			label: __("To Date"),
			fieldtype: "Date",
			default: frappe.datetime.get_today(),
		},
	],
};
