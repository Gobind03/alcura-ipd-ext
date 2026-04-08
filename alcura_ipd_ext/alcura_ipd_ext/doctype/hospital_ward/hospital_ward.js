// Copyright (c) 2026, Alcura and contributors
// For license information, please see license.txt

const CRITICAL_CARE_CLASSIFICATIONS = new Set([
	"ICU", "CICU", "MICU", "NICU", "PICU", "SICU", "HDU", "Burns",
]);

frappe.ui.form.on("Hospital Ward", {
	setup(frm) {
		frm.set_query("healthcare_service_unit", () => {
			const filters = { is_group: 1 };
			if (frm.doc.company) {
				filters.company = frm.doc.company;
			}
			return { filters };
		});
	},

	refresh(frm) {
		frm.toggle_enable(["total_beds", "occupied_beds", "available_beds"], false);
	},

	ward_code(frm) {
		if (frm.doc.ward_code) {
			frm.set_value("ward_code", frm.doc.ward_code.toUpperCase().trim());
		}
	},

	ward_classification(frm) {
		const is_cc = CRITICAL_CARE_CLASSIFICATIONS.has(frm.doc.ward_classification) ? 1 : 0;
		frm.set_value("is_critical_care", is_cc);
	},

	company(frm) {
		if (frm.doc.healthcare_service_unit) {
			frm.set_value("healthcare_service_unit", "");
		}
	},
});
