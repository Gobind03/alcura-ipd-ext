// Copyright (c) 2026, Alcura and contributors
// For license information, please see license.txt

frappe.ui.form.on("IPD MAR Entry", {
	refresh(frm) {
		if (frm.doc.status === "Corrected") {
			frm.dashboard.add_comment(
				__("This entry has been corrected."),
				"orange",
				true
			);
			frm.disable_save();
		}

		if (!frm.is_new() && frm.doc.status === "Active" && !frm.is_dirty()) {
			frm.add_custom_button(__("Correct Entry"), () => {
				_create_mar_correction(frm);
			});
		}
	},

	administration_status(frm) {
		if (["Given", "Self-Administered"].includes(frm.doc.administration_status)) {
			if (!frm.doc.administered_at) {
				frm.set_value("administered_at", frappe.datetime.now_datetime());
			}
			if (!frm.doc.administered_by) {
				frm.set_value("administered_by", frappe.session.user);
			}
		}
	},
});

function _create_mar_correction(frm) {
	const d = new frappe.ui.Dialog({
		title: __("Correct MAR Entry"),
		fields: [
			{
				fieldtype: "Small Text",
				fieldname: "correction_reason",
				label: __("Reason for Correction"),
				reqd: 1,
			},
		],
		primary_action_label: __("Create Correction"),
		primary_action(values) {
			d.hide();
			frappe.call({
				method: "alcura_ipd_ext.api.charting.create_mar_correction",
				args: {
					original_entry: frm.doc.name,
					correction_reason: values.correction_reason,
				},
				freeze: true,
				callback(r) {
					if (r.message) {
						frappe.set_route("Form", "IPD MAR Entry", r.message.name);
					}
				},
			});
		},
	});
	d.show();
}
