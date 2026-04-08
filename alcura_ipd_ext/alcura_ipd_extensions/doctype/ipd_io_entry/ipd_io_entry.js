// Copyright (c) 2026, Alcura and contributors
// For license information, please see license.txt

frappe.ui.form.on("IPD IO Entry", {
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
				_create_io_correction(frm);
			});
		}

		if (frm.doc.inpatient_record && !frm.is_new()) {
			_show_running_balance(frm);
		}
	},

	io_type(frm) {
		_set_default_categories(frm);
	},
});

function _set_default_categories(frm) {
	const intake_cats = ["IV Fluid", "Oral", "Blood Products", "TPN"];
	const output_cats = ["Urine", "Drain", "Vomit", "Stool", "Blood Loss", "NG Aspirate"];

	if (frm.doc.io_type === "Intake" && output_cats.includes(frm.doc.fluid_category)) {
		frm.set_value("fluid_category", "");
	}
	if (frm.doc.io_type === "Output" && intake_cats.includes(frm.doc.fluid_category)) {
		frm.set_value("fluid_category", "");
	}
}

function _show_running_balance(frm) {
	frappe.call({
		method: "alcura_ipd_ext.api.charting.get_fluid_balance_summary",
		args: { inpatient_record: frm.doc.inpatient_record },
		callback(r) {
			if (!r.message) return;
			const b = r.message;
			const color = b.balance >= 0 ? "blue" : "orange";
			frm.dashboard.add_comment(
				__("Today's Balance: Intake {0} mL — Output {1} mL = {2} mL", [
					b.total_intake,
					b.total_output,
					b.balance,
				]),
				color,
				true
			);
		},
	});
}

function _create_io_correction(frm) {
	const d = new frappe.ui.Dialog({
		title: __("Correct I/O Entry"),
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
				method: "alcura_ipd_ext.api.charting.create_io_correction",
				args: {
					original_entry: frm.doc.name,
					correction_reason: values.correction_reason,
				},
				freeze: true,
				callback(r) {
					if (r.message) {
						frappe.set_route("Form", "IPD IO Entry", r.message.name);
					}
				},
			});
		},
	});
	d.show();
}
