frappe.ui.form.on("Payer Billing Rule Set", {
	setup(frm) {
		frm.set_query("payer", () => ({
			filters: { disabled: 0 },
		}));
	},

	payer_type(frm) {
		if (frm.doc.payer_type === "Cash") {
			frm.set_value("payer", "");
			frm.set_value("insurance_payor", "");
		}
	},
});
