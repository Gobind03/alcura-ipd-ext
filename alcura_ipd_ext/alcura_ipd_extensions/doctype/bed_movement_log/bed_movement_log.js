// Copyright (c) 2026, Alcura and contributors
// For license information, please see license.txt

frappe.ui.form.on("Bed Movement Log", {
	refresh(frm) {
		_set_indicator(frm);

		if (!frm.is_new()) {
			frm.disable_save();
		}
	},
});

function _set_indicator(frm) {
	const map = {
		Admission: ["Admission", "green"],
		Transfer: ["Transfer", "blue"],
		Discharge: ["Discharge", "orange"],
	};
	const entry = map[frm.doc.movement_type];
	if (entry) {
		frm.page.set_indicator(__(entry[0]), entry[1]);
	}
}
