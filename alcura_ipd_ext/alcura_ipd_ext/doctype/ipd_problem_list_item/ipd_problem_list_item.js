// Copyright (c) 2026, Alcura and contributors
// For license information, please see license.txt

frappe.ui.form.on("IPD Problem List Item", {
	refresh(frm) {
		if (frm.doc.status === "Active" && !frm.is_new()) {
			frm.add_custom_button(__("Resolve"), () => {
				const d = new frappe.ui.Dialog({
					title: __("Resolve Problem"),
					fields: [
						{
							fieldtype: "Small Text",
							fieldname: "resolution_notes",
							label: __("Resolution Notes"),
						},
					],
					primary_action_label: __("Resolve"),
					primary_action(values) {
						d.hide();
						frm.set_value("status", "Resolved");
						frm.set_value("resolution_notes", values.resolution_notes || "");
						frm.save();
					},
				});
				d.show();
			});
		}
	},

	inpatient_record(frm) {
		if (frm.doc.inpatient_record) {
			frappe.db.get_value(
				"Inpatient Record",
				frm.doc.inpatient_record,
				["patient", "company"],
				(r) => {
					if (r) {
						frm.set_value("patient", r.patient);
						frm.set_value("company", r.company);
					}
				}
			);
		}
	},
});
