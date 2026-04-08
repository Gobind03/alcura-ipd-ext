// Copyright (c) 2026, Alcura and contributors
// For license information, please see license.txt

frappe.ui.form.on("IPD Order SLA Config", {
	refresh(frm) {
		if (!frm.is_new()) {
			frm.set_intro(
				__("SLA targets for {0} orders with {1} urgency.", [
					frm.doc.order_type,
					frm.doc.urgency,
				])
			);
		}
	},
});
