// Copyright (c) 2026, Alcura and contributors
// For license information, please see license.txt

frappe.ui.form.on("IPD Bed Policy", {
	refresh(frm) {
		frm.page.set_indicator(__("Settings"), "blue");
		frm.set_intro(
			__(
				"Configure hospital-wide bed operation policies. " +
				"These settings govern availability computation, gender enforcement, " +
				"housekeeping SLAs, and payer eligibility filtering across the IPD module."
			)
		);
	},
});
