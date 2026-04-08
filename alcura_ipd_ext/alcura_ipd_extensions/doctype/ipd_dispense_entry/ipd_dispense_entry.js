// Copyright (c) 2026, Alcura and contributors
// For license information, please see license.txt

frappe.ui.form.on("IPD Dispense Entry", {
	refresh(frm) {
		if (frm.doc.status === "Returned") {
			frm.dashboard.add_comment(
				__("This dispense has been returned."),
				"orange",
				true
			);
		}

		if (!frm.is_new() && frm.doc.status === "Dispensed" && !frm.is_dirty()) {
			frm.add_custom_button(__("Return"), () => {
				_return_dispense(frm);
			});
		}
	},

	clinical_order(frm) {
		if (frm.doc.clinical_order) {
			frappe.db.get_value(
				"IPD Clinical Order",
				frm.doc.clinical_order,
				["medication_item", "medication_name", "dose", "dose_uom", "patient", "inpatient_record"],
				(r) => {
					if (r) {
						frm.set_value("medication_item", r.medication_item);
						frm.set_value("medication_name", r.medication_name);
						frm.set_value("dose", r.dose);
						frm.set_value("dose_uom", r.dose_uom);
						frm.set_value("patient", r.patient);
						frm.set_value("inpatient_record", r.inpatient_record);
					}
				}
			);
		}
	},

	medication_item(frm) {
		if (frm.doc.medication_item && !frm.doc.medication_name) {
			frappe.db.get_value("Item", frm.doc.medication_item, "item_name", (r) => {
				if (r && r.item_name) {
					frm.set_value("medication_name", r.item_name);
				}
			});
		}
	},
});

function _return_dispense(frm) {
	const d = new frappe.ui.Dialog({
		title: __("Return Dispense"),
		fields: [
			{
				fieldtype: "Small Text",
				fieldname: "reason",
				label: __("Return Reason"),
				reqd: 1,
			},
		],
		primary_action_label: __("Return"),
		primary_action(values) {
			d.hide();
			frappe.call({
				method: "alcura_ipd_ext.api.pharmacy.return_dispense",
				args: {
					dispense_entry: frm.doc.name,
					reason: values.reason,
				},
				freeze: true,
				callback() {
					frm.reload_doc();
				},
			});
		},
	});
	d.show();
}
