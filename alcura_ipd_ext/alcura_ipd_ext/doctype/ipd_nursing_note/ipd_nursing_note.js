// Copyright (c) 2026, Alcura and contributors
// For license information, please see license.txt

frappe.ui.form.on("IPD Nursing Note", {
	refresh(frm) {
		if (frm.doc.status === "Amended") {
			frm.dashboard.add_comment(
				__("This note has been amended. See the addendum for updates."),
				"orange",
				true
			);
		}

		if (!frm.is_new() && frm.doc.status === "Active" && !frm.is_dirty()) {
			frm.add_custom_button(__("Add Addendum"), () => {
				_create_addendum(frm);
			});
		}
	},
});

function _create_addendum(frm) {
	const d = new frappe.ui.Dialog({
		title: __("Add Addendum"),
		fields: [
			{
				fieldtype: "Small Text",
				fieldname: "addendum_reason",
				label: __("Reason for Addendum"),
				reqd: 1,
			},
		],
		primary_action_label: __("Create Addendum"),
		primary_action(values) {
			d.hide();
			frappe.new_doc("IPD Nursing Note", {
				patient: frm.doc.patient,
				inpatient_record: frm.doc.inpatient_record,
				category: frm.doc.category,
				is_addendum: 1,
				addendum_to: frm.doc.name,
				addendum_reason: values.addendum_reason,
			});
		},
	});
	d.show();
}
