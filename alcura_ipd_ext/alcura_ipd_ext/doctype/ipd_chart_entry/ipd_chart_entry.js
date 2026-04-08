// Copyright (c) 2026, Alcura and contributors
// For license information, please see license.txt

frappe.ui.form.on("IPD Chart Entry", {
	refresh(frm) {
		if (frm.doc.status === "Corrected") {
			frm.dashboard.add_comment(
				__("This entry has been corrected. See the correction entry for current values."),
				"orange",
				true
			);
			frm.disable_save();
		}

		if (!frm.is_new() && frm.doc.status === "Active" && !frm.is_dirty()) {
			frm.add_custom_button(__("Correct Entry"), () => {
				_create_correction(frm);
			});
		}

		_highlight_critical(frm);
	},

	bedside_chart(frm) {
		if (!frm.doc.bedside_chart) return;
		_load_template_parameters(frm);
	},
});

function _load_template_parameters(frm) {
	frappe.call({
		method: "alcura_ipd_ext.api.charting.get_chart_parameters",
		args: { bedside_chart: frm.doc.bedside_chart },
		callback(r) {
			if (!r.message) return;
			frm.clear_table("observations");
			for (const param of r.message) {
				const row = frm.add_child("observations");
				row.parameter_name = param.parameter_name;
				row.uom = param.uom || "";
				row.numeric_value = 0;
			}
			frm.refresh_field("observations");
		},
	});
}

function _create_correction(frm) {
	const d = new frappe.ui.Dialog({
		title: __("Correct Entry"),
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
				method: "alcura_ipd_ext.api.charting.create_correction_entry",
				args: {
					original_entry: frm.doc.name,
					correction_reason: values.correction_reason,
				},
				freeze: true,
				freeze_message: __("Creating correction entry..."),
				callback(r) {
					if (r.message) {
						frappe.set_route("Form", "IPD Chart Entry", r.message.name);
					}
				},
			});
		},
	});
	d.show();
}

function _highlight_critical(frm) {
	(frm.doc.observations || []).forEach((row, idx) => {
		if (row.is_critical) {
			const grid_row = frm.fields_dict.observations.grid.grid_rows[idx];
			if (grid_row) {
				$(grid_row.row).css("background-color", "var(--red-50, #fff5f5)");
			}
		}
	});
}
