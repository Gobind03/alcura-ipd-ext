frappe.ui.form.on("ICU Monitoring Profile", {
	refresh(frm) {
		if (!frm.is_new() && frm.doc.is_active) {
			frm.add_custom_button(
				__("View Applicable Wards"),
				() => {
					frappe.set_route("List", "Hospital Ward", {
						ward_classification: frm.doc.unit_type,
						is_active: 1,
					});
				},
				__("Actions")
			);
		}
	},
});
