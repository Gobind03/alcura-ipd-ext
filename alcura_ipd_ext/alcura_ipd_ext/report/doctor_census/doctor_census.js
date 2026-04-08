// Copyright (c) 2026, Alcura and contributors
// For license information, please see license.txt
//
// US-E5: Doctor Census report — shows all admitted patients for a practitioner

frappe.query_reports["Doctor Census"] = {
	filters: [
		{
			fieldname: "practitioner",
			label: __("Practitioner"),
			fieldtype: "Link",
			options: "Healthcare Practitioner",
			reqd: 1,
		},
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
			fieldname: "medical_department",
			label: __("Department"),
			fieldtype: "Link",
			options: "Medical Department",
		},
	],

	formatter(value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);

		if (column.fieldname === "allergy_alert" && data && data.allergy_alert) {
			value = '<span class="indicator-pill red">ALLERGY</span>';
		}

		if (column.fieldname === "overdue_charts" && data && data.overdue_charts > 0) {
			value = `<span class="indicator-pill red">${data.overdue_charts}</span>`;
		}

		if (column.fieldname === "active_problems" && data && data.active_problems > 0) {
			value = `<span class="indicator-pill orange">${data.active_problems}</span>`;
		}

		if (column.fieldname === "days_admitted" && data && data.days_admitted > 7) {
			value = `<span class="text-danger"><strong>${data.days_admitted}</strong></span>`;
		}

		return value;
	},

	onload(report) {
		report.page.add_inner_button(__("Start Round Note"), () => {
			const selected = report.get_checked_items();
			if (!selected.length) {
				frappe.msgprint(__("Please select a patient row first."));
				return;
			}
			const row = selected[0];
			frappe.call({
				method: "alcura_ipd_ext.api.round_sheet.create_round_note",
				args: {
					inpatient_record: row.inpatient_record,
					practitioner: report.get_filter_value("practitioner"),
				},
				freeze: true,
				freeze_message: __("Creating Progress Note..."),
				callback(r) {
					if (r.message) {
						frappe.set_route("Form", "Patient Encounter", r.message.encounter);
					}
				},
			});
		});
	},
};
