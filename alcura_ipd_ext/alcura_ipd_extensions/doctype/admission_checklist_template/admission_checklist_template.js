// Copyright (c) 2026, Alcura and contributors
// For license information, please see license.txt

frappe.ui.form.on("Admission Checklist Template", {
	refresh(frm) {
		if (!frm.is_new() && frm.doc.checklist_items) {
			const mandatory = frm.doc.checklist_items.filter((r) => r.is_mandatory).length;
			const total = frm.doc.checklist_items.length;
			frm.dashboard.add_comment(
				__("{0} items ({1} mandatory)", [total, mandatory]),
				"blue",
				true
			);
		}
	},
});
